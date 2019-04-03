import unittest
from unittest.mock import patch

from src.jira import JiraIssue
from src.sync import Sync
from src.zenhub import ZenHubIssue
from tests.test_jira import mocked_response
from tests.test_zenhub import mocked_response



class TestSync(unittest.TestCase):

    def setUp(self):
        self.ZENHUB_ISSUE_1 = ZenHubIssue(
            response={'estimate': {'value': 2},
                      'plus_ones': [],
                      'pipeline': {'name': 'Review/QA'},
                      'is_epic': True}
            )
        self.ZENHUB_ISSUE_1.github_key = 1

        self.ZENHUB_ISSUE_2 = ZenHubIssue(
            response={'estimate': {'value': 2},
                      'plus_ones': [],
                      'pipeline': {'name': 'In Progress'},
                      'is_epic': False}
        )
        self.ZENHUB_ISSUE_2.github_key = 2

        self.ZENHUB_ISSUE_3 = ZenHubIssue(
            response={'estimate': {'value': 2},
                      'plus_ones': [],
                      'pipeline': {'name': 'In Progress'},
                      'is_epic': False}
        )
        self.ZENHUB_ISSUE_3.github_key = 3

        self.ZENHUB_ISSUE_4 = ZenHubIssue(
            response={'estimate': {'value': 2},
                      'plus_ones': [],
                      'pipeline': {'name': 'In Progress'},
                      'is_epic': False}
        )
        self.ZENHUB_ISSUE_4.github_key = 4

        self.JIRA_ISSUE_1 = JiraIssue(
            response={'issues':
            [{'fields': {
                'assignee': None,
                'created': '2019-02-05T14:52:11.501-0800',
                'customfield_10008': None,
                'customfield_10014': 3.0,
                'description': 'synchronized with github: Repository Name: abc, Issue Number: 1',
                'issuetype': {'id': '10001',
                              'name': 'Story'},
                'sprint': None,
                'status': {'name': 'In Progress'},
                'summary': 'Test 2',
                'updated': '2019-02-20T14:34:08.870-0800'},
            'key': 'TEST-1'}]}
        )
        self.JIRA_ISSUE_2 = JiraIssue(
            response={'issues':
                [{'fields': {
                    'assignee': None,
                    'created': '2019-02-05T14:52:11.501-0800',
                    'customfield_10008': None,
                    'customfield_10014': 3.0,
                    'description': 'synchronized with github: Repository Name: abc, Issue Number: 2',
                    'issuetype': {'id': '10001',
                                  'name': 'Story'},
                    'sprint': None,
                    'status': {'name': 'In Progress'},
                    'summary': 'Test 2',
                    'updated': '2019-02-20T14:34:08.870-0800'},
                    'key': 'TEST-2'}]}
        )
        self.JIRA_ISSUE_3 = JiraIssue(
            response={'issues':
                [{'fields': {
                    'assignee': None,
                    'created': '2019-02-05T14:52:11.501-0800',
                    'customfield_10008': None,
                    'customfield_10014': 3.0,
                    'description': 'synchronized with github: Repository Name: abc, Issue Number: 3',
                    'issuetype': {'id': '10001',
                                  'name': 'Story'},
                    'sprint': None,
                    'status': {'name': 'In Progress'},
                    'summary': 'Test 2',
                    'updated': '2019-02-20T14:34:08.870-0800'},
                    'key': 'TEST-3'}]}
        )
        self.JIRA_ISSUE_4 = JiraIssue(
            response={'issues':
                [{'fields': {
                    'assignee': None,
                    'created': '2019-02-05T14:52:11.501-0800',
                    'customfield_10008': None,
                    'customfield_10014': 3.0,
                    'description': 'synchronized with github: Repository Name: abc, Issue Number: 4',
                    'issuetype': {'id': '10001',
                                  'name': 'Story'},
                    'sprint': None,
                    'status': {'name': 'In Progress'},
                    'summary': 'Test 2',
                    'updated': '2019-02-20T14:34:08.870-0800'},
                    'key': 'TEST-4'}]}
        )

    @patch('src.jira.get_epic_children')
    @patch('src.zenhub.get_epic_children')
    @patch('src.jira.add_to_epic', side_effect=pass)
    @patch('src.jira.remove_from_epic', side_effect=pass)
    @patch('src.zenhub.change_epic_membership', side_effect=pass)
    def test_sync_epics(self, get_mock_jira_children, get_mock_zenhub_children, add_to_mock_jira_epic,
                        remove_from_mock_jira_epic, change_mock_zenhub_epic_membership):
        get_mock_jira_children.return_value = ['TEST-2', 'TEST-3']
        get_mock_zenhub_children.return_value = [3, 4]

        Sync.sync_epics(self.JIRA_ISSUE_1, self.ZENHUB_ISSUE_1)  # test syncing from jira to zenhub
        change_mock_zenhub_epic_membership.assert_called_with(add='2')
        change_mock_zenhub_epic_membership.assert_called_with(remove='4')

        Sync.sync_epics(self.ZENHUB_ISSUE_1, self.JIRA_ISSUE_1)  # test syncing from zenhub to jira
        add_to_mock_jira_epic.assert_called_with('TEST-4')
        remove_from_mock_jira_epic.assert_called_with('TEST-2')