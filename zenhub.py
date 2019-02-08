#!/usr/env/python3


import os, sys, logging, requests
from settings import *

logger = logging.getLogger()

def main():
    path_to_token = sys.argv[1]
    repo_name = sys.argv[2]
    issue = sys.argv[3]

    #print(repo['AZUL'])
    zen = ZenHub(path_to_token=path_to_token,
                 repo_name=repo_name,
                 issue=issue)
    print(f'Story points: {zen.get_storypoints()}')


class ZenHub():

    def __init__(self, path_to_token=None, repo_name=None, issue=None):
        self.token = self.get_token(path_to_token)
        self.repo_id = self.get_repo(repo_name)
        self.issue = str(issue)
        self.url = self._generate_url()


    def get_storypoints(self):
        url = self._generate_url()
        headers = {'X-Authentication-Token': self.token}
        response = requests.get(url, headers=headers, verify=False)
        if not response.status_code == 200:
            return {'reason': response.reason}
        else:
            return response.json()

    @staticmethod
    def get_token(path_to_token):
        try:
            with open(path_to_token, 'r') as fh:
                tok = fh.readlines()
                return tok[0]
        except FileNotFoundError as e:
            logger.info(e.strerror)

    def _generate_url(self):
        _url = giturl['URL']
        return os.path.join(_url, self.repo_id, 'issues', self.issue)

    @staticmethod
    def get_repo(repo_name):
        try:
            if repo_name == 'azul':
                return str(repo['AZUL'])
        except ValueError as err:
            logger.info(f'{repo} is not a known repo')


if __name__=='__main__':
    main()
