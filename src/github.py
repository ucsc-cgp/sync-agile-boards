import datetime
import requests
import re

from settings import default_orgs
from src.access import get_access_params
from src.jira import Issue


class GitHubIssue(Issue):

    def __init__(self, key: str = None, repo_name: str = None, response: dict = None):
        """
        Create a GitHub Issue object from an issue key and repo or from a portion of an API response

        :param key: If this and repo_name specified, make an API call searching by this issue key
        :param repo_name: If this and key are specified, make an API call searching in this repo
        :param response: If specified, don't make a new API call but use this response from an earlier one
        """
        super().__init__()

        self.url = get_access_params('github')['options']['server'] + default_orgs['github'] + "/"
        self.token = get_access_params('github')['api_token']
        self.headers = {'Authorization': 'token ' + self.token}
        self.github_repo_name = repo_name

        if key and repo_name:
            response = requests.get(self.url + repo_name + "/issues/" + str(key), headers=self.headers).json()
            if "number" not in response.keys():  # If the key doesn't match any issues, this field won't exist
                raise ValueError("No issue matching this id and repo was found")

        self.description = response['body']
        self.github_key = response['number']
        self.jira_key = self.get_jira_equivalent()
        self.summary = response['title']
        self.created = datetime.datetime.strptime(response['created_at'].split('Z')[0], '%Y-%m-%dT%H:%M:%S')
        self.updated = datetime.datetime.strptime(response['updated_at'].split('Z')[0], '%Y-%m-%dT%H:%M:%S')

        # TODO: Note that GitHub api responses have both str 'assignee' and str array 'assignees' fields. 'assignee' is
        #  deprecated. This could cause problems if multiple people are assigned to an issue in GitHub, because the Jira
        #  assignee field can only hold one person. For now I will assume there is only one assignee in the list.

        if response['assignees']:
            self.assignee = response['assignees'][0]

    def get_jira_equivalent(self) -> str:
        """Find the equivalent Jira issue key if it is listed in the issue text. Issues synced by unito-bot will have
        this information."""

        match_obj = re.search(r'Issue Number: (.*)', self.description)  # search for the key in the issue description
        if match_obj:
            return match_obj.group(1)
        else:
            print("No jira key was found in the description.")
            return None

    def dict_format(self) -> dict:
        d = {
            "title": self.summary,
            "body": self.description,
            "assignees": [self.assignee],
            # "milestone": 1,  # I think this field is unique to GitHub, is it analogous to an epic?
            "labels": [
                "bug"
            ]
        }

        return d

    def post_new_issue(self):
        """Post this issue to GitHub for the first time. The issue should not already exist."""

        response = requests.post(self.url + self.github_repo_name + "/issues/", headers=self.headers, json=self.dict_format)

