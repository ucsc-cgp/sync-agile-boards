import datetime
from more_itertools import first
import re
import requests

from settings import board_map, transitions
from src.access import get_access_params
from src.issue import Board, Issue
from src.utilities import get_zenhub_pipeline

import pprint


class JiraBoard(Board):

    def __init__(self, repo, org, issues: list = None):
        """Create a Project storing all issues belonging to the provided project key
        :param repo: Required. The repo to work with e.g. TEST
        :param org: Required. The organization the repo belongs to, e.g. ucsc-cgl
        :param issues: Optional. If not specified, all issues in the repo will be retrieved. If specified, only will
        retrieve and update the listed issues.
        """

        super().__init__()
        self.url = get_access_params('jira')['options']['server'] % org
        self.headers = {'Authorization': 'Basic ' + get_access_params('jira')['api_token']}

        self.jira_repo = repo
        self.jira_org = org
        self.issues = dict()

        if issues:
            for i in issues:
                self.issues[i] = JiraIssue(key=i, org=self.jira_org, board=self)

        else:  # By default, get all issues
            self.api_call()  # Get information for all issues in the project

        # self.github_org, self.github_repo = board_map[org][repo]

    def api_call(self, start=0):
        """
        Make API calls until all results have been retrieved. Jira API responses can be paginated, defaulting to 50
        results per page, so a new call has to be made until the total is reached.

        :param start: The index in the results to start at. Always call this function with start=0
        """

        response = requests.get(f'{self.url}search?jql=project={self.jira_repo}&startAt={str(start)}',
                                headers=self.headers).json()

        for i in response['issues']:
            self.issues[i['key']] = JiraIssue(response=i, org=self.jira_org, board=self)

        if response['total'] >= start + response['maxResults']:  # There could be another page of results
            self.api_call(start=start + response['maxResults'])

    def get_all_epics(self):
        # TODO is this used anywhere?
        """Search for issues in this project with issuetype=Epic"""

        r = requests.get(f'{self.url}search?jql=project={self.jira_repo} AND issuetype=Epic').json()
        return r

    class CrypticNames:
        """A class to hold field ids with names that aren't self explanatory"""
        sprint = 'customfield_10010'
        story_points = 'customfield_10014'


class JiraIssue(Issue):

    # TODO break up this huge method
    def __init__(self, board: 'JiraBoard', key: str = None, org: str = None, response: dict = None):
        """
        Create an Issue object from an issue key or from a portion of an API response

        :param board: The JiraBoard object representing the repo this issue belongs to
        :param key: If specified, make an API call searching by this issue key
        :param org: The organization the issue belongs to, e.g. ucsc-cgl
        :param response: If specified, don't make a new API call but use this response from an earlier one
        """
        super().__init__()

        self.jira_board = board
        self.url = self.jira_board.url
        self.headers = self.jira_board.headers
        self.jira_org = org

        if key:
            r = requests.get(f'{self.url}search?jql=id={key}', headers=self.headers)

            if r.status_code == 200:
                r = r.json()
            else:
                raise ValueError(f'{r.status_code} Error: {r.text}')

            if 'issues' in r.keys():  # If the key doesn't match any issues, this will be an empty list
                response = r['issues'][0]  # Get the one and only issue in the response
            else:
                raise ValueError('No issue matching this id was found')

        if response['fields']['assignee']:
            self.assignees = [response['fields']['assignee']['name']]
        self.created = datetime.datetime.strptime(response['fields']['created'].split('.')[0], '%Y-%m-%dT%H:%M:%S')
        self.description = response['fields']['description']
        self.issue_type = response['fields']['issuetype']['name']
        self.jira_key = response['key']
        self.status = response['fields']['status']['name']

        self.summary = response['fields']['summary']
        self.updated = datetime.datetime.strptime(response['fields']['updated'].split('.')[0], '%Y-%m-%dT%H:%M:%S')

        # Not all issue descriptions have the corresponding github issue listed in them
        self.github_repo, self.github_key = self.get_github_equivalent() or (None, None)

        if self.jira_board.CrypticNames.story_points in response['fields'].keys():
            self.story_points = response['fields'][self.jira_board.CrypticNames.story_points]

        if self.jira_board.CrypticNames.sprint in response['fields']:  # This custom field holds sprint information
            if response['fields'][self.jira_board.CrypticNames.sprint]:
                # This field is a list containing a dictionary that's been put in string format.
                # Sprints can have duplicate names. id is the unique identifier used by the API.

                match_obj = re.search(r'id=(\w*),', response['fields']['customfield_10010'][0])
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
        r = requests.post(f'{self.url}issue/{self.jira_key}/transitions', headers=self.headers, json=transition)

        if r.status_code != 204:  # HTTP 204 No Content on success
            print(f'{r.status_code} Error transitioning')

        # Issue assignee, description, summary, and story points fields can be updated from a dictionary
        r = requests.put(f'{self.url}issue/{self.jira_key}', headers=self.headers, json=self.dict_format())

        if r.status_code != 204:  # HTTP 204 No Content on success
            print(f'{r.status_code} Error updating Jira: {r.text}')

    def post_new_issue(self):
        """Post this issue to Jira for the first time. The issue must not already exist."""

        r = requests.post(f'{self.url}issue/', headers=self.headers, json=self.dict_format())

        if r.status_code != 201:  # HTTP 201 means created
            print(f'{r.status_code} Error posting to Jira: {r.text}')

        self.jira_key = r.json()['key']  # keep the key that Jira assigned to this issue when creating it

    def add_to_this_epic(self, issue_key):
        """Make the given issue belong to this epic (self). If it is already in an epic, that will be overwritten."""

        issues = {'issues': [issue_key]}
        old_api_url = first(self.url.split('api'))  # remove 'api/latest' from the url
        # This operation seems to work only in the old API version 1.0
        r = requests.post(f'{old_api_url}agile/1.0/epic/{self.jira_key}/issue', json=issues, headers=self.headers)

        if r.status_code != 204:  # HTTP 204 No content on success
            print(f'{r.status_code} Error adding to Jira epic: {r.text}')

    def remove_from_this_epic(self, issue_key):
        issues = {'issues': [issue_key]}
        old_api_url = first(self.url.split('api'))  # remove 'api/latest' from the url

        r = requests.post(f'{old_api_url}agile/1.0/epic/none/issue', json=issues, headers=self.headers)

        if r.status_code != 204:  # HTTP 200 No content on success
            print(f'{r.status_code} Error removing from Jira epic: {r.text}')

    def get_epic_children(self):
        """If this issue is an epic, get all its children"""
        r = requests.get(f"{self.url}search?jql=cf[10008]='{self.jira_key}'", headers=self.headers)

        if r.status_code == 200:  # HTTP 200 OK
            children = [i['key'] for i in r.json()['issues']]
            return children
        else:
            print(f'{r.status_code} Error getting Jira epic children: {r.text}')

