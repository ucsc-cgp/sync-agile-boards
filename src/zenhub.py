#!/usr/env/python3

import os
import sys
import logging
import requests
import json
sys.path.append(".")
from src.access import get_access_params
from src.utilities import get_repo_id
from settings import repo
from src.jira import Issue, JiraIssue
from src.github import GitHub, GitHubIssue


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
        response = requests.get(url, headers=self.headers, verify=False)
        if response.status_code == 200:
            data = response.json()
            pipeline = data['pipeline']['name']
            if data['plus_ones'] == []:
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
            return response.json()

    def _generate_url(self):
        _url = self.access_params['options']['server']
        return os.path.join(_url, self.repo_id, 'issues', self.issue)

    def _update_issue_points(self, value):
        # Change the point estimate for the issue.
        logger.info(f'Changing the current value of story points to {value}')

        url = os.path.join(self.url, 'estimate')
        json_dict = {'estimate': value}
        response = requests.put(url, headers=self.headers, json=json_dict)

        if response.status_code == 200:
            logger.info(f'Success. {self.issue} now has a story points value of {value}')
        else:
            logger.info(
                f'Error occured when updating issue points. Status Code: {response.status_code}. Reason: {response.reason}')
            raise RuntimeError(
                f'Error occured when updating issue points. Status Code: {response.status_code}. Reason: {response.reason}')

    def _update_issue_pipeline(self, pipeline, pos=None):
        # Change the pipeline of an issue.

        # See https://github.com/ZenHubIO/API#move-an-issue-between-pipelines for further documentation.

        # pipeline: A string representing a valid pipeline present in this in ZenHub repo ('New Issue', 'Icebox'...)
        #           Checked against the pipelines found in ZenHub_get_pipeline_ids() and stored in self.pipeline_ids.
        # pos: Either 'top', 'bottom', or a 0-based position in the array of tickets in this pipeline.
        pipeline = pipeline.title()
        if pipeline in self.pipeline_ids:
            logger.info(f'Changing the current value of pipeline to {pipeline}')

            url = os.path.join(self.url, 'moves')
            json_dict = {'pipeline_id': self.pipeline_ids[pipeline], 'position': pos or 'top'}

            response = requests.post(url, headers=self.headers, json=json_dict)

            if response.status_code == 200:
                logger.info(f'Success. {self.issue} was moved to {pipeline}')
            else:
                logger.info(
                    f'Error occured when moving issue to new pipeline. Status Code: {response.status_code}. Reason: {response.reason}')
                raise RuntimeError(
                    f'Error occured when moving issue to new pipeline. Status Code: {response.status_code}. Reason: {response.reason}')
        else:
            logger.info(f'{pipeline} is not a valid pipeline.')

    def _update_issue_to_epic(self):
        # Change the issue into an Epic.
        logger.info(f'Turning {self.issue} into an epic in repo {self.repo_name}')

        url = os.path.join(self.url, 'convert_to_epic')
        json_dict = {'issues': [{'repo_id': self.repo_id, 'issue_number': self.issue}]}
        response = requests.put(url, headers=self.headers, json=json_dict)

        if response.status_code == 200:
            logger.info(f'Success. {self.issue} was converted to an Epic')
        else:
            logger.info(
                f'Error occured when updating issue to epic. Status Code: {response.status_code}. Reason: {response.reason}')
            raise RuntimeError(
                f'Error occured when updating issue to epic. Status Code: {response.status_code}. Reason: {response.reason}')

    def _get_pipeline_ids(self):
        # Determine the valid pipeline IDs for this repo.
        logger.info(f'Retrieving pipeline ids for {self.repo_name}.')
        url = os.path.join(self.access_params['options']['server'], self.repo_id, 'board')
        response = requests.get(url, headers=self.headers)

        if response.status_code == 200:
            logger.info(f'Successfully retrieved pipeline ids for {self.repo_name}.')
            data = response.json()
            ids = {pipeline['name']: pipeline['id'] for pipeline in data['pipelines']}
            return ids
        else:
            logger.info(
                f'Error in retreiving pipeline ids. Status Code: {response.status_code}. Reason: {response.reason}')
            raise RuntimeError(
                f'Error in retreiving pipeline ids. Status Code: {response.status_code}. Reason: {response.reason}')

    def update_issue(self, points=None, pipeline=None, pipeline_pos=None, to_epic=False):
        """
        Update the information of a ZenHub Issue.
        :param int points: The number of points the issue should have.
        :param str pipeline: The pipeline the issue should move to.
        :param str or int pipeline_pos: The issue's position in the new pipeline. 'top', 'bottom', or 0-based index.
                                        If unspecified, defaults to 'top'.
        :param bool to_epic: Should the ticket be changed into an Epic?
        """
        logger.info(f'Beginning updating {self.issue} in repo {self.repo_name}')

        if points:
            self._update_issue_points(points)
        if pipeline:
            self._update_issue_pipeline(pipeline, pipeline_pos)
        if to_epic:
            self._update_issue_to_epic()

        logger.info(f'Finished updating {self.issue} in repo {self.repo_name}')


class ZenHubIssue(Issue):

    def __init__(self, key=None, repo_name=None, response=None):
        """
        Create an Issue object from an issue key and repo name or from a portion of an API response

        :param key: If this and repo_name are specified, make an API call searching by this issue key
        :param repo_name: If this and key are specified, make an API call searching in this repo
        :param response: If specified, don't make a new API call but use this response from an earlier one
        """
        super().__init__()

        self.url = get_access_params('zenhub')['options']['server']
        self.token = get_access_params('zenhub')['api_token']
        self.headers = {'X-Authentication-Token': self.token}
        self.github_repo_name = repo_name

        if key and repo_name:
            self.github_key = key  # this identifier is used by zenhub and github
            response = requests.get("%s%s/issues/%s" % (self.url, GitHubIssue.get_repo_id(repo_name), key),
                                    headers=self.headers).json()

        self.status = response['pipeline']['name']

        if "estimate" in response:
            self.story_points = response['estimate']['value']

    def get_github_equivalent(self):
        """Get the GitHub issue that has the same key as this ZenHub issue"""

        return GitHubIssue(key=self.github_key, repo_name=self.repo_name)


if __name__ == '__main__':
    main()
