import datetime
import re
import requests

from src.access import get_access_params
from src.issue import Issue, Repo


class GitHubRepo(Repo):

    def __init__(self, repo_name: str = None, org: str = None, issues: list = None, updated_since: datetime = None):

        super().__init__()
        self.url = get_access_params('github')['options']['server'] + org + '/'
        self.headers = {'Authorization': 'token ' + get_access_params('github')['api_token']}

        self.name = repo_name
        self.org = org
        self.issues = dict()

        if updated_since:  # format the datetime object to use as a search filter
            timestamp_filter = f'+updated:>={updated_since.strftime("%Y-%m-%dT%H:%M:%SZ")}'
        else:
            timestamp_filter = ''  # otherwise don't filter

        if issues is not None :  # Get certain specified issues
            for i in issues:
                self.issues[i] = GitHubIssue(repo=self, key=i)
        else:  # Get all issues in the repo_name
            content = self.api_call(requests.get, url_head='https://api.github.com/',
                                    url_tail=f'search/issues?q=repo:{self.org}/{self.name}{timestamp_filter}&page=', page=1)

            for issue_dict in content['items']:
                self.issues[str(issue_dict['number'])] = GitHubIssue(key=issue_dict['number'], repo=self, content=issue_dict)


class GitHubIssue(Issue):

    def __init__(self, key: str, repo: 'GitHubRepo', content: dict = None):
        """
        Create a GitHub Issue object from an issue key and repo or from a portion of an API response

        :param key: The number of this issue in GitHub
        :param repo: The GitHubRepo object this issue belongs to. All issues must have a repo.
        :param content: If specified, don't make a new API call but use this response from an earlier one
        """
        super().__init__()

        self.repo = repo

        if not content:
            content = self.repo.api_call(requests.get, f'{self.repo.name}/issues/{str(key)}')

            if 'number' not in content.keys():  # If the key doesn't match any issues, this field won't exist
                raise ValueError('No issue matching this id and repo was found')

        self.description = content['body']
        self.github_key = content['number']
        self.jira_key = self.get_jira_equivalent()
        self.summary = content['title']
        self.created = datetime.datetime.strptime(content['created_at'].split('Z')[0], '%Y-%m-%dT%H:%M:%S')
        self.updated = datetime.datetime.strptime(content['updated_at'].split('Z')[0], '%Y-%m-%dT%H:%M:%S')

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

    def update_remote(self):
        """Update this issue on GitHub. The issue must already exist."""

        self.repo.api_call(requests.patch, f'{self.repo.name}/issues/{self.github_key}', json=self.dict_format())

if __name__ == '__main__':
    g = GitHubRepo(repo_name='sync-test', org='ucsc-cgp')
