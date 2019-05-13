import datetime
from more_itertools import first
import re
import requests

from settings import transitions
from src.access import get_access_params
from src.issue import Repo, Issue
from src.utilities import CrypticNames, get_zenhub_pipeline


class JiraRepo(Repo):

    def __init__(self, repo_name, jira_org, issues: list = None, updated_since: datetime = None):
        """Create a Project storing all issues belonging to the provided project key
        :param repo_name: Required. The repo to work with e.g. TEST
        :param jira_org: Required. The organization the repo belongs to, e.g. ucsc-cgl
        :param issues: Optional. If not specified, all issues in the repo will be retrieved. If specified, only will
        retrieve and update the listed issues.
        :param updated_since: If specified, get just the issues that have been updated since the time given in this
        datetime object. Otherwise, get all issues in the repo.
        """

        super().__init__()
        self.url = get_access_params('jira')['options']['server'] % jira_org
        self.headers = {'Authorization': 'Basic ' + get_access_params('jira')['api_token']}

        self.name = repo_name
        self.org = jira_org
        self.issues = dict()

        if issues:
            for issue in issues:
                self.issues[issue] = JiraIssue(key=issue, repo=self)

        else:  # By default, get all issues
            if updated_since:  # format the timestamp to use in a Jira query
                timestamp_filter = f" AND updated>='{updated_since.strftime('%Y-%m-%d %H:%M')}'"
            else:
                timestamp_filter = ''  # otherwise do not filter by timestamp

            content = self.api_call(requests.get, f'search?jql=project={self.name}{timestamp_filter}&startAt=', page=0)
            for issue in content['issues']:
                self.issues[issue['key']] = JiraIssue(content=issue, repo=self)

        # self.github_org, self.github_repo = board_map[jira_org][repo]


class JiraIssue(Issue):

    # TODO break up this huge method
    def __init__(self, repo: 'JiraRepo', key: str = None, content: dict = None):
        """
        Create an Issue object from an issue key or from a portion of an API response

        :param repo: The JiraRepo object representing the repo this issue belongs to
        :param key: If specified, make an API call searching by this issue key
        :param content: If specified, don't make a new API call but use this response from an earlier one
        """

        super().__init__()

        self.repo = repo

        if key:
            json = self.repo.api_call(requests.get, f'search?jql=id={key}')

            if 'issues' in json.keys():  # If the key doesn't match any issues, this will be an empty list
                content = json['issues'][0]  # Get the one and only issue in the response
            else:
                raise ValueError('No issue matching this id was found')

        if content['fields']['assignee']:
            self.assignees = [content['fields']['assignee']['name']]
        self.created = datetime.datetime.strptime(content['fields']['created'].split('.')[0], '%Y-%m-%dT%H:%M:%S')
        self.description = content['fields']['description']
        self.issue_type = content['fields']['issuetype']['name']
        self.jira_key = content['key']
        self.status = content['fields']['status']['name']

        self.summary = content['fields']['summary']
        self.updated = datetime.datetime.strptime(content['fields']['updated'].split('.')[0], '%Y-%m-%dT%H:%M:%S')

        # Not all issue descriptions have the corresponding github issue listed in them
        self.github_repo_name, self.github_key = self.get_github_equivalent() or (None, None)

        if CrypticNames.story_points in content['fields'].keys():
            self.story_points = content['fields'][CrypticNames.story_points]

        if CrypticNames.sprint in content['fields']:  # This custom field holds sprint information
            if content['fields'][CrypticNames.sprint]:
                # This field is a list containing a dictionary that's been put in string format.
                # Sprints can have duplicate names. id is the unique identifier used by the API.

                match_obj = re.search(r'id=(\w*),', content['fields']['customfield_10010'][0])
                if match_obj:
                    self.jira_sprint = int(match_obj.group(1))
                else:
                    print('No sprint name was found in the sprint field')

        self.pipeline = get_zenhub_pipeline(self)  # This must be done after sprint status is set

    def get_github_equivalent(self):
        """Find the equivalent Github issue key and repo name if listed in the issue text. Issues synced by unito-bot
        will have this information."""

        if self.description:
            match_obj = re.search(r'Repository Name: ([\w_-]*)[\s\S]*Issue Number: ([\w-]*)', self.description)
            if match_obj:
                return match_obj.group(1), match_obj.group(2)
            print(self.jira_key, 'No match was found in the description.')

    def dict_format(self) -> dict:
        """Describe this issue in a dictionary that can be posted to Jira"""

        d = {
            'fields': {  # these fields can be updated
                'description': self.description,
                'issuetype': {'name': self.issue_type},
                'summary': self.summary
            }
        }

        if self.story_points:
            d['fields']['customfield_10014'] = self.story_points

        if self.assignees:
            d['fields']['assignee'] = {'name': self.assignees[0]}

        if self.jira_sprint:
            d['fields']['customfield_10010'] = self.jira_sprint

        return d

    def update_remote(self):
        """Update the remote issue. The issue must already exist in Jira."""

        transition = {'transition': {'id': transitions[self.status]}}

        # Issue status has to be updated as a transition
        self.repo.api_call(requests.post, f'issue/{self.jira_key}/transitions', json=transition, success_code=204)

        # Issue assignee, description, summary, and story points fields can be updated from a dictionary
        self.repo.api_call(requests.put, f'issue/{self.jira_key}', json=self.dict_format(), success_code=204)

    def change_epic_membership(self, add: str = None, remove: str = None):
        """Add or remove given issue from this epic (self). Specify one issue to add or remove as a kwarg"""

        if add and not remove:
            epic_name = self.jira_key
        elif remove and not add:
            epic_name = 'none'
        else:
            raise RuntimeError('change_epic_membership must be called with exactly one argument')

        issues = {'issues': [add or remove]}

        self.repo.api_call(requests.post, url_head=first(self.repo.url.split('api')),
                           url_tail=f'agile/1.0/epic/{epic_name}/issue', json=issues, success_code=204)

    def get_epic_children(self) -> list:
        """If this issue is an epic, get all its children"""

        children = [i['key'] for i in self.repo.api_call(requests.get, f"search?jql=cf[10008]='{self.jira_key}'")['issues']]
        return children


if __name__ == '__main__':
    j = JiraRepo(jira_org='ucsc-cgl', repo_name='TEST', issues=['TEST-42'])
    print(j.issues['TEST-42'].get_epic_children())
