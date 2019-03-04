import base64
import re
import requests
import pprint
import time

from src.access import get_access_params
from src.board import Issue


class JiraBoard:

    def __init__(self, project_key):
        """
        Create a Project storing all issues belonging to the provided project key

        :param str project_key: The Jira project key e.g. "TEST"
        """
        self.url = get_access_params('jira')['options']['server']
        self.token = get_access_params('jira')['api_token']
        self.headers = {'X-Authentication-Token': self.token}
        self.key = project_key
        self.issues = dict()
        self.api_call(0)  # Get information for all issues in the project

    def api_call(self, start):
        """
        Make API calls until all results have been retrieved. Jira API responses can be paginated, defaulting to 50
        results per page, so a new call has to be made until the total is reached.

        :param start: The index in the results to start at. Always call this function with start=0
        """

        response = requests.get(self.url + 'search?jql=project=%s&startAt=%s' % (self.key, str(start)),
                                headers=self.headers).json()

        for i in response["issues"]:
            self.issues[i["key"]] = JiraIssue(response=i)

        if response['total'] >= start + response['maxResults']:  # There could be another page of results
            self.api_call(start + response['maxResults'])


class JiraIssue(Issue):

    def __init__(self, key=None, response=None):
        """
        Create an Issue object from an issue key or from a portion of an API response

        :param key: If specified, make an API call searching by this issue key
        :param response: If specified, don't make a new API call but use this response from an earlier one
        """
        super().__init__()

        self.url = get_access_params('jira')['options']['server']
        self.token = base64.b64encode(get_access_params('jira')['api_token'].encode())
        self.headers = {'Authorization': 'Basic ' + self.token.decode()}

        if key:
            r = requests.get("%ssearch?jql=id=%s" % (self.url, key), headers=self.headers).json()
            # pp = pprint.PrettyPrinter()
            # pp.pprint(r)
            if "issues" in r.keys():  # If the key doesn't match any issues, this will be an empty list
                response = r["issues"][0]  # Get the one and only issue in the response
            else:
                raise ValueError("No issue matching this id was found")

        if response["fields"]["assignee"]:
            self.assignee = response["fields"]["assignee"]["name"]
        self.created = response["fields"]["created"]
        self.description = response["fields"]["description"]
        self.issue_type = response["fields"]["issuetype"]["name"]
        self.jira_key = response["key"]
        self.status = response["fields"]["status"]["name"]
        self.summary = response["fields"]["summary"]
        self.updated = response["fields"]["updated"]

        self.github_repo_name, self.github_key = self.get_github_equivalent()

        if "customfield_10014" in response["fields"].keys():  # This custom field holds story point values
            self.story_points = response["fields"]["customfield_10014"]

    def get_github_equivalent(self):
        """Find the equivalent Github issue key and repo name if listed in the issue text. Issues synced by unito-bot
        will have this information."""

        match_obj = re.search(r'Repository Name: ([\w_-]*).*\n.*Issue Number: ([\w-]*)', self.description)
        if match_obj:
            return match_obj.group(1), match_obj.group(2)
        else:
            print("No match was found in the description.")
            return None

    def dict_format(self):
        d = {
            "fields": {  # these fields can be updated
                "assignee": {"name": self.assignee},
                "description": self.description,
                "summary": self.summary
            }
        }

        if self.story_points:
            d["fields"]["customfield_10014"] = self.story_points

        return d

    def update_remote(self):
        """Update the remote issue. The issue must already exist in Jira."""

        transitions = {  # Jira API uses these codes to identify status changes
            'To Do': 11,
            'In Progress': 21,
            'Done': 31,
            'In Review': 41,
            'Rejected': 51,
            'New Issue': 61,
            'Merged': 71
        }

        transition = {"transition": {"id": transitions[self.status]}}

        # Issue status has to be updated as a transition
        r = requests.post("%sissue/%s/transitions" % (self.url, self.jira_key), headers=self.headers, json=transition)

        if r.status_code != 204:  # HTTP 204 No Content on success
            print("%d Error transitioning" % r.status_code)

        # Issue assignee, description, summary, and story points fields can be updated from a dictionary
        r = requests.put("%sissue/%s" % (self.url, self.jira_key),
                         headers={'Authorization': 'Basic ZXNvdGhAdWNzYy5lZHU6dG5EUlRXTTZCa2RyRUh6VTBlQ0Q0OEMz'},
                         json=self.dict_format())

        if r.status_code != 204:  # HTTP 204 No Content on success
            print("%d Error" % r.status_code)

    def post_new_issue(self):
        """Post this issue to Jira for the first time. The issue must not already exist."""

        r = requests.post(self.url + "issue/", headers=self.headers, json=self.dict_format())

        if r.status_code != 201:  # HTTP 201 means created
            print("%d Error" % r.status_code)

