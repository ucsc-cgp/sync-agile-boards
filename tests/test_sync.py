import re
import unittest
from unittest.mock import patch, call

from src.jira import JiraIssue
from src.sync import Sync
from src.zenhub import ZenHubIssue


def side_effect(*args, **kwargs):
    print("side effect")
    pass


@patch('requests.Response')
def mock_response(url, mock_response, headers):
    """This test uses four issues. Issue 1 is an epic. Issue 2 belongs to 1 in Jira but not in ZenHub. Issue 3 belongs
    to 1 in both. Issue 4 belongs to 1 in ZenHub but not Jira. This way, adding and removing issues from epics can be
    tested in both directions."""

    class MockResponse:
        def __init__(self, json_data):
            self.json_data = json_data

        def json(self):
            return self.json_data

    # Mock ZenHub issue information
    if url == "https://api.zenhub.io/p1/repositories/abc/issues/1":
        return MockResponse({"estimate": {"value": 2}, "plus_ones": [], "pipeline": {"name": "Review/QA"} , "is_epic": True})
    elif url == "https://api.zenhub.io/p1/repositories/abc/issues/2":
        return MockResponse({"estimate": {"value": 2}, "plus_ones": [], "pipeline": {"name": "In Progress"} , "is_epic": False})
    elif url == "https://api.zenhub.io/p1/repositories/abc/issues/3":
        return MockResponse({"estimate": {"value": 2}, "plus_ones": [], "pipeline": {"name": "In Progress"} , "is_epic": False})
    elif url == "https://api.zenhub.io/p1/repositories/abc/issues/4":
        return MockResponse({"estimate": {"value": 2}, "plus_ones": [], "pipeline": {"name": "In Progress"} , "is_epic": False})

    # Mock Jira issue information
    # TODO this could be condensed
    elif url == "https://ucsc-cgl.atlassian.net/rest/api/latest/search?jql=id=TEST-1":
        return MockResponse({'issues': [{
            'fields': {
                'assignee': None,
                'created': '2019-02-05T14:52:11.501-0800',
                'customfield_10008': None,
                'customfield_10014': 3.0,
                'description': 'synchronized with github: Repository Name: abc\n Issue Number: 1',
                'issuetype': {'id': '10001',
                              'name': 'Epic'},
                'sprint': None,
                'status': {'name': 'In Progress'},
                'summary': 'Test 2',
                'updated': '2019-02-20T14:34:08.870-0800'},
            'key': 'TEST-1'}]})
    elif url == "https://ucsc-cgl.atlassian.net/rest/api/latest/search?jql=id=TEST-2":
        return MockResponse({'issues': [{
                'fields': {
                    'assignee': None,
                    'created': '2019-02-05T14:52:11.501-0800',
                    'customfield_10008': None,
                    'customfield_10014': 3.0,
                    'description': 'synchronized with github: Repository Name: abc\n Issue Number: 2',
                    'issuetype': {'id': '10001',
                                  'name': 'Story'},
                    'sprint': None,
                    'status': {'name': 'In Progress'},
                    'summary': 'Test 2',
                    'updated': '2019-02-20T14:34:08.870-0800'},
                    'key': 'TEST-2'}]})
    elif url == "https://ucsc-cgl.atlassian.net/rest/api/latest/search?jql=id=TEST-3":
        return MockResponse({'issues': [{'fields': {
                    'assignee': None,
                    'created': '2019-02-05T14:52:11.501-0800',
                    'customfield_10008': None,
                    'customfield_10014': 3.0,
                    'description': 'synchronized with github: Repository Name: abc\n Issue Number: 3',
                    'issuetype': {'id': '10001',
                                  'name': 'Story'},
                    'sprint': None,
                    'status': {'name': 'In Progress'},
                    'summary': 'Test 2',
                    'updated': '2019-02-20T14:34:08.870-0800'},
                    'key': 'TEST-3'}]})
    elif url == "https://ucsc-cgl.atlassian.net/rest/api/latest/search?jql=id=TEST-4":
        return MockResponse({'issues': [{'fields': {
            'assignee': None,
            'created': '2019-02-05T14:52:11.501-0800',
            'customfield_10008': None,
            'customfield_10014': 3.0,
            'description': 'synchronized with github: Repository Name: abc\n Issue Number: 4',
            'issuetype': {'id': '10001',
                          'name': 'Story'},
            'sprint': None,
            'status': {'name': 'In Progress'},
            'summary': 'Test 2',
            'updated': '2019-02-20T14:34:08.870-0800'},
        'key': 'TEST-4'}]})

    # Mock GitHub issue information
    elif "https://api.github.com/repos/ucsc-cgp/abc/issues/" in url:
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
        self.patch_pipeline_ids = patch('src.zenhub.ZenHubIssue._get_pipeline_ids', return_value={'Done': 1})
        self.patch_requests = patch('requests.get', side_effect=mock_response)
        self.patch_token = patch('src.access._get_token', return_value='xyz')

        for p in [self.patch_zenhub_children, self.patch_jira_children, self.patch_get_repo_id, self.patch_pipeline_ids,
                  self.patch_requests, self.patch_token]:
            p.start()
            self.addCleanup(p.stop)  # all patches started in this way have to be stopped at the end

        self.ZENHUB_ISSUE_1 = ZenHubIssue(key='1', repo='abc', org='ucsc-cgp')

        self.JIRA_ISSUE_1 = JiraIssue(key='TEST-1', org='ucsc-cgl')

    @patch('src.jira.JiraIssue.add_to_this_epic')
    @patch('src.jira.JiraIssue.remove_from_this_epic')
    @patch('src.zenhub.ZenHubIssue.change_epic_membership')
    def test_sync_epics(self, change_mock_zenhub_epic_membership, remove_from_mock_jira_epic, add_to_mock_jira_epic):

        Sync.sync_epics(self.JIRA_ISSUE_1, self.ZENHUB_ISSUE_1)  # test syncing from Jira to ZenHub
        change_mock_zenhub_epic_membership.assert_has_calls([call(add='2'), call(remove='4')])

        Sync.sync_epics(self.ZENHUB_ISSUE_1, self.JIRA_ISSUE_1)  # test syncing from ZenHub to Jira
        add_to_mock_jira_epic.assert_called_with('TEST-4')
        remove_from_mock_jira_epic.assert_called_with('TEST-2')

