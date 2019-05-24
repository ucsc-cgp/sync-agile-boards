import datetime
import pytz
import unittest
from unittest.mock import patch

from src.jira import JiraRepo, JiraIssue


def mocked_response(*args, **kwargs):
    """A class to mock a response from a Jira API call"""

    class MockResponse:
        def __init__(self, json_data):
            self.json_data = json_data
            self.status_code = 200

        def json(self):
            return self.json_data

    # Careful, args needs to be a tuple, and that always ends with a ',' character in Python!!
    if args == ('https://mock-org.atlassian.net/search?jql=project=TEST AND issuekey=ISSUE-WITH-BLANKS&startAt=0',):
        return MockResponse(
        {'issues':  # A condensed API response for an issue
            [{'fields': {
                'assignee': None,
                'created': '2019-02-05T14:52:11.501-0800',
                'customfield_10008': None,
                'customfield_10014': None,
                'description': 'Repository Name: abc{color}\n┆{color:#707070}Issue Number: 27{color}\n',
                'issuetype': {'name': 'Story'},
                'sprint': None,
                'status': {'name': 'In Progress'},
                'summary': 'Test 3',
                'updated': '2019-02-20T14:34:08.870-0800'},
            'id': '15546',
            'key': 'ISSUE-WITH-BLANKS'}],
          'total': 1,
          'maxResults': 50})

    elif args == ('https://mock-org.atlassian.net/search?jql=id=NONEXISTENT-ISSUE',):
        return MockResponse(
            {'errorMessages': ['An issue with key "TEST-100" does not exist for field '
                               '"id".'],
            'warningMessages': []
            }
        )

    elif args == ('https://mock-org.atlassian.net/search?jql=project=TEST&startAt=0',):
        return MockResponse(
            {'total': 2,
             'maxResults': 50,
             'issues':  # A condensed API response for all issues in a board
                [{'fields': {
                    'assignee': {'name': 'aaaaa'},
                    'created': '2019-02-05T14:52:11.501-0800',
                    'customfield_10008': None,
                    'customfield_10014': 7.0,
                    'description': 'test ticket\n\n┆{color:#707070}Issue is synchronized with a [GitHub issue\n'
                                   '┆{color:#707070}Repository Name: abc{color}\n┆{color:#707070}Issue Number: 25{color}\n',
                    'issuetype': {'id': '10001',
                                  'name': 'Story'},
                    'sprint': None,
                    'status': {'id': '10001',
                               'name': 'Done'},
                    'summary': 'Test 1',
                    'updated': '2019-02-20T14:34:08.870-0800'},
                    'id': '15546',
                    'key': 'REAL-ISSUE-1'},
                 {'fields': {
                    'assignee': None,
                    'created': '2019-02-05T14:52:11.501-0800',
                    'customfield_10008': None,
                    'customfield_10014': 3.0,
                    'description': 'another test ticket\n\n┆{color:#707070}Issue is synchronized with a [GitHub issue\n'
                                   '┆{color:#707070}Repository Name: abc{color}\n┆{color:#707070}Issue Number: 26{color}\n',
                    'issuetype': {'id': '10001',
                                  'name': 'Story'},
                    'sprint': None,
                    'status': {'name': 'In Progress'},
                    'summary': 'Test 2',
                    'updated': '2019-02-20T14:34:08.870-0800'},
                    'id': '15546',
                    'key': 'REAL-ISSUE-2'},
                 ]
             }
        )

    else:
        raise RuntimeError(args, kwargs)


class TestJiraIssue(unittest.TestCase):

    @classmethod
    @patch('src.jira.get_access_params')
    @patch('src.jira.requests.get', side_effect=mocked_response)
    def setUp(cls, get_mocked_response, get_mocked_token):
        get_mocked_token.return_value = {'options': {'server': 'https://mock-%s.atlassian.net/',
                                                     'alt_server': 'https://mock-%s.atlassian.net/rest/agile/1.0/'},
                                         'api_token': 'mock token'}

        # Initialize a board with all its issues
        cls.board = JiraRepo(repo_name='TEST', jira_org='org')
        print(cls.board.issues)
        cls.j = cls.board.issues['REAL-ISSUE-1']
        cls.k = cls.board.issues['REAL-ISSUE-2']

        # Initialize a board by specifying one issue of interest
        cls.another_board = JiraRepo(repo_name='TEST', jira_org='org', jql='issuekey=ISSUE-WITH-BLANKS')
        cls.l = cls.another_board.issues['ISSUE-WITH-BLANKS']

    def test_happy_init(self):
        self.assertEqual(self.j.status, 'Done')
        self.assertEqual(self.j.issue_type, 'Story')
        self.assertEqual(self.j.story_points, 7.0)
        self.assertEqual(self.j.updated, datetime.datetime(2019, 2, 20, 14, 34, 8).replace(
            tzinfo=datetime.timezone(datetime.timedelta(hours=-8))))

    @patch('src.jira.get_access_params')
    @patch('src.jira.requests.get', side_effect=mocked_response)
    def test_issue_not_found_init(self, get_mocked_response, get_mocked_token):
        get_mocked_token.return_value = {'options': {'server': 'https://mock-%s.atlassian.net/'}, 'api_token': 'mock token'}
        with self.assertRaises(ValueError):
            JiraIssue(key='NONEXISTENT-ISSUE', repo=self.board)

    def test_get_github_equivalent(self):
        self.j.get_github_equivalent()
        self.assertEqual(self.j.github_key, '25')
        self.assertEqual(self.j.github_repo, 'abc')

    def test_dict_format(self):
        d = self.j.dict_format()
        expected_result = {
            'fields': {
                'assignee': {'name': 'aaaaa'},
                'description': 'test ticket\n\n┆{color:#707070}Issue is synchronized with a [GitHub issue\n'
                               '┆{color:#707070}Repository Name: abc{color}\n┆{color:#707070}Issue Number: 25{color}\n',
                'summary': 'Test 1',
                'issuetype': {'name': 'Story'},
                'customfield_10014': 7.0
            }
        }
        self.assertEqual(d, expected_result)

    def test_update_from(self):
        self.k.update_from(self.j)
        # self.assertEqual(self.k.assignees, ['aaaaa'])
        self.assertEqual(self.k.story_points, 7.0)
        self.assertEqual(self.k.status, 'Done')
