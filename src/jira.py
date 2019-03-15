import datetime
import re
import requests

from settings import default_orgs, transitions
from src.access import get_access_params
from src.issue import Issue


class JiraBoard:

    def __init__(self, project_key: str):
        """Create a Project storing all issues belonging to the provided project key"""

        self.url = get_access_params('jira')['options']['server'] + default_orgs['jira']
        self.token = get_access_params('jira')['api_token']
        self.headers = {'Authorization': 'Basic ' + self.token}

        self.key = project_key
        self.issues = dict()
        self.api_call(0)  # Get information for all issues in the project

    def api_call(self, start):
        """
        Make API calls until all results have been retrieved. Jira API responses can be paginated, defaulting to 50
        results per page, so a new call has to be made until the total is reached.

        :param start: The index in the results to start at. Always call this function with start=0
        """

        response = requests.get(f'{self.url}search?jql=project={self.key}&startAt={str(start)}',
                                headers=self.headers).json()

        for i in response["issues"]:
            self.issues[i["key"]] = JiraIssue(response=i)

        if response['total'] >= start + response['maxResults']:  # There could be another page of results
            self.api_call(start + response['maxResults'])

    def get_all_epics(self):
        """Search for issues in this project with issuetype=Epic"""

        r = requests.get(f'{self.url}search?jql=project%20%3D%20{self.key}%20AND%20issuetype%20%3D%20Epic').json()

    def get_epic_issues(self, epic_key):

        r = requests.get(f"{self.url}search?jql=cf[10008]='{epic_key}'").json()


class JiraIssue(Issue):

    def __init__(self, key: str = None, response: dict = None):
        """
        Create an Issue object from an issue key or from a portion of an API response

        :param key: If specified, make an API call searching by this issue key
        :param response: If specified, don't make a new API call but use this response from an earlier one
        """
        super().__init__()  # Initiate the super class, Issue

        self.url = get_access_params('jira')['options']['server'] % (default_orgs['jira'])
        self.token = self.token = get_access_params('jira')['api_token']
        self.headers = {'Authorization': 'Basic ' + self.token}

        if key:
            r = requests.get(f"{self.url}search?jql=id={key}", headers=self.headers).json()

            if "issues" in r.keys():  # If the key doesn't match any issues, this will be an empty list
                response = r["issues"][0]  # Get the one and only issue in the response
            else:
                raise ValueError("No issue matching this id was found")

        if response["fields"]["assignee"]:
            self.assignees = [response["fields"]["assignee"]["name"]]
        self.created = datetime.datetime.strptime(response["fields"]["created"].split('.')[0], '%Y-%m-%dT%H:%M:%S')
        self.description = response["fields"]["description"]
        self.issue_type = response["fields"]["issuetype"]["name"]
        self.jira_key = response["key"]

        if response["fields"]["sprint"]:
            self.jira_sprint = response["fields"]["sprint"]["id"]

        self.parent = response["fields"]["customfield_10008"]  # This custom field holds the epic link
        self.status = response["fields"]["status"]["name"]
        self.summary = response["fields"]["summary"]
        self.updated = datetime.datetime.strptime(response["fields"]["updated"].split('.')[0], '%Y-%m-%dT%H:%M:%S')

        # Not all issue descriptions have the corresponding github issue listed in them
        self.github_repo_name, self.github_key = self.get_github_equivalent() or (None, None)

        if "customfield_10014" in response["fields"].keys():  # This custom field holds story point values
            self.story_points = response["fields"]["customfield_10014"]

    def get_github_equivalent(self):
        """Find the equivalent Github issue key and repo name if listed in the issue text. Issues synced by unito-bot
        will have this information."""

        if self.description:
            match_obj = re.search(r'Repository Name: ([\w_-]*).*\n.*Issue Number: ([\w-]*)', self.description)
            if match_obj:
                return match_obj.group(1), match_obj.group(2)
            print("No match was found in the description.")

    def dict_format(self) -> dict:
        """Describe this issue in a dictionary that can be posted to Jira"""

        d = {
            "fields": {  # these fields can be updated
                "assignee": {"name": self.assignees[0]},
                "description": self.description,
                "summary": self.summary
            }
        }

        if self.story_points:
            d["fields"]["customfield_10014"] = self.story_points

        return d

    def update_remote(self):
        """Update the remote issue. The issue must already exist in Jira."""

        transition = {"transition": {"id": transitions[self.status]}}

        # Issue status has to be updated as a transition
        r = requests.post(f"{self.url}issue/{self.jira_key}/transitions", headers=self.headers, json=transition)

        if r.status_code != 204:  # HTTP 204 No Content on success
            print(f"{r.status_code} Error transitioning")

        # Issue assignee, description, summary, and story points fields can be updated from a dictionary
        r = requests.put(f"{self.url}issue/{self.jira_key}", headers=self.headers, json=self.dict_format())

        if r.status_code != 204:  # HTTP 204 No Content on success
            print(f"{r.status_code} Error")

    def post_new_issue(self):
        """Post this issue to Jira for the first time. The issue must not already exist."""

        r = requests.post(self.url + "issue/", headers=self.headers, json=self.dict_format())

        if r.status_code != 201:  # HTTP 201 means created
            print(f"{r.status_code} Error")

        self.jira_key = r.json()["key"]  # keep the key that Jira assigned to this issue when creating it

    def add_to_epic(self, epic_key):
        """Make this issue part of a Jira epic. If it is already in an epic, that will be overwritten."""
        issues = {'issues': [self.jira_key]}

        # This operation seems to work only in the old API version 1.0
        r = requests.post(f"https://ucsc-cgl.atlassian.net/rest/agile/1.0/epic/{epic_key}/issue", json=issues,
                          headers=self.headers)

        if r.status_code != 204:  # HTTP 204 No content on success
            print(f"{r.status_code} Error")

