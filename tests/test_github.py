from src.github import GitHubIssue
import unittest
from unittest.mock import patch


def mocked_response(*args, **kwargs):
    """Create class to mock response in _get_info method."""

    class MockResponse:
        def __init__(self, json_data):
            self.json_data = json_data

        def json(self):
            return self.json_data

    # Careful, args needs to be a tuple, and that always ends with a "," character in Python!!
    if args == ('mock-url-REPO/issues/REAL-ISSUE',):

        return MockResponse(
            {'assignee': None,
             'body': 'Issue Number: ABC-10',
             'created_at': '2019-02-20T22:51:33Z',
             'number': 100,
             'state': 'open',
             'title': 'Really an issue',
             'updated_at': '2019-02-21T19:37:18Z',
             'url': 'https://api.github.com/repos/ucsc-cgp/sync-agile-boards/issues/34',
             'user': {'login': 'unito-bot'}}
        )

    elif args == ('mock-url-REPO/issues/NONEXISTENT-ISSUE',):
        return MockResponse(
            {'documentation_url': 'https://developer.github.com/v3/issues/#get-a-single-issue',
             'message': 'Not Found'})

    else:
        raise RuntimeError(args, kwargs)


def mocked_token():
    return 'mock-token'


class TestGitHubIssue(unittest.TestCase):

    @patch('src.github.get_access_params')
    @patch('requests.get', side_effect=mocked_response)
    def test_happy_init(self, get_mocked_response, get_mocked_token):
        get_mocked_token.return_value = {'options': {'server': 'mock-url-'}, 'api_token': 'mock token'}
        g = GitHubIssue(key='REAL-ISSUE', repo_name="REPO")
        self.assertEqual(g.summary, "Really an issue")
        self.assertEqual(g.issue_type, None)
        self.assertEqual(g.story_points, None)
        self.assertEqual(g.created, '2019-02-20T22:51:33Z')
        self.assertEqual(g.github_key, 100)
        self.assertEqual(g.github_repo_name, 'REPO')

    @patch('src.github.get_access_params')
    @patch('requests.get', side_effect=mocked_response)
    def test_issue_not_found_init(self, get_mocked_response, get_mocked_token):
        get_mocked_token.return_value = {'options': {'server': 'mock-url-'}, 'api_token': 'mock token'}
        with self.assertRaises(ValueError):
            GitHubIssue(key='NONEXISTENT-ISSUE', repo_name='REPO')

    @patch('src.github.get_access_params')
    @patch('requests.get', side_effect=mocked_response)
    def test_get_github_equivalent(self, get_mocked_response, get_mocked_token):
        get_mocked_token.return_value = {'options': {'server': 'mock-url-'}, 'api_token': 'mock token'}
        g = GitHubIssue(key='REAL-ISSUE', repo_name='REPO')
        self.assertEqual(g.get_jira_equivalent(), 'ABC-10')
