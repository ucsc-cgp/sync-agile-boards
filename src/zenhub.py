#!/usr/env/python3

import os
import sys
import logging
import requests
import json
sys.path.append(".")
from src.access import get_access_params
from settings import repo

logger = logging.getLogger()
logger.setLevel(logging.INFO)
FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format=FORMAT)


def main():
    repo_name = sys.argv[1]
    issue = sys.argv[2]
    points = sys.argv[3]
    pipeline = sys.argv[4]

    zen = ZenHub(repo_name=repo_name,
                 issue=issue)

    before_change = json.dumps(zen.get_info())
    print(before_change)

    zen.update_issue(points=points, pipeline=pipeline)

    after_change = json.dumps(zen.get_info())
    print(after_change)


class ZenHub:

    def __init__(self, repo_name=None, issue=None):
        self.access_params = get_access_params(mgmnt_sys='zenhub')
        self.repo_name = repo_name
        self.repo_id = self._get_repo_id(repo_name)
        self.issue = str(issue)
        self.url = self._generate_url()
        self.headers = {'X-Authentication-Token': self.access_params['api_token'], 'Content-Type': 'application/json'}
        self.pipeline_ids = self._get_pipeline_ids()

    def get_info(self):
        logger.info(f'Getting pipeline, storypoints and timestamp for story {self.issue} in repo {self.repo_name}')
        response = requests.get(self.url, headers=self.headers, verify=False)
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

    # TODO: very temporary: need to use GitHub API to return repo_id in the future
    @staticmethod
    def _get_repo_id(repo_name):
        try:
            if repo_name == 'azul':
                return str(repo['AZUL'])
            elif repo_name == 'sync-agile-boards':
                return str(repo['SYNC'])
            elif repo_name == 'sync-test':
                return str(repo['SYNCTest'])
        except ValueError as err:
            logger.info(f'{repo_name} is not a known repo')

    def _update_issue_points(self, value):
        # Change the point estimate for the issue.
        logger.info(f'Changing the current value of story points to {value}')

        url = os.path.join(self.url, 'estimate')
        json_dict = {'estimate': value}
        response = requests.put(url, headers=self.headers, json=json_dict)

        if response.status_code == 200:
            logger.info(f'Success. {self.issue} now has a story points value of {value}')
        else:
            logger.info(f'Failed to change the story point value of {self.issue} to {value}')

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
                logger.info(f'Failed to move {self.issue} to {pipeline}')
        else:
            logger.error(f'{pipeline} is not a valid pipeline.')

    def _update_issue_to_epic(self):
        # Change the issue into an Epic.
        logger.info(f'Turning {self.issue} into an epic in repo {self.repo_name}')

        url = os.path.join(self.url, 'convert_to_epic')
        json_dict = {'issues': [{'repo_id': self.repo_id, 'issue_number': self.issue}]}
        response = requests.put(url, headers=self.headers, json=json_dict)

        if response.status_code == 200:
            logger.info(f'Success. {self.issue} was converted to an Epic')
        else:
            logger.info(f'Failed to convert {self.issue} to an Epic')

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
            logger.info(f'Failed to retrieve pipeline ids for {self.repo_name}.')

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


if __name__ == '__main__':
    main()
