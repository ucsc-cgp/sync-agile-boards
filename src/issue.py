#! /usr/bin/env python3

import logging
import requests

logger = logging.getLogger(__name__)


class Issue:

    def __init__(self):
        self.assignees = None
        self.description = None  # str
        self.github_key = None  # str, this identifier is used by ZenHub and github
        self.issue_type = None  # str, for Jira: Epic or Task or Story or Bug, for ZenHub: Epic or Issue
        self.jira_key = None  # str, this identifier is only used by jira
        self.github_key = None
        self.github_org = None
        self.pipeline = None  # str, issue state in zenhub
        self.status = None  # str, issue state in jira
        self.story_points = None  # int
        self.summary = None  # str
        self.updated = None  # datetime object

        self.sprint_name = None  # str, when synchronized this should be the same in Jira and ZenHub
        self.sprint_id = None  # str, unique to Jira
        self.milestone_name = None  # str
        self.milestone_id = None  # int, unique to GitHub/ZenHub
        self.repo = None  # Repo object, the repo in which this issue lives

    def update_from(self, source: 'Issue'):
        """
        Set all fields in the sink issue (self) to match those in the source Issue object.
        Fields that are defined in self but are None in source will be left alone.
        :param source: an Issue object to use as the source
        """

        # Headers, url, and token are specific to the issue being in Jira or ZenHub.
        self.__dict__.update({k: v for k, v in source.__dict__.items() if v and k not in ['repo', 'description']})

        # The ZenHub story point value cannot be set to None. If it's being updated from a Jira issue with no story
        # point value, set the story points to 0.
        if source.__class__.__name__ == 'JiraIssue' and source.story_points is None:
            self.story_points = 0

    def print(self):
        """Print out all fields for this issue. For testing purposes"""
        for attribute, value in self.__dict__.items():
            print(f'{attribute}: {value}')
        print('\n')


class Repo:

    def __init__(self):
        self.name = None
        self.org = None
        self.issues = dict()
        self.url = None
        self.headers = None
        self.id = None

    def api_call(self, action, url_tail: str, url_head: str = None, json: dict = None, page: int = '',
                 success_code: int = 200) -> dict:
        """
        Method to handle all API calls
        :param action: A requests method to call, e.g. requests.get or requests.post
        :param url_tail: The part of the url that is unique to this request. Appended to url_head.
        :param url_head: Defaults to self.repo.url, e.g. 'https://api.zenhub.io/p1/repositories/'. Can be set to
                         another value, like for using the old API version.
        :param json: The dictionary-formatted payload to send with the request.
        :param page: For paginated responses, the page/response number upon which to make the next call. This should
                     always be called with either 0 or 1 depending on the API being used. It will then make recursive
                     calls incrementing the page number each time until there are no more pages.
        :param success_code: The HTTP response code that should be returned on success. Defaults to 200; may need to be
                             set to 204 for some cases.
        """

        response = action(f'{url_head or self.url}{url_tail}{page}', headers=self.headers, json=json)

        if response.status_code == success_code:
            if action == requests.get:
                content = response.json()
            else:
                content = {}  # Some other requests return blank json content and decoding them causes an error

            if page:  # Need to check if there is another page of results to get
                if 'total' and 'maxResults' in content.keys():  # For Jira
                    if content['total'] >= page + content['maxResults']:  # There could be another page of results
                        content.update(self.api_call(action, url_tail, url_head=url_head, json=json,
                                                     page=page + content['maxResults'], success_code=success_code))

                elif 'rel="next"' in response.headers['Link']:  # For GitHub, update the 'items' list with the next page
                    content['items'].extend(self.api_call(action, url_tail, url_head=url_head, json=json, page=page + 1,
                                                          success_code=success_code)['items'])
            return content

        elif response.json():  # we don't want to raise an error, but deal with it locally
            return response.json()
