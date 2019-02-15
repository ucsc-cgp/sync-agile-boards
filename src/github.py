from src.access import get_access_params
import pprint
import requests
import re
from src.jira import Issue


class GitHubIssue(Issue):

    def __init__(self, key=None, repo_name=None, response=None):
        """
        Create an Issue object from an issue key or from a portion of an API response

        :param key: If specified, make an API call searching by this issue key
        :param response: If specified, don't make a new API call but use this response from an earlier one
        :param github: a GitHub instance with the necessary url and login credentials
        """
        super().__init__()
        print(key, repo_name)

        self.url = get_access_params('github')['options']['server']
        self.token = get_access_params('github')['api_token']
        self.headers = {'Authorization': 'token ' + self.token}
        self.github_repo_name = repo_name

        if key:
            response = requests.get(self.url + repo_name + "/issues/" + str(key), headers=self.headers).json()
            pp = pprint.PrettyPrinter()
            pp.pprint(response)
            if "number" not in response.keys():  # If the key doesn't match any issues, this field won't exist
                raise ValueError("No issue matching this id and repo was found")

        self.description = response['body']
        self.github_key = response['number']
        self.jira_key = self.get_jira_equivalent()
        self.summary = response['title']
        self.created = response['created_at']
        self.updated = response['updated_at']
        self.assignee = response['assignee']

    def get_jira_equivalent(self):
        """Find the equivalent Jira issue key if it is listed in the issue text. Issues synced by unito-bot will have
        this information."""

        match_obj = re.search(r'Issue Number: (.*)', self.description)  # search for the key in the issue description
        if match_obj:
            return match_obj.group(1)
        else:
            print("No jira key was found in the description.")
            return None

    @staticmethod
    def get_repo_id(self, repo_name):
        response = requests.get(self.url + repo_name, headers=self.headers).json()
        return response['id']


if __name__ == '__main__':
    i = GitHubIssue(key=1, repo_name='sync-agile-board')
    i.get_jira_equivalent()
