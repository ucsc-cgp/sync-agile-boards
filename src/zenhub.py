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

    zen = ZenHub(path_to_token=path_to_token,
                 repo_name=repo_name,
                 issue=issue)
    print(json.dumps(zen.get_info()))


class ZenHub():

    def __init__(self, path_to_token=None, repo_name=None, issue=None):
        self.token = self._get_token(path_to_token)
        self.repo_name = repo_name
        self.repo_id = self._get_repo_id(repo_name)
        self.issue = str(issue)
        self.url = self._generate_url()


    def get_info(self):
        url = self._generate_url()
        logger.info(f'Getting storypoints for story {self.issue} in repo {self.repo_name}')
        headers = {'X-Authentication-Token': self.token}
        response = requests.get(url, headers=headers, verify=False)
        if response.status_code == 200:
            data = response.json()
            return {'Pipeline': data['pipeline']['name'],
                    'Storypoints': data['estimate']['value']}

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
                return tok[0]
        except FileNotFoundError as e:
            logger.info(e.strerror)

    @staticmethod
    def _get_repo_id(repo_name):
        try:
            if repo_name == 'azul':
                return str(repo['AZUL'])
        except ValueError as err:
            logger.info(f'{repo_name} is not a known repo')


if __name__ == '__main__':
    main()
