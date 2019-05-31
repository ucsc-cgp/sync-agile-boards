import datetime
import pytz
import unittest
from unittest.mock import patch

from src.github import GitHubIssue, GitHubRepo


def mocked_response(*args, **kwargs):
    """A class to mock a response from a GitHub API call"""

    class MockResponse:
        def __init__(self, json_data):
            self.json_data = json_data
            self.status_code = 200

        def json(self):
            return self.json_data

    if args == ('https://mockapi.github.com/repos/SOME_ORG/REPO/issues/REAL-ISSUE',):

        return MockResponse(
            {'assignee': None,
             'assignees': [{'login': 'aaaaa'}],
             'body': 'Issue Number: ABC-10',
             'created_at': '2019-02-20T22:51:33Z',
             'milestone': None,
             'number': 100,
             'state': 'open',
             'title': 'Really an issue',
             'updated_at': '2019-02-21T19:37:18Z',
             'url': 'https://api.github.com/repos/ucsc-cgp/sync-agile-boards/issues/34',
             'user': {'login': 'unito-bot'}}
        )

    elif args == ('https://mockapi.github.com/repos/SOME_ORG/REPO/issues/REAL-ISSUE-2',):

        return MockResponse(
            {'assignee': None,
             'assignees': [{'login': 'aaaaa'}],
             'body': 'no issue key here',
             'created_at': '2019-02-20T22:51:33Z',
             'milestone': None,
             'number': 100,
             'state': 'open',
             'title': 'Really an issue',
             'updated_at': '2019-02-21T19:37:18Z',
             'url': 'https://api.github.com/repos/ucsc-cgp/sync-agile-boards/issues/34',
             'user': {'login': 'unito-bot'}}
        )

    elif args == ('https://mockapi.github.com/repos/SOME_ORG/REPO/issues/NONEXISTENT-ISSUE',):
        return MockResponse(
            {'documentation_url': 'https://developer.github.com/v3/issues/#get-a-single-issue',
             'message': 'Not Found'})

    else:
        raise RuntimeError(args, kwargs)


class TestGitHubIssue(unittest.TestCase):

    @patch('src.github.get_access_params')
    @patch('src.github.requests.get', side_effect=mocked_response)
    def setUp(self, get_mocked_response, mock_access_params):
        mock_access_params.return_value = {'options': {'server': 'https://mockapi.github.com/repos/'},
                                         'api_token': 'mock token'}
        self.github_repo = GitHubRepo(repo_name='REPO', org='SOME_ORG', issues=['REAL-ISSUE', 'REAL-ISSUE-2'])
        self.g = self.github_repo.issues['REAL-ISSUE']
        self.h = self.github_repo.issues['REAL-ISSUE-2']

    def test_happy_init(self):
        self.assertEqual(self.g.summary, 'Really an issue')
        self.assertEqual(self.g.assignees, ['aaaaa'])
        self.assertEqual(self.g.issue_type, None)
        self.assertEqual(self.g.story_points, None)
        self.assertEqual(self.g.created, datetime.datetime(2019, 2, 20, 22, 51, 33, tzinfo=pytz.timezone('UTC')))
        self.assertEqual(self.g.github_key, '100')
        self.assertEqual(self.g.repo.name, 'REPO')
        self.assertEqual(self.g.repo.org, 'SOME_ORG')

    @patch('src.github.get_access_params')
    @patch('src.github.requests.get', side_effect=mocked_response)
    def test_issue_not_found_init(self, get_mocked_response, mock_access_params):
        mock_access_params.return_value = {'options': {'server': 'https://mockapi.github.com/repos/'},
                                           'api_token': 'mock token'}

        with self.assertRaises(ValueError):
            GitHubIssue(key='NONEXISTENT-ISSUE', repo=self.github_repo)

    def test_get_jira_equivalent(self):
        self.assertEqual(self.g.get_jira_equivalent(), 'ABC-10')

    def test_no_issue_key_in_description(self):
        self.assertEqual(self.h.get_jira_equivalent(), '')
