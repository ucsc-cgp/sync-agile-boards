import datetime
import unittest
from unittest.mock import patch

from src.github import GitHubIssue


def mocked_response(*args, **kwargs):
    """A class to mock a response from a GitHub API call"""

    class MockResponse:
        def __init__(self, json_data):
            self.json_data = json_data

        def json(self):
            return self.json_data

    # Careful, args needs to be a tuple, and that always ends with a "," character in Python!!
    if args == ('mock-ucsc-cgp/REPO/issues/REAL-ISSUE',):

        return MockResponse(
            {'assignee': None,
             'assignees': ['aaaaa'],
             'body': 'Issue Number: ABC-10',
             'created_at': '2019-02-20T22:51:33Z',
             'number': 100,
             'state': 'open',
             'title': 'Really an issue',
             'updated_at': '2019-02-21T19:37:18Z',
             'url': 'https://api.github.com/repos/ucsc-cgp/sync-agile-boards/issues/34',
             'user': {'login': 'unito-bot'}}
        )

    elif args == ('mock-ucsc-cgp/REPO/issues/NONEXISTENT-ISSUE',):
        return MockResponse(
            {'documentation_url': 'https://developer.github.com/v3/issues/#get-a-single-issue',
             'message': 'Not Found'})

    else:
        raise RuntimeError(args, kwargs)


class TestGitHubIssue(unittest.TestCase):

    @patch('src.github.get_access_params')
    @patch('requests.get', side_effect=mocked_response)
    def test_happy_init(self, get_mocked_response, get_mocked_token):
        get_mocked_token.return_value = {'options': {'server': 'mock-'}, 'api_token': 'mock token'}
        g = GitHubIssue(key='REAL-ISSUE', repo_name="REPO")
        self.assertEqual(g.summary, "Really an issue")
        self.assertEqual(g.assignee, 'aaaaa')
        self.assertEqual(g.issue_type, None)
        self.assertEqual(g.story_points, None)
        self.assertEqual(g.created, datetime.datetime(2019, 2, 20, 22, 51, 33))
        self.assertEqual(g.github_key, 100)
        self.assertEqual(g.github_repo_name, 'REPO')

    @patch('src.github.get_access_params')
    @patch('requests.get', side_effect=mocked_response)
    def test_issue_not_found_init(self, get_mocked_response, get_mocked_token):
        get_mocked_token.return_value = {'options': {'server': 'mock-'}, 'api_token': 'mock token'}
        with self.assertRaises(ValueError):
            GitHubIssue(key='NONEXISTENT-ISSUE', repo_name='REPO')

    @patch('src.github.get_access_params')
    @patch('requests.get', side_effect=mocked_response)
    def test_get_github_equivalent(self, get_mocked_response, get_mocked_token):
        get_mocked_token.return_value = {'options': {'server': 'mock-'}, 'api_token': 'mock token'}
        g = GitHubIssue(key='REAL-ISSUE', repo_name='REPO')
        self.assertEqual(g.get_jira_equivalent(), 'ABC-10')