import requests
import pprint
import json
import copy


class Project:

    def __init__(self, url, project_key, username, password):
        """
        Create a Project storing all issues belonging to the provided project key

        :param str url: The first portion of the URL for the project of interest e.g. "https://ucsc-cgl.atlassian.net/"
                    Be sure to include the trailing /
        :param str project_key: The Jira project key e.g. "TEST"
        :param str username: Your username with Jira, probably an email address
        :param str password: Your Jira password
        """
        self.url = url
        self.key = project_key
        self.username = username
        self.password = password

        r = requests.get("%srest/api/latest/search?jql=project=%s" % (url, project_key))
        pp = pprint.PrettyPrinter()
        pp.pprint(json.loads(r.text))
        self.issues = [Issue(response) for response in json.loads(r.text)["issues"]]

    def post_new_issue(self, issue):
        """
        Post a new issue to this project with the Jira REST API

        :param issue: an Issue object
        """

        r = requests.post("https://ucsc-cgl.atlassian.net/rest/api/latest/issue/", json=issue.copy(),
                          auth=(self.username, self.password))

        if r.status_code != 201:  # HTTP 201 means created
            print("%d Error" % r.status_code)

    def edit_existing_issue(self, issue, **kwargs):
        """
        Edit fields in an existing issue and post the changes

        :param issue: An Issue object to edit
        :param kwargs: Key-value pairs of issue fields and their new values. For some fields, their value must be set to
         a sub-dictionary e.g. status={'description': 'A new issue',
                                        'id': '10013',
                                        name': 'New Issue'}
        You can either pass these values as a dictionary like this, or just by their names e.g. status='New Issue', in
        which case they will be formatted into a dictionary.
        """
        for key, val in kwargs:
            if key in ["assignee", "issuetype", "status"] and isinstance(val, str):  # These have sub-dictionaries
                val = {"name": val}  # Make a sub-dictionary to hold the name
            issue.fields[key] = val  # Update the value

        r = requests.post("%s/rest/api/latest/issue/%s" % (self.key, issue.fields["key"]), json=issue.copy(),
                          auth=(self.username, self.password))

        if r.status_code != 201:
            print("%d Error" % r.status_code)

class Issue:

    def __init__(self, response):
        """
        Create an Issue object from a portion of an API response

        :param dict response: An element in response.text["issues"].
                              In the format {'expand': ...,
                                             'fields': {field 1: ...,
                                                        field 2: ...}
                                             'id': ...,
                                             'key': ...,
                                             'self': ...}
        """
        self.fields = dict()
        self.fields["project"] = response["fields"]["project"]
        self.fields["key"] = response["fields"]["key"]
        self.fields["summary"] = response["fields"]["summary"]
        self.fields["description"] = response["fields"]["description"]
        self.fields["created"] = response["fields"]["created"]
        self.fields["status"] = response["fields"]["status"]
        self.fields["issuetype"] = {"name": response["fields"]["issuetype"]["name"]}

        if "customfield_10014" in response["fields"].keys():  # This custom field holds story point values
            self.fields["customfield_10014"] = response["fields"]["customfield_10014"]

    def copy(self):
        """Return this issue's information in a format that can be used to create a new issue"""

        json_dict = copy.deepcopy(self.fields)

        for forbidden_field in ["created", "status"]:  # Creating an issue with these fields will cause an error
            json_dict.pop(forbidden_field)

        fields = {
            "fields": json_dict
        }
        return fields


p = Project("https://ucsc-cgl.atlassian.net/", "TEST", "esoth@ucsc.edu", "frOOtl00ps")
