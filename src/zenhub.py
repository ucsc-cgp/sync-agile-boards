#!/usr/env/python3
# from settings import board_map
from src.access import get_access_params
from src.issue import Repo, Issue
from src.github import GitHubRepo, GitHubIssue
from src.utilities import get_repo_id, get_jira_status

import json
import logging
import os
import requests
import sys

sys.path.append('.')
logger = logging.getLogger()
logger.setLevel(logging.INFO)
FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format=FORMAT)


def main():
    org_name = sys.argv[1]
    repo_name = sys.argv[2]
    issue = sys.argv[3]

    zen = ZenHub(org_name=org_name, repo_name=repo_name, issue=issue)
    print(json.dumps(zen.get_info()))


class ZenHub:

    def __init__(self, org_name, repo_name, issue):
        self.access_params = get_access_params(mgmnt_sys='zenhub')
        self.org_name = org_name
        self.repo_name = repo_name
        self.headers = {'X-Authentication-Token': self.access_params['api_token'], 'Content-Type': 'application/json'}
        d = get_repo_id(repo_name, org_name)
        if d['status_code'] is not 200:
            raise ValueError(f'Check if {repo_name} is an existing repository the organization {org_name}.')
        self.repo_id = str(d['repo_id'])
        self.issue = str(issue)
        self.url = self._generate_url()

    def get_info(self):
        url = self._generate_url()
        logger.info(f'Getting pipeline, storypoints and timestamp for story {self.issue} in repo {self.repo_name}')
        r = requests.get(url, headers=self.headers)
        if r.status_code == 200:
            data = r.json()
            pipeline = data['pipeline']['name']
            if not data['plus_ones']:
                timestamp = 'Not available'
            else:
                timestamp = data['plus_ones']['created_at']
            if 'estimate' not in data.keys():
                storypoints = 'None'
            else:
                storypoints = data['estimate']['value']
            return {'Story number': self.issue,
                    'Repository': self.repo_name,
                    'Pipeline': pipeline,
                    'Storypoints': storypoints,
                    'Timestamp': timestamp}

        else:
            return r.json()

    def _generate_url(self):
        _url = self.access_params['options']['server']
        return os.path.join(_url, self.repo_id, 'issues', self.issue)

    def _get_pipeline_ids(self):
        # Determine the valid pipeline IDs for this repo.
        logger.info(f'Retrieving pipeline ids for {self.repo_name}.')
        r = requests.get(f'{self.url}{self.repo_id}/board', headers=self.headers)

        if r.status_code == 200:
            logger.info(f'Successfully retrieved pipeline ids for {self.repo_name}.')
            data = r.json()
            ids = {pipeline['name']: pipeline['id'] for pipeline in data['pipelines']}
            return ids
        else:
            logger.info(
                f'Error in retrieving pipeline ids. Status Code: {r.status_code}. Reason: {r.reason}')
            raise RuntimeError(
                f'Error in retrieving pipeline ids. Status Code: {r.status_code}. Reason: {r.reason}')


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
        self.id = str(get_repo_id(repo_name, org)['repo_id'])
        self.issues = dict()
        self.pipeline_ids = self._get_pipeline_ids()
        # self.jira_org = board_map[org][repo]

        if issues:
            for i in issues:
                self.issues[i] = ZenHubIssue(repo=self, key=i)
                self.issues[i].repo_object = self  # Store a reference to the board object
        else:
            self.get_all_issues()  # By default, get all issues in the repo

    def get_all_issues(self):
        # ZenHub API endpoint for repo issues only lists open ones, so I'm using the GitHub API to get all issues
        g = GitHubRepo(repo=self.name, org=self.org)
        for key, issue in g.issues.items():
            self.issues[key] = ZenHubIssue(repo=self)

    def _get_pipeline_ids(self):
        # Determine the valid pipeline IDs for this repo.
        logger.info(f'Retrieving pipeline ids for {self.name}.')
        r = requests.get(f'{self.url}{self.id}/board', headers=self.headers)

        if r.status_code == 200:
            logger.info(f'Successfully retrieved pipeline ids for {self.name}.')
            data = r.json()
            return {pipeline['name']: pipeline['id'] for pipeline in data['pipelines']}

        else:
            logger.debug(
                f'Error in retreiving pipeline ids. Status Code: {r.status_code}. Reason: {r.text}')
            raise RuntimeError(
                f'Error in retreiving pipeline ids. Status Code: {r.status_code}. Reason: {r.text}')

    def get_all_epics_in_this_repo(self) -> list:
        # TODO this should be part of the zenhub board class when that happens

        r = requests.get(f'{self.url}{self.id}/epics', headers=self.headers).json()
        return [i['issue_number'] for i in r['epic_issues']]


