#!/usr/env/python3

from src.access import get_access_params
from src.issue import Repo, Issue
from src.github import GitHubRepo, GitHubIssue
from src.utilities import get_jira_status, _get_repo_url

import logging
import requests
import sys

sys.path.append('.')
logger = logging.getLogger()
logger.setLevel(logging.INFO)
FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format=FORMAT)


class ZenHubRepo(Repo):

    def __init__(self, repo_name: str = None, org: str = None, issues: list = None):
        """Create a ZenHub board object.
        :param repo_name: Required. The name of the repo e.g. test-sync.
        :param org: Required. The name of the organization to which the repo belongs e.g. ucsc-cgp
        :param issues: Optional. If not specified, all issues in the repo will be retrieved. If specified, only retrieve
        and update the listed issues.
        """

        super().__init__()
        self.url = get_access_params('zenhub')['options']['server']
        self.headers = {'Content-Type': 'application/json',
                        'X-Authentication-Token': get_access_params('zenhub')['api_token']}

        self.name = repo_name
        self.org = org
        self.id = self.get_repo_id()
        self.issues = dict()
        self.pipeline_ids = self._get_pipeline_ids()
        self.github_equivalent = GitHubRepo(repo_name=self.name, org=self.org, issues=[])
        # self.jira_org = board_map[org][repo]

        if issues:
            for i in issues:
                self.issues[i] = ZenHubIssue(repo=self, key=i)
        else:
            self.get_all_issues()  # By default, get all issues in the repo

    def get_all_issues(self):
        # ZenHub API endpoint for repo issues only lists open ones, so I'm using the GitHub API to get all issues
        g = GitHubRepo(repo_name=self.name, org=self.org)
        for key, issue in g.issues.items():
            self.issues[key] = ZenHubIssue(repo=self)

    def _get_pipeline_ids(self):
        """Determine the valid pipeline IDs for this repo"""

        content = self.api_call(requests.get, f'{self.id}/board')
        return {pipeline['name']: pipeline['id'] for pipeline in content['pipelines']}

    def get_repo_id(self):
        """Return the repo ID retrieved thru GitHub"""
        url = _get_repo_url(self.name, self.org)
        content = self.api_call(requests.get, url_head=url, url_tail='')
        return str(content['id'])


class ZenHubIssue(Issue):

    def __init__(self, repo: 'ZenHubRepo', key: str = None, content: dict = None):
        """
        Create an Issue object from an issue key and repo name or from a portion of a ZenHub API response.
        All Issue objects should be made thru a Board object.

        :param key: If this and repo_name are specified, make an API call searching by this issue key
        :param repo: If this and key are specified, make an API call searching in this repo
        :param content: If specified, don't make a new API call but use this response from an earlier one
        """

        super().__init__()
        self.repo = repo

        if not content:
            content = self.repo.api_call(requests.get, f'{self.repo.id}/issues/{key}')
            content['issue_number'] = key

        self.github_key = content['issue_number']  # this identifier is used by zenhub and github

        if 'estimate' in content:
            self.story_points = content['estimate']['value']
        if 'pipeline' in content:
            self.pipeline = content['pipeline']['name']
        else:
            self.pipeline = 'Closed'  # TODO is this the only case in which the pipeline is not labelled?

        if content['is_epic'] is True:
            self.issue_type = 'Epic'
        else:
            self.issue_type = 'Story'

        self.github_equivalent = GitHubIssue(key=self.github_key, repo=self.repo.github_equivalent)

        # Fill in the missing information for this issue that's in GitHub but not ZenHub
        self.update_from(self.github_equivalent)

        self.status = get_jira_status(self)

    def update_remote(self):
        """Push the changes to the remote issue in ZenHub and GitHub"""

        # Points and pipeline can be updated thru ZenHub's API
        self._update_issue_points()
        self._update_issue_pipeline()

        # Other fields like description and title have to be updated thru GitHub
        self.github_equivalent.update_from(self)
        self.github_equivalent.update_remote()

    def _update_issue_points(self):
        """Update the remote issue's points estimate to the value currently held by the Issue object"""

        json_dict = {'estimate': self.story_points}
        self.repo.api_call(requests.put, f'{self.repo.id}/issues/{self.github_key}/estimate', json=json_dict)

    def _update_issue_pipeline(self):
        """Update the remote issue's pipeline to the status currently held by the Issue object.

        See https://github.com/ZenHubIO/API#move-an-issue-between-pipelines for further documentation.
        Issue pipeline name must be valid. By default issues are inserted at the top of the list in the pipeline."""

        if self.pipeline in self.repo.pipeline_ids:
            json_dict = {'pipeline_id': self.repo.pipeline_ids[self.pipeline], 'position': 'top'}
            self.repo.api_call(requests.post, f'{self.repo.id}/issues/{self.github_key}/moves', json=json_dict)

        else:
            print("not a valid pipeline")

    def promote_issue_to_epic(self):
        """Convert an issue to an epic"""

        json_dict = {'issues': [{'repo_id': self.repo.id, 'issue_number': self.github_key}]}
        self.repo.api_call(requests.post, f'{self.repo.id}/issues/{self.github_key}/convert_to_epic', json=json_dict)

    def demote_epic_to_issue(self):
        """Convert an epic into a regular issue"""

        json_dict = {'issues': [{'repo_id': self.repo.id, 'issue_number': self.github_key}]}
        self.repo.api_call(requests.post, f'{self.repo.id}/epics/{self.github_key}/convert_to_issue', json=json_dict)

    def get_epic_children(self) -> list:
        """Return a list of all issues that belong to this epic. Self must be an epic."""

        content = self.repo.api_call(requests.get, f'{self.repo.id}/epics/{self.github_key}')
        return [str(i['issue_number']) for i in content['issues']]  # Convert int to str for consistency

    def change_epic_membership(self, add: str = None, remove: str = None):
        """
        Add a given issue to or remove it from this epic in ZenHub. ZenHub issues can belong to multiple epics.
        :param add: If specified, add the given issue as a child of self
        :param remove: If specified, remove the given issue from self epic
        """
        if add:
            content = {'add_issues': [{'repo_id': int(self.repo.id), 'issue_number': int(add)}]}
        elif remove:
            content = {'remove_issues': [{'repo_id': int(self.repo.id), 'issue_number': int(remove)}]}
        else:
            raise ValueError('need to specify an epic to add to or remove from')

        self.repo.api_call(requests.post, f'{self.repo.id}/epics/{self.github_key}/update_issues', json=content)
