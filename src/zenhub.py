#!/usr/env/python3
# from settings import board_map
from src.access import get_access_params
from src.issue import Board, Issue
from src.github import GitHubBoard, GitHubIssue
from src.utilities import get_repo_id, get_jira_status

import json
import logging
import os
import requests
import sys

import pprint
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


class ZenHubBoard(Board):

    def __init__(self, repo: str = None, org: str = None, issues: list = None):
        """Create a ZenHub board object.
        :param repo: Required. The name of the repo e.g. test-sync.
        :param org: Required. The name of the organization to which the repo belongs e.g. ucsc-cgp
        :param issues: Optional. If not specified, all issues in the repo will be retrieved. If specified, only retrieve
        and update the listed issues.
        """

        super().__init__()
        self.url = get_access_params('zenhub')['options']['server']
        self.headers = {'Content-Type': 'application/json',
                        'X-Authentication-Token': get_access_params('zenhub')['api_token']}

        self.github_repo = repo
        self.github_org = org
        self.repo_id = str(get_repo_id(repo, org)['repo_id'])
        self.issues = dict()
        self.pipeline_ids = self._get_pipeline_ids()
        # self.jira_org = board_map[org][repo]

        if issues:
            for i in issues:
                self.issues[i] = ZenHubIssue(key=i, repo=self.github_repo, org=self.github_org)
                self.issues[i].zenhub_board = self  # Store a reference to the board object
        else:
            self.get_all_issues()  # By default, get all issues in the repo

    def get_all_issues(self):
        # ZenHub API endpoint for repo issues only lists open ones, so I'm using the GitHub API to get all issues
        g = GitHubBoard(repo=self.github_repo, org=self.github_org)
        for key, issue in g.issues.items():
            self.issues[key] = ZenHubIssue(key=key, repo=self.github_repo, org=self.github_org)
            self.issues[key].zenhub_board = self  # Store a reference to the board object

    def _get_pipeline_ids(self):
        # Determine the valid pipeline IDs for this repo.
        logger.info(f'Retrieving pipeline ids for {self.github_repo}.')
        r = requests.get(f'{self.url}{self.repo_id}/board', headers=self.headers)

        if r.status_code == 200:
            logger.info(f'Successfully retrieved pipeline ids for {self.github_repo}.')
            data = r.json()
            return {pipeline['name']: pipeline['id'] for pipeline in data['pipelines']}

        else:
            logger.debug(
                f'Error in retreiving pipeline ids. Status Code: {r.status_code}. Reason: {r.text}')
            raise RuntimeError(
                f'Error in retreiving pipeline ids. Status Code: {r.status_code}. Reason: {r.text}')

    def get_all_epics_in_this_repo(self) -> list:
        # TODO this should be part of the zenhub board class when that happens

        r = requests.get(f'{self.url}{self.repo_id}/epics', headers=self.headers).json()
        return [i['issue_number'] for i in r['epic_issues']]


