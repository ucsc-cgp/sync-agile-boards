import re
import unittest
from unittest.mock import patch, call

from src.jira import JiraBoard, JiraIssue
from src.sync import Sync
from src.zenhub import ZenHubBoard, ZenHubIssue


@patch('requests.Response')
def mock_response(url, mock_response, headers):
    """This test uses four issues. Issue 1 is an epic. Issue 2 belongs to 1 in Jira but not in ZenHub. Issue 3 belongs
    to 1 in both. Issue 4 belongs to 1 in ZenHub but not Jira. This way, adding and removing issues from epics can be
    tested in both directions."""

    class MockResponse:
        def __init__(self, json_data):
            self.json_data = json_data
            self.status_code = 200

        def json(self):
            return self.json_data

    # Mock ZenHub issue information
    if url == 'https://api.zenhub.io/p1/repositories/abc/issues/1':
        return MockResponse({'estimate': {'value': 2}, 'plus_ones': [], 'pipeline': {'name': 'Review/QA'},
                             'is_epic': True})
    elif 'https://api.zenhub.io/p1/repositories/abc/issues/' in url:  # For issues 2, 3, and 4
        return MockResponse({'estimate': {'value': 2}, 'plus_ones': [], 'pipeline': {'name': 'In Progress'},
                             'is_epic': False})

    # Mock Jira issue information
    elif url == 'https://ucsc-cgl.atlassian.net/rest/api/latest/search?jql=id=TEST-1':
        return MockResponse({'issues': [{
            'fields': {
                'assignee': None,
                'created': '2019-02-05T14:52:11.501-0800',
                'customfield_10008': None,
                'customfield_10014': 3.0,
                'description': 'synchronized with github: Repository Name: abc Issue Number: 1',
                'issuetype': {'name': 'Epic'},
                'sprint': None,
                'status': {'name': 'In Progress'},
                'summary': 'Test 2',
                'updated': '2019-02-20T14:34:08.870-0800'},
            'key': 'TEST-1'}]})

    elif 'https://ucsc-cgl.atlassian.net/rest/api/latest/search?jql=id=TEST-' in url:  # For issues 2, 3, ad 4
        match_obj = re.search(r'id=TEST-(\d*)', url)
        return MockResponse({'issues': [{
            'fields': {
                'assignee': None,
                'created': '2019-02-05T14:52:11.501-0800',
                'customfield_10008': None,
                'customfield_10014': 3.0,
                'description': 'synchronized with github: Repository Name: abc Issue Number: ' + match_obj.group(1),
                'issuetype': {'name': 'Story'},
                'sprint': None,
                'status': {'name': 'In Progress'},
                'summary': 'Test ' + match_obj.group(1),
                'updated': '2019-02-20T14:34:08.870-0800'},
            'key': 'TEST-' + match_obj.group(1)}]})

    # Mock GitHub issue information
    elif 'https://api.github.com/repos/ucsc-cgp/abc/issues/' in url:
        match_obj = re.search(r'issues/(\d*)', url)
        return MockResponse({
            'assignee': None,
            'assignees': [],
             'body': 'Issue Number: TEST-' + match_obj.group(1),  # We just want this to fill in the issue number field
            'created_at': '2019-02-20T22:51:33Z',
            'milestone': None,
            'title': None,
            'updated_at': '2019-02-20T22:51:33Z',
            'number': match_obj.group(1)
            })
    else:
        raise ValueError(url)


class TestSync(unittest.TestCase):

    def setUp(self):

        # NOTE it's important that the path here refers to where get_repo_id is used - the reference to it that's
        # imported in zenhub.py, not the actual location in utilities.py
        self.patch_zenhub_children = patch('src.zenhub.ZenHubIssue.get_epic_children', return_value=['3', '4'])
        self.patch_jira_children = patch('src.jira.JiraIssue.get_epic_children', return_value=['TEST-2', 'TEST-3'])
        self.patch_get_repo_id = patch('src.zenhub.get_repo_id', return_value={'repo_id': 'abc'})
        self.patch_pipeline_ids = patch('src.zenhub.ZenHubBoard._get_pipeline_ids', return_value={'Done': 1})
        self.patch_requests = patch('src.zenhub.requests.get', side_effect=mock_response)
        self.patch_token = patch('src.access._get_token', return_value='xyz')

        for p in [self.patch_zenhub_children, self.patch_jira_children, self.patch_get_repo_id, self.patch_pipeline_ids,
                  self.patch_requests, self.patch_token]:
            p.start()
            self.addCleanup(p.stop)  # all patches started in this way have to be stopped at the end

        self.ZENHUB_BOARD = ZenHubBoard(repo='abc', org='ucsc-cgp', issues=['1', '2', '3', '4'])
        self.ZENHUB_ISSUE_1 = self.ZENHUB_BOARD.issues['1']

        self.JIRA_BOARD = JiraBoard(repo='TEST', org='ucsc-cgl', issues=['TEST-1', 'TEST-2', 'TEST-3', 'TEST-4'])
        self.JIRA_ISSUE_1 = self.JIRA_BOARD.issues['TEST-1']

    @patch('src.jira.JiraIssue.add_to_this_epic')
    @patch('src.jira.JiraIssue.remove_from_this_epic')
    @patch('src.zenhub.ZenHubIssue.change_epic_membership')
    def test_sync_epics(self, change_mock_zenhub_epic_membership, remove_from_mock_jira_epic, add_to_mock_jira_epic):

        Sync.sync_epics(self.JIRA_ISSUE_1, self.ZENHUB_ISSUE_1)  # test syncing from Jira to ZenHub
        change_mock_zenhub_epic_membership.assert_has_calls([call(add='2'), call(remove='4')])

        Sync.sync_epics(self.ZENHUB_ISSUE_1, self.JIRA_ISSUE_1)  # test syncing from ZenHub to Jira
        add_to_mock_jira_epic.assert_called_with('TEST-4')
        remove_from_mock_jira_epic.assert_called_with('TEST-2')

