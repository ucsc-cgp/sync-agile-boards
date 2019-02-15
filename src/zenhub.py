#!/usr/env/python3


import os, sys, logging, requests, json
sys.path.append(".")
from settings import repo, giturl


logger = logging.getLogger()
logger.setLevel(logging.INFO)
FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format=FORMAT)

def main():
    path_to_token = sys.argv[1]
    repo_name = sys.argv[2]
    issue = sys.argv[3]
    points = sys.argv[4]
    pipeline = sys.argv[5]

    zen = ZenHub(path_to_token=path_to_token,
                 repo_name=repo_name,
                 issue=issue)

    before_change = json.dumps(zen.get_info())
    print(before_change)

    zen.update_ticket(points=points, pipeline=pipeline)

    after_change = json.dumps(zen.get_info())
    print(after_change)

class ZenHub():

    def __init__(self, path_to_token=None, repo_name=None, issue=None):
        self.token = self._get_token(path_to_token)
        self.repo_name = repo_name
        self.repo_id = self._get_repo_id(repo_name)
        self.issue = str(issue)
        self.url = self._generate_url()
        self.headers = {'X-Authentication-Token': self.token, 'Content-Type': 'application/json'}
        self.pipeline_ids = self._get_pipeline_ids()

    def get_info(self):
        logger.info(f'Getting pipeline, storypoints and timestamp for story {self.issue} in repo {self.repo_name}')
        response = requests.get(self.url, headers=self.headers, verify=False)
        if response.status_code == 200:
            data = response.json()
            pipeline = data['pipeline']['name']

            if 'estimate' in data:
                storypoints = data['estimate']['value']
            else:
                storypoints = None

            if data['plus_ones'] == []:
                timestamp = 'Not available'
            else:
                timestamp = data['plus_ones']['created_at']
            return {'Story number': self.issue,
                    'Repository': self.repo_name,
                    'Pipeline': pipeline,
                    'Storypoints': storypoints,
                    'Timestamp': timestamp}

        else:
            return response.json()

    def _generate_url(self):
        _url = giturl['URL']
        return os.path.join(_url, self.repo_id, 'issues', self.issue)

    @staticmethod
    def _get_token(path_to_token):
        try:
            with open(path_to_token, 'r') as fh:
                tok = fh.readlines()
                return tok[0].rstrip()
        except FileNotFoundError as e:
            logger.info(e.strerror)

    @staticmethod
    def _get_repo_id(repo_name):
        try:
            if repo_name == 'azul':
                return str(repo['AZUL'])
            elif repo_name == 'sync-agile-boards':
                return str(repo['SYNC'])
        except ValueError as err:
            logger.info(f'{repo_name} is not a known repo')

    def _update_issue_points(self, value):
        """
        Change the point estimate for the issue.

        :param int value: The desired value for the point estimate.
        """
        logger.debug(f'Changing the current value of story points to {value}')

        url = os.path.join(self.url, 'estimate')
        json_dict = {'estimate': value}
        response = requests.put(url, headers=self.headers, json=json_dict)

        if response.status_code == 200:
            logger.debug(f'Success. {self.issue} now has a story points value of {value}')
        else:
            logger.debug(f'Failed to change the story point value of {self.issue} to {value}')

    def _update_issue_pipeline(self, pipeline, pos=None):
        """
        Change the pipeline of an issue.

        See https://github.com/ZenHubIO/API#move-an-issue-between-pipelines for further documentation.

        :param str pipeline: A valid string representing a pipeline in Zenhub ('New Issue', 'Icebox'...)
                             See the Product Development Pipelines section of the following ink for valid values:
                                 https://www.zenhub.com/blog/how-the-zenhub-team-uses-zenhub-boards-on-github/
        :param pos: Either 'top', 'bottom', or a 0-based position in the array of tickets in this pipeline.
        """
        if pipeline in self.pipeline_ids:
            logger.debug(f'Changing the current value of pipeline to {pipeline}')

            url = os.path.join(self.url, 'moves')
            json_dict = {'pipeline_id': self.pipeline_ids[pipeline], 'position': pos or 'top'}

            response = requests.post(url, headers=self.headers, json=json_dict)

            if response.status_code == 200:
                logger.debug(f'Success. {self.issue} was moved to {pipeline}')
            else:
                logger.debug(f'Failed to move {self.issue} to {pipeline}')
        else:
            logger.error(f'{pipeline} is not a valid pipeline.')

    def _update_issue_to_epic(self):
        """Change the issue into an Epic."""
        logger.debug(f'Turning {self.issue} into an epic in repo {self.repo_name}')

        url = os.path.join(self.url, 'convert_to_epic')
        json_dict = {'issues': [{'repo_id': self.repo_id, 'issue_number': self.issue}]}
        response = requests.put(url, headers=self.headers, json=json_dict)

        if response.status_code == 200:
            logger.debug(f'Success. {self.issue} was converted to an Epic')
        else:
            logger.debug(f'Failed to convert {self.issue} to an Epic')

    def _get_pipeline_ids(self):
        """
        Determine the valid pipeline IDs for this repo.

        :return ids: A dictionary pairing a string representing the pipeline name with its integer ID.
        """
        url = os.path.join(giturl['URL'], self.repo_id, 'board')
        response = requests.get(url, headers=self.headers)

        if response.status_code == 200:
            logger.info(f'Success.')
            data = response.json()
            ids = {pipeline['name']: pipeline['id'] for pipeline in data['pipelines']}
            return ids
        else:
            logger.info(f'Failed.')

    def update_ticket(self, points=None, pipeline=None, pipeline_pos = None, to_epic=False):
        """
        Update the information of a Zenhub Issue.

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
