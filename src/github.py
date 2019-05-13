import datetime
import re
import requests

from src.access import get_access_params
from src.issue import Repo, Issue


class GitHubRepo(Repo):

    def __init__(self, repo: str = None, org: str = None):

        super().__init__()
        self.url = get_access_params('github')['options']['server'] + org + '/'
        self.headers = {'Authorization': 'token ' + get_access_params('github')['api_token']}

        self.github_repo = repo
        self.github_org = org
        self.issues = dict()
        self.api_call()

    def api_call(self, start=1, updated_since: datetime = None):
        """
        Make API requests until all results have been retrieved. API responses are split into pages of 30 results

        :param start: The index in the results to start at. Always call this function with start=0
        :param updated_since: If specified, get just the issues that have been updated since the time given in this
        datetime object. Otherwise, get all issues in the repo."""

        if updated_since:  # format the datetime object to use as a search filter
            timestamp_filter = f'+updated:>={updated_since.strftime("%Y-%m-%dT%H:%M:%SZ")}'
        else:
            timestamp_filter = ''  # otherwise don't filter

        response = requests.get(f'https://api.github.com/search/issues?q=repo:{self.github_org}/{self.github_repo}{timestamp_filter}&page={start}')

        if response.status_code == 200:
            content = response.json()
        else:
            raise ValueError(f'{response.status_code} Error: {response.text}')

        for issue_dict in content['items']:
            self.issues[str(issue_dict['number'])] = GitHubIssue(org=self.github_org, content=issue_dict)

        # The 'Link' field in the header gives a link to the next page labelled with rel="next', if there is one
        if 'rel="next"' in response.headers['Link']:
            self.api_call(start=start + 1, updated_since=updated_since)


class GitHubIssue(Issue):

    def __init__(self, key: str = None, repo: str = None, org: str = None, content: dict = None):
        """
        Create a GitHub Issue object from an issue key and repo or from a portion of an API response

        :param key: If this and repo_name specified, make an API call searching by this issue key
        :param repo: If this and key are specified, make an API call searching in this repo
        :param org: The organization to which the repo belongs, e.g. ucsc-cgp
        :param content: If specified, don't make a new API call but use this response from an earlier one
        """
        super().__init__()

        self.url = get_access_params('github')['options']['server'] + org + '/'
        self.headers = {'Authorization': 'token ' + get_access_params('github')['api_token']}
        self.github_repo = repo
        self.github_org = org

        if key and repo:
            content = requests.get(f'{self.url}{repo}/issues/{str(key)}', headers=self.headers).json()

            if 'number' not in content.keys():  # If the key doesn't match any issues, this field won't exist
                raise ValueError('No issue matching this id and repo was found')

        self.description = content['body']
        self.github_key = content['number']
        self.jira_key = self.get_jira_equivalent()
        self.summary = content['title']
        # Get datetime objects from timestamp strings and adjust for time zone
        self.created = datetime.datetime.strptime(content['created_at'].split('Z')[0], '%Y-%m-%dT%H:%M:%S') - datetime.timedelta(hours=7)
        self.updated = datetime.datetime.strptime(content['updated_at'].split('Z')[0], '%Y-%m-%dT%H:%M:%S') - datetime.timedelta(hours=7)

        if content['milestone']:
            self.milestone = content['milestone']['number']

        # TODO: Note that GitHub api responses have both dict 'assignee' and dict array 'assignees' fields. 'assignee'
        #  is deprecated. This could cause problems if multiple people are assigned to an issue in GitHub, because the
        #  Jira assignee field can only hold one person.

        if content['assignees']:  # this should be filled in
            self.assignees = [a['login'] for a in content['assignees']]

        elif content['assignee']:  # but just in case
            self.assignees = [content['assignee']['login']]

    def get_jira_equivalent(self) -> str:
        """Find the equivalent Jira issue key if it is listed in the issue text. Issues synced by unito-bot will have
        this information."""

        match_obj = re.search(r'Issue Number: (.*)', self.description)  # search for the key in the issue description
        if match_obj:
            return match_obj.group(1)
        else:
            print(self.github_key, 'No jira key was found in the description.')
            return ''

    def dict_format(self) -> dict:
        dic = {
            'title': self.summary,
            'body': self.description,
            'labels': []
        }

        return dic

    def post_new_issue(self):
        """Post this issue to GitHub for the first time. The issue should not already exist."""

        response = requests.post(f'{self.url}{self.github_repo}/issues/', headers=self.headers, json=self.dict_format)

        if response.status_code != 200:
            print(f'{response.status_code} Error posting to GitHub: {response.text}')

        self.github_key = response.json()['id']  # keep the key that GitHub assigned to this issue when creating it

    def update_remote(self):
        """Update this issue on GitHub. The issue must already exist."""

        response = requests.patch(f'{self.url}{self.github_repo}/issues/{self.github_key}', headers=self.headers,
                           json=self.dict_format())

        if response.status_code != 200:
            print(f'{response.status_code} Error updating GitHub: {response.text}')
