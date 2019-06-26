import datetime
import logging
import pytz
import re
import requests

from src.access import get_access_params
from src.issue import Issue, Repo

logger = logging.getLogger(__name__)


class GitHubRepo(Repo):

    def __init__(self, repo_name: str = None, org: str = None, issues: list = None):
        """
        Create a GitHub Repo object from a repo name and organization
        :param repo_name: Name of the repo in GitHub
        :param org: Organization this repo belongs to in GitHub
        :param issues: Optional. If specified, only retrieve information for this set of issues
        """

        super().__init__()
        self.url = get_access_params('github')['options']['server'] + org + '/'
        self.headers = {'Authorization': 'token ' + get_access_params('github')['api_token']}

        self.name = repo_name
        self.org = org

        if issues is not None:  # Get certain specified issues
            for i in issues:
                self.issues[i] = GitHubIssue(repo=self, key=i)
        else:  # Get all issues in the repo_name
            content = self.api_call(requests.get, url_head='https://api.github.com/',
                                    url_tail=f'search/issues?q=repo:{self.org}/{self.name}&page=', page=1)

            for issue_dict in content['items']:
                self.issues[str(issue_dict['number'])] = GitHubIssue(key=issue_dict['number'], repo=self,
                                                                     content=issue_dict)


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
        self.github_key = str(content['number'])
        self.summary = content['title']
        self.jira_key = self.get_jira_equivalent()

        # Get datetime objects from timestamp strings and adjust for time zone
        default_tz = pytz.timezone('UTC')  # GitHub timestamps are all in UTC time
        self.created = default_tz.localize(datetime.datetime.strptime(content['created_at'].split('Z')[0],
                                                                      '%Y-%m-%dT%H:%M:%S'))
        self.updated = default_tz.localize(datetime.datetime.strptime(content['updated_at'].split('Z')[0],
                                                                      '%Y-%m-%dT%H:%M:%S'))

        if content['milestone']:
            self.milestone_name = content['milestone']['title']
            self.milestone_id = content['milestone']['number']

        # TODO: Note that GitHub api responses have both dict 'assignee' and dict array 'assignees' fields. 'assignee'
        #  is deprecated. This could cause problems if multiple people are assigned to an issue in GitHub, because the
        #  Jira assignee field can only hold one person.

        if content['assignees']:  # this should be filled in
            self.assignees = [a['login'] for a in content['assignees']]

        elif content['assignee']:  # but just in case
            self.assignees = [content['assignee']['login']]

    def get_jira_equivalent(self):
        """Find the equivalent Jira issue key if it is listed in the issue text. Issues synced by unito-bot will have
        this information."""

        match_obj = re.search(r'Issue Number: ([\w-]+)', self.description)  # search in the issue description

        if match_obj:
            return match_obj.group(1)
        else:
            logging.warning(f'No Jira key was found in the description of issue {self.github_key}')
            return ''

    def open(self):
        """Set this issue's state to open"""

        self.repo.api_call(requests.patch, f'{self.repo.name}/issues/{self.github_key}', json={"state": "open"})

    def add_to_milestone(self, milestone_id):
        """
        Add this issue to a milestone.
        :param milestone_id: ZenHub/GitHub ID of milestone to add to
        """
        logger.debug(f'Adding issue {self.github_key} to milestone {milestone_id}')
        self.repo.api_call(requests.patch, f'{self.repo.name}/issues/{self.github_key}',
                           json={"milestone": milestone_id})

    def remove_from_milestone(self):
        """Remove this issue from any milestone it may be in."""

        logger.debug(f'Removing issue {self.github_key} from milestone')
        self.repo.api_call(requests.patch, f'{self.repo.name}/issues/{self.github_key}', json={"milestone": None})

    def get_milestone_id(self, milestone_name: str) -> int or None:
        """
        Look up the ID for a milestone given its name
        :param milestone_name: Name of milestone to search for
        """
        content = self.repo.api_call(requests.get, f'{self.repo.name}/milestones')
        for milestone in content:
            if milestone['title'] == milestone_name:
                return milestone['number']
        return None
