#! /usr/bin/env python3

import logging

logger = logging.getLogger(__name__)


class Issue:

    def __init__(self):

        self.assignees = None  # list[str]
        self.created = None  # datetime object

        self.description = None  # str
        self.github_key = None  # str, this identifier is used by ZenHub and github
        self.issue_type = None  # str, for Jira: Epic or Task or Story or Bug, for ZenHub: Epic or Issue
        self.jira_key = None  # str, this identifier is only used by jira
        self.jira_sprint_id = None  # str
        self.github_key = None
        self.github_milestone = None
        self.github_milestone_number = None
        self.github_org = None
        self.pipeline = None  # str, issue state in zenhub
        self.status = None  # str, issue state in jira
        self.story_points = None  # int
        self.summary = None  # str
        self.updated = None  # datetime object

        self.repo = None  # Repo object, the repo in which this issue lives

    def update_from(self, source: 'Issue'):
        """
        Set all fields in the sink issue (self) to match those in the source Issue object.
        Fields that are defined in self but are None in source will be left alone.
        """
        # TODO sync assignees

        # Headers, url, and token are specific to the issue being in Jira or ZenHub.
        # Description and assignees are more complicated to sync.
        self.__dict__.update({k: v for k, v in source.__dict__.items() if v and k not in ['headers', 'url', 'token',
                                                                                          'description', 'assignees',
                                                                                          'repo']})

        # The ZenHub story point value cannot be set to None. If it's being updated from a Jira issue with no story
        # point value, set the story points to 0.
        if source.__class__.__name__ == 'JiraIssue' and source.story_points is None:
            self.story_points = 0

        if self.description and source.description:       # Both issues should have a description already
            self.description = Issue.merge_descriptions(source.description, self.description)
        elif source.__class__.__name__ == 'GitHubIssue':  # unless a ZenHubIssue is being updated from GitHub
            self.description = source.description
        else:                                             # Otherwise, something is wrong
            raise RuntimeError(f'Issue {self.jira_key} or {self.github_key} has no description')

    def fill_in_blanks_from(self, source: 'Issue'):
        # TODO is this used anywhere?
        """If a field in the sink issue (self) is blank, fill it with info from the source issue."""

        for attribute in source.__dict__.keys():
            if attribute not in ['headers', 'url', 'token', 'description']:  # ignore attributes specific to the source
                if self.__dict__[attribute] is None:
                    self.__dict__[attribute] = source.__dict__[attribute]  # fill in missing info

    @staticmethod
    def merge_descriptions(source: str, sink: str) -> str:
        """Merge issue descriptions by copying over description text without changing the sync info put in by Unito"""

        if sink.startswith('┆'):  # lines added by unito start with ┆
            unito_link = [line for line in sink.split('\n') if line.startswith('┆')]
            new_description = [line for line in source.split('\n') if not line.startswith('┆')]
        else:  # source contains Unito-added text
            unito_link = [line for line in source.split('\n') if line.startswith('┆')]
            new_description = [line for line in sink.split('\n') if not line.startswith('┆')]
        return '\n'.join(new_description) + '\n'.join(unito_link)

    def print(self):
        """Print out all fields for this issue. For testing purposes"""
        for attribute, value in self.__dict__.items():
            print(f'{attribute}: {value}')
        print('\n')


class Repo:

    def __init__(self):
        self.name = None
        self.org = None
        self.issues = None
        self.url = None
        self.headers = None
        self.id = None