class ZenHubIssue(Issue):

    def __init__(self, key: str = None, repo: str = None, org: str = None, response: dict = None):
        """
        Create an Issue object from an issue key and repo name or from a portion of a ZenHub API response.
        All Issue objects should be made thru a Board object.

        :param key: If this and repo_name are specified, make an API call searching by this issue key
        :param repo: If this and key are specified, make an API call searching in this repo
        :param org: The organization to which the repo belongs, e.g. ucsc-cgp
        :param response: If specified, don't make a new API call but use this response from an earlier one
        """

        super().__init__()

        self.url = get_access_params('zenhub')['options']['server']
        self.headers = {'Content-Type': 'application/json',
                        'X-Authentication-Token': get_access_params('zenhub')['api_token']}
        self.github_repo = repo
        self.github_org = org
        self.repo_id = str(get_repo_id(repo, org)['repo_id'])

        if key and repo:
            r = requests.get(f'{self.url}{self.repo_id}/issues/{key}', headers=self.headers)
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
            self.children = self.get_epic_children()  # Fill in the self.children field
        else:
            self.issue_type = 'Story'
            self.children = []

        # Fill in the missing information for this issue that's in GitHub but not ZenHub
        self.update_from(GitHubIssue(key=self.github_key, repo=self.github_repo, org=self.github_org))

        self.status = get_jira_status(self)
        print(self.github_key, self.status)

    def update_remote(self):
        # TODO the ZenHub API only supports editing issue points, pipeline, and epic status. Other changes can be made
        #  thru the GitHub API. Updating the issue in GitHub as well should be incorporated into this method.

        self._update_issue_points(self.story_points)
        self._update_issue_pipeline(self.pipeline)

    def _update_issue_points(self, value):
        # Change the point estimate for the issue.
        logger.info(f'Changing the current value of story points to {value}')
        json_dict = {'estimate': value}

        r = requests.put(f'{self.url}{self.repo_id}/issues/{self.github_key}/estimate', headers=self.headers,
                         json=json_dict)

        if r.status_code == 200:
            logger.info(f'Success. {self.github_key} now has a story points value of {value}')
        else:
            logger.debug(
                f'Error occured when updating issue points. Status Code: {r.status_code}. Reason: {r.text}')
            raise RuntimeError(
                f'Error occured when updating issue points. Status Code: {r.status_code}. Reason: {r.text}')

    def _update_issue_pipeline(self, pipeline, pos=None):
        # Change the pipeline of an issue.

        # See https://github.com/ZenHubIO/API#move-an-issue-between-pipelines for further documentation.

        # pipeline: A string representing a valid pipeline present in this in ZenHub repo ('New Issue', 'Icebox'...)
        #           Checked against the pipelines found in ZenHub_get_pipeline_ids() and stored in self.pipeline_ids.
        # pos: Either 'top', 'bottom', or a 0-based position in the array of tickets in this pipeline.
        pipeline = pipeline.title()

        if pipeline in self.zenhub_board.pipeline_ids:
            logger.info(f'Changing the current value of pipeline to {pipeline}')

            json_dict = {'pipeline_id': self.zenhub_board.pipeline_ids[pipeline], 'position': pos or 'top'}

            r = requests.post(f'{self.url}{self.repo_id}/issues/{self.github_key}/moves', headers=self.headers,
                              json=json_dict)

            if r.status_code == 200:
                print("success changing pipeline")
                logger.info(f'Success. {self.github_key} was moved to {pipeline}')
            else:
                print("changing pipeline failed")
                logger.debug(f'{r.status_code} error occured when updating issue {self.github_key} to epic: {r.text}')
                raise RuntimeError(
                    f'{r.status_code} error occured when updating issue {self.github_key} to epic: {r.text}')
        else:
            print("not a valid pipeline")
            logger.debug(f'{pipeline} is not a valid pipeline.')

    def promote_issue_to_epic(self):

        logger.info(f'Turning {self.github_key} into an epic in repo {self.github_key}')

        json_dict = {'issues': [{'repo_id': self.repo_id, 'issue_number': self.github_key}]}
        r = requests.post(f'{self.url}{self.repo_id}/issues/{self.github_key}/convert_to_epic', headers=self.headers,
                          json=json_dict)

        if r.status_code == 200:
            logger.info(f'Success. {self.github_key} was converted to an Epic')
        else:
            logger.debug(
                f'{r.status_code} error occured when updating issue {self.github_key} to epic: {r.text}')
            raise RuntimeError(
                f'{r.status_code} error occured when updating issue {self.github_key} to epic: {r.text}')

    def demote_epic_to_issue(self):

        logger.info(f'Turning {self.github_key} into an issue in repo {self.github_repo}')

        json_dict = {'issues': [{'repo_id': self.repo_id, 'issue_number': self.github_key}]}

        r = requests.post(f'{self.url}{self.repo_id}/epics/{self.github_key}/convert_to_issue', headers=self.headers,
                          json=json_dict)

        if r.status_code == 200:
            logger.info(f'Success. {self.github_key} was converted to an Epic')
        else:
            logger.debug(f'{r.status_code} error occured when updating issue {self.github_key} to epic: {r.text}')
            raise RuntimeError(f'{r.status_code} error occured when updating issue {self.github_key} to epic: {r.text}')

    def get_epic_children(self):
        """Fill in the self.children field with all issues that belong to this epic. Self must be an epic."""

        r = requests.get(f'{self.url}{self.repo_id}/epics/{self.github_key}', headers=self.headers).json()

        return [i['issue_number']for i in r['issues']]

    def change_epic_membership(self, add: str = None, remove: str = None):
        """
        Add a given issue to or remove it from this epic in ZenHub. ZenHub issues can belong to multiple epics.
        :param add: If specified, add the given issue as a child of self
        :param remove: If specified, remove the given issue from self epic
        """

        if add:
            content = {'add_issues': [{'repo_id': int(self.repo_id), 'issue_number': int(add)}]}
        elif remove:
            content = {'remove_issues': [{'repo_id': int(self.repo_id), 'issue_number': int(remove)}]}
        else:
            raise ValueError('need to specify an epic to add to or remove from')

        r = requests.post(f'{self.url}{self.repo_id}/epics/{self.github_key}/update_issues', headers=self.headers,
                          json=content)

        if r.status_code != 200:
            raise ValueError(f'{r.status_code} Error: {r.text}')

    def get_issue_events(self):
        r = requests.get(f'{self.url}{self.repo_id}/issues/{self.github_key}/events', headers=self.headers)
        r = r.json()


if __name__ == '__main__':
    z = ZenHubBoard(repo='sync-test', org='ucsc-cgp', issues=['42'])
    z.issues['42'].get_issue_events()
