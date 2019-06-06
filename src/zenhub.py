#!/usr/env/python3
import datetime
import logging
import pytz
import requests
import sys
from tqdm import tqdm

from src.access import get_access_params
from src.issue import Repo, Issue
from src.github import GitHubRepo, GitHubIssue
from src.utilities import get_jira_status, _get_repo_url

sys.path.append('.')
logger = logging.getLogger(__name__)


class ZenHubRepo(Repo):

    def __init__(self, repo_name: str = None, org: str = None, issues: list = None, open_only: bool = False):
        """Create a ZenHub board object.
        :param repo_name: Required. The name of the repo e.g. test-sync.
        :param org: Required. The name of the organization to which the repo belongs e.g. ucsc-cgp
        :param issues: Optional. If not specified, all issues in the repo will be retrieved. If specified, only retrieve
                       and update the listed issues.
        :param open_only: Optional. If true, only retrieve and update issues that are open in ZenHub.
        """

        super().__init__()
        self.url = get_access_params('zenhub')['options']['server']
        self.headers = {'Content-Type': 'application/json',
                        'X-Authentication-Token': get_access_params('zenhub')['api_token']}

        self.name = repo_name
        self.org = org
        self.id = self.get_repo_id()
        self.pipeline_ids = self._get_pipeline_ids()
        self.github_equivalent = GitHubRepo(repo_name=self.name, org=self.org, issues=[])

        if issues is not None:  # Only get information for a subset of issues
            for i in tqdm(issues, desc='getting ZenHub issues'):  # progress bar
                self.issues[i] = ZenHubIssue(repo=self, key=i)

        elif open_only:
            self.get_open_issues()  # Only get issues that are open
        else:
            self.get_all_issues()  # By default, get all issues in the repo

    def get_all_issues(self):
        """Retrieve all issues, open or closed"""
        # ZenHub's API will only return open issues when asked to show all issues in a repo
        # But it can return information about closed issues when queried with their key
        # GitHub's API will return all issues in a repo, open or closed
        # So GitHub is used here to get a list of all issues. Then the ZenHub API is asked about each one individually.
        g = GitHubRepo(repo_name=self.name, org=self.org)
        for key, issue in tqdm(g.issues.items(), desc='getting ZenHub issues'):  # progress bar
            self.issues[key] = ZenHubIssue(key=key, repo=self)

    def get_open_issues(self):
        """Retrieve all open issues in this repo thru the ZenHub API"""

        content = self.api_call(requests.get, f'{self.id}/board')

        # progress bar, only shows number of pipelines not number of issues
        for pipeline in tqdm(content['pipelines'], desc='getting ZenHub issues by pipeline'):
            for issue in pipeline['issues']:
                issue['pipeline'] = {'name': pipeline['name']}  # Add in the pipeline info to the sub-dictionary
                self.issues[str(issue['issue_number'])] = ZenHubIssue(repo=self, content=issue)

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
            if key:
                content = self.repo.api_call(requests.get, f'{self.repo.id}/issues/{key}')
                content['issue_number'] = key
            else:
                raise RuntimeError("Both key and content missing from ZenHubIssue constructor")

        self.github_key = content['issue_number']  # this identifier is used by zenhub and github

        if 'estimate' in content:
            self.story_points = content['estimate']['value']
        if 'pipeline' in content:
            self.pipeline = content['pipeline']['name']
        else:
            self.pipeline = 'Closed'

        if content['is_epic'] is True:
            self.issue_type = 'Epic'
        else:
            self.issue_type = 'Story'

        self.github_equivalent = GitHubIssue(key=self.github_key, repo=self.repo.github_equivalent)

        # Fill in the missing information for this issue that's in GitHub but not ZenHub
        self.update_from(self.github_equivalent)

        # Get the most current update timestamp for this issue, whether in GitHub or ZenHub
        # Changes to pipeline and estimate are not reflected in GitHub, so ZenHub events must be checked
        self.updated = max(self.github_equivalent.updated, self.get_most_recent_event())
        self.status = get_jira_status(self)

    def update_remote(self):
        """Push the changes to the remote issue in ZenHub"""

        # Points and pipeline can be updated thru ZenHub's API
        self._update_issue_points()
        self._update_issue_pipeline()

    def _update_issue_points(self):
        """Update the remote issue's points estimate to the value currently held by the Issue object"""
        logger.debug(f"Updating ZenHub issue {self.github_key}'s points value to {self.story_points}")
        json_dict = {'estimate': self.story_points}
        self.repo.api_call(requests.put, f'{self.repo.id}/issues/{self.github_key}/estimate', json=json_dict)

    def _update_issue_pipeline(self):
        """Update the remote issue's pipeline to the status currently held by the Issue object.

        See https://github.com/ZenHubIO/API#move-an-issue-between-pipelines for further documentation.
        Issue pipeline name must be valid. By default issues are inserted at the top of the list in the pipeline."""

        logger.debug(f'Updating ZenHub issue {self.github_key} pipeline to {self.pipeline}')
        if self.pipeline in self.repo.pipeline_ids:
            if self.pipeline != 'Closed':  # Moving between pipelines doesn't work if the issue is closed
                self.github_equivalent.open()

            json_dict = {'pipeline_id': self.repo.pipeline_ids[self.pipeline], 'position': 'top'}
            self.repo.api_call(requests.post, f'{self.repo.id}/issues/{self.github_key}/moves', json=json_dict)

        else:
            logging.warning(f'Cannot update issue {self.github_key} pipeline: not a valid pipeline')

    def promote_issue_to_epic(self):
        """Convert an issue to an epic"""

        logger.debug(f'Promoting ZenHub issue {self.github_key} to epic')
        json_dict = {'issues': [{'repo_id': self.repo.id, 'issue_number': self.github_key}]}
        self.repo.api_call(requests.post, f'{self.repo.id}/issues/{self.github_key}/convert_to_epic', json=json_dict)

    def demote_epic_to_issue(self):
        """Convert an epic into a regular issue"""

        logger.debug(f'Demoting ZenHub epic {self.github_key} to issue')
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
            logger.debug(f'Adding ZenHub issue {add} to epic {self.github_key}')
            content = {'add_issues': [{'repo_id': int(self.repo.id), 'issue_number': int(add)}]}
        elif remove:
            logger.debug(f'Removing ZenHub issue {remove} from epic {self.github_key}')
            content = {'remove_issues': [{'repo_id': int(self.repo.id), 'issue_number': int(remove)}]}
        else:
            raise ValueError('need to specify an epic to add to or remove from')

        self.repo.api_call(requests.post, f'{self.repo.id}/epics/{self.github_key}/update_issues', json=content)

    def get_most_recent_event(self) -> datetime:
        """Look up the list of ZenHub events for this issue and return the timestamp of the most recent one"""

        content = self.repo.api_call(requests.get, f'{self.repo.id}/issues/{self.github_key}/events')
        default_tz = pytz.timezone('UTC')

        if content:
            # Get the first, most recent event in the list. Get its timestamp and convert to a datetime object,
            # ignoring the milliseconds and Z after the period and localizing to UTC time.
            return default_tz.localize(datetime.datetime.strptime(content[0]['created_at'].split('.')[0],
                                                                  '%Y-%m-%dT%H:%M:%S'))
        else:  # This issue has no events. Return the minimum datetime value so the GitHub timestamp will always be used
            return default_tz.localize(datetime.datetime.min)

    def add_to_milestone(self, milestone_id):
        """
        Add this issue to a milestone.
        :param milestone_id: ZenHub/GitHub ID of milestone to add to
        """
        self.github_equivalent.add_to_milestone(milestone_id)

    def remove_from_milestone(self):
        """Remove this issue from any milestone it may be in."""

        self.github_equivalent.remove_from_milestone()

    def get_milestone_id(self, milestone_name: str) -> int:
        """
        Look up the ID for a milestone given its name
        :param milestone_name: Name of milestone to search for
        """
        return self.github_equivalent.get_milestone_id(milestone_name)
