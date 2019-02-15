from src.jira import Issue
import unittest

import unittest
from unittest.mock import patch, MagicMock
from src.jira import JiraIssue


def mocked_response(*args, **kwargs):
    """Create class to mock response in _get_info method."""

    class MockResponse:
        def __init__(self, json_data):
            self.json_data = json_data

        def json(self):
            return self.json_data

    # Careful, args needs to be a tuple, and that always ends with a "," character in Python!!
    if args == ('https://ucsc-cgl.atlassian.net/rest/api/latest/search?jql=id=REAL-ISSUE',):

        return MockResponse(
        {'issues':  # A condensed API response for an issue
            [{'fields': {
                'assignee': {'key': 'aaaaa'},
                'created': '2019-02-05T14:52:11.501-0800',
                'customfield_10014': 7.0,
                'description': 'test ticket\n'
                               '\n'
                               '┆{color:#707070}Issue is synchronized with a '
                               '[GitHub '
                               'issue\n'
                               '┆{color:#707070}Repository Name: '
                               'abc{color}\n'
                               '┆{color:#707070}Issue Number: 25{color}\n',
                'issuetype': {'id': '10001',
                              'name': 'Story'},
                'project': {'key': 'TEST'},
                'status': {'id': '10001',
                           'name': 'Done'},
                'summary': 'Test 1',
                'updated': '2019-02-20T14:34:08.870-0800'},
            'id': '15546',
            'key': 'TEST-1'}]})

    elif args == ('https://ucsc-cgl.atlassian.net/rest/api/latest/search?jql=id=NONEXISTENT-ISSUE',):
        return MockResponse(
            {'errorMessages': ["An issue with key 'TEST-100' does not exist for field "
                               "'id'."],
            'warningMessages': []
            }
        )

    else:
        raise RuntimeError(args, kwargs)


class TestJiraIssue(unittest.TestCase):

    @patch('requests.get', side_effect=mocked_response)
    def test_happy_init(self, get_mocked_response):
        j = JiraIssue(key='REAL-ISSUE')
        self.assertEqual(j.status, "Done")
        self.assertEqual(j.issue_type, "Story")
        self.assertEqual(j.story_points, 7.0)
        self.assertEqual(j.created, '2019-02-05T14:52:11.501-0800')

    @patch('requests.get', side_effect=mocked_response)
    def test_issue_not_found_init(self, get_mocked_response):
        with self.assertRaises(ValueError):
            JiraIssue(key='NONEXISTENT-ISSUE')

    @patch('requests.get', side_effect=mocked_response)
    def test_get_github_equivalent(self, get_mocked_response):
        j = JiraIssue(key='REAL-ISSUE')
        self.assertEqual(j.get_github_equivalent(), ('abc', '25'))