class ZenHubIssue(Issue):

    def __init__(self, repo: 'ZenHubRepo', key: str = None, response: dict = None):
        """
        Create an Issue object from an issue key and repo name or from a portion of a ZenHub API response.
        All Issue objects should be made thru a Board object.

        :param key: If this and repo_name are specified, make an API call searching by this issue key
        :param repo: If this and key are specified, make an API call searching in this repo
        :param response: If specified, don't make a new API call but use this response from an earlier one
        """

        super().__init__()

        self.repo_object = repo

        if key and repo:
            r = requests.get(f'{self.repo_object.url}{self.repo_object.id}/issues/{key}', headers=self.repo_object.headers)
            if r.status_code == 200:
                response = r.json()
                response['issue_number'] = key
            else:
                raise ValueError(f'{r.status_code} Error: {r.text}')

        self.github_key = response['issue_number']  # this identifier is used by zenhub and github

        if 'estimate' in response:
            self.story_points = response['estimate']['value']
        if 'pipeline' in response:
            self.pipeline = response['pipeline']['name']
        else:
            self.pipeline = 'Closed'  # TODO is this the only case in which the pipeline is not labelled?

        if response['is_epic'] is True:
            self.issue_type = 'Epic'
        else:
            self.issue_type = 'Story'

        self.github_equivalent = GitHubIssue(key=self.github_key, repo=self.repo_object.name, org=self.repo_object.org)

        # Fill in the missing information for this issue that's in GitHub but not ZenHub
        self.update_from(self.github_equivalent)

        self.status = get_jira_status(self)

    def update_remote(self):
        # TODO the ZenHub API only supports editing issue points, pipeline, and epic status. Other changes can be made
        #  thru the GitHub API. Updating the issue in GitHub as well should be incorporated into this method.

        self._update_issue_points()
        self._update_issue_pipeline()

    def _update_issue_points(self):
        """Update the remote issue's points estimate to the value currently held by the Issue object"""

        logger.info(f'Changing the current value of story points to {self.story_points}')
        json_dict = {'estimate': self.story_points}

        r = requests.put(f'{self.repo_object.url}{self.repo_object.id}/issues/{self.github_key}/estimate',
                         headers=self.repo_object.headers, json=json_dict)

        if r.status_code == 200:
            logger.info(f'Success. {self.github_key} now has a story points value of {self.story_points}')
        else:
            logger.debug(
                f'Error occured when updating issue points. Status Code: {r.status_code}. Reason: {r.text}')
            raise RuntimeError(
                f'Error occured when updating issue points. Status Code: {r.status_code}. Reason: {r.text}')

    def _update_issue_pipeline(self):
        """Update the remote issue's pipeline to the status currently held by the Issue object.

        See https://github.com/ZenHubIO/API#move-an-issue-between-pipelines for further documentation.
        Issue pipeline name must be valid. By default issues are inserted at the top of the list in the pipeline."""

        if self.pipeline in self.repo_object.pipeline_ids:
            logger.info(f'Changing the current value of pipeline to {self.pipeline}')

            json_dict = {'pipeline_id': self.repo_object.pipeline_ids[self.pipeline], 'position': 'top'}

            r = requests.post(f'{self.repo_object.url}{self.repo_object.id}/issues/{self.github_key}/moves',
                              headers=self.repo_object.headers, json=json_dict)

            if r.status_code == 200:
                logger.info(f'Success. {self.github_key} was moved to {self.pipeline}')
            else:
                logger.debug(f'{r.status_code} error occured when updating issue {self.github_key} to epic: {r.text}')
                raise RuntimeError(
                    f'{r.status_code} error occured when updating issue {self.github_key} to epic: {r.text}')
        else:
            print("not a valid pipeline")
            logger.debug(f'{self.pipeline} is not a valid pipeline.')

    def promote_issue_to_epic(self):

        logger.info(f'Turning {self.github_key} into an epic in repo {self.github_key}')

        json_dict = {'issues': [{'repo_id': self.repo_object.id, 'issue_number': self.github_key}]}
        r = requests.post(f'{self.repo_object.url}{self.repo_object.id}/issues/{self.github_key}/convert_to_epic', headers=self.repo_object.headers,
                          json=json_dict)

        if r.status_code == 200:
            logger.info(f'Success. {self.github_key} was converted to an Epic')
        else:
            logger.debug(
                f'{r.status_code} error occured when updating issue {self.github_key} to epic: {r.text}')
            raise RuntimeError(
                f'{r.status_code} error occured when updating issue {self.github_key} to epic: {r.text}')

    def demote_epic_to_issue(self):

        logger.info(f'Turning {self.github_key} into an issue in repo {self.repo_object.name}')

        json_dict = {'issues': [{'repo_id': self.repo_object.id, 'issue_number': self.github_key}]}

        r = requests.post(f'{self.repo_object.url}{self.repo_object.id}/epics/{self.github_key}/convert_to_issue', headers=self.repo_object.headers,
                          json=json_dict)

        if r.status_code == 200:
            logger.info(f'Success. {self.github_key} was converted to an Epic')
        else:
            logger.debug(f'{r.status_code} error occured when updating issue {self.github_key} to epic: {r.text}')
            raise RuntimeError(f'{r.status_code} error occured when updating issue {self.github_key} to epic: {r.text}')

    def get_epic_children(self):
        """Fill in the self.children field with all issues that belong to this epic. Self must be an epic."""

        r = requests.get(f'{self.repo_object.url}{self.repo_object.id}/epics/{self.github_key}', headers=self.repo_object.headers)

        if r.status_code == 200:
            return [str(i['issue_number']) for i in r.json()['issues']]  # Convert to str from int for consistency
        else:
            raise ValueError(f'{r.status_code} Error getting {self.github_key} children: {r.text}')

    def change_epic_membership(self, add: str = None, remove: str = None):
        """
        Add a given issue to or remove it from this epic in ZenHub. ZenHub issues can belong to multiple epics.
        :param add: If specified, add the given issue as a child of self
        :param remove: If specified, remove the given issue from self epic
        """
        if add:
            content = {'add_issues': [{'repo_id': int(self.repo_object.id), 'issue_number': int(add)}]}
        elif remove:
            content = {'remove_issues': [{'repo_id': int(self.repo_object.id), 'issue_number': int(remove)}]}
        else:
            raise ValueError('need to specify an epic to add to or remove from')

        r = requests.post(f'{self.repo_object.url}{self.repo_object.id}/epics/{self.github_key}/update_issues', headers=self.repo_object.headers,
                          json=content)

        if r.status_code != 200:
            raise ValueError(f'{r.status_code} Error: {r.text}')


if __name__ == '__main__':
    z = ZenHubRepo(repo_name='sync-test', org='ucsc-cgp', issues=['7'])
