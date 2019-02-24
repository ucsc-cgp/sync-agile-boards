#!/usr/env/python3

import os
import sys
import logging
import requests
import json
sys.path.append(".")
from src.access import get_access_params
from src.utilities import get_repo_id


logger = logging.getLogger()
logger.setLevel(logging.INFO)
FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format=FORMAT)

def main():
    repo_name = sys.argv[1]
    issue = sys.argv[2]

    zen = ZenHub(repo_name=repo_name, issue=issue)
    print(json.dumps(zen.get_info()))


class ZenHub():

    def __init__(self, repo_name, issue):
        self.access_params = get_access_params(mgmnt_sys='zenhub')
        self.repo_name = repo_name
        d = get_repo_id(repo_name)
        self.repo_id = str(d['repo_id'])
        self.issue = str(issue)
        self.url = self._generate_url()


    def get_info(self):
        url = self._generate_url()
        logger.info(f'Getting pipeline, storypoints and timestamp for story {self.issue} in repo {self.repo_name}')
        headers = {'X-Authentication-Token': self.access_params['api_token']}
        response = requests.get(url, headers=headers, verify=False)
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


if __name__ == '__main__':
    main()
