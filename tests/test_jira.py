
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
    if args == ('mock-url-search?jql=id=REAL-ISSUE',):

        return MockResponse(
        {'issues':  # A condensed API response for an issue
            [{'fields': {
                'assignee': {'name': 'aaaaa'},
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

    elif args == ('mock-url-search?jql=id=NONEXISTENT-ISSUE',):
        return MockResponse(
            {'errorMessages': ["An issue with key 'TEST-100' does not exist for field "
                               "'id'."],
            'warningMessages': []
            }
        )

    else:
        raise RuntimeError(args, kwargs)


class TestJiraIssue(unittest.TestCase):

    @patch('src.jira.get_access_params')
    @patch('requests.get', side_effect=mocked_response)
    def setUp(self, get_mocked_response, get_mocked_token):
        get_mocked_token.return_value = {'options': {'server': 'mock-url-'}, 'api_token': 'mock token'}
        self.j = JiraIssue(key='REAL-ISSUE')

    def test_happy_init(self):
        self.assertEqual(self.j.status, "Done")
        self.assertEqual(self.j.issue_type, "Story")
        self.assertEqual(self.j.story_points, 7.0)
        self.assertEqual(self.j.created, '2019-02-05T14:52:11.501-0800')

    @patch('src.jira.get_access_params')
    @patch('requests.get', side_effect=mocked_response)
    def test_issue_not_found_init(self, get_mocked_response, get_mocked_token):
        get_mocked_token.return_value = {'options': {'server': 'mock-url-'}, 'api_token': 'mock token'}
        with self.assertRaises(ValueError):
            JiraIssue(key='NONEXISTENT-ISSUE')

    def test_get_github_equivalent(self):
        self.assertEqual(self.j.get_github_equivalent(), ('abc', '25'))

    def test_dict_format(self):
        d = self.j.dict_format()
        expected_result = {
            "fields": {
                "assignee": {"name": 'aaaaa'},
                "description": 'test ticket\n\n┆{color:#707070}Issue is synchronized with a [GitHub issue\n'
                               '┆{color:#707070}Repository Name: abc{color}\n┆{color:#707070}Issue Number: 25{color}\n',
                "summary": 'Test 1',
                "customfield_10014": 7.0
            }
        }
        self.assertEqual(d, expected_result)

