import re
import unittest
from unittest.mock import patch, call

from src.jira import JiraRepo, JiraIssue
from src.sync import Sync
from src.zenhub import ZenHubRepo, ZenHubIssue


@patch('requests.Response')
def mock_response(url, *args, **kwargs):
    """This test uses four mock issues to simulate a repo to sync. For test_sync_epics, the methods that make API calls
     are mocked out in order to test this method in isolation. For testing syncing an entire repo, all API responses
    are mocked accurately to the format of an actual API response to thoroughly test everything."""

    class MockResponse:
        def __init__(self, json_data, status_code=200):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return self.json_data

    # Mock ZenHub issue information
    if url == 'https://api.zenhub.io/p1/repositories/123/issues/1':
        return MockResponse({'plus_ones': [], 'pipeline': {'name': 'New Issues'},  # no estimate set
                             'is_epic': False})
    elif url == 'https://api.zenhub.io/p1/repositories/123/issues/2':
        return MockResponse({'estimate': {'value': 5}, 'plus_ones': [], 'pipeline': {'name': 'In Progress'},
                             'is_epic': True})
    elif url == 'https://api.zenhub.io/p1/repositories/123/issues/3':
        return MockResponse({'estimate': {'value': 2}, 'plus_ones': [], 'pipeline': {'name': 'Review/QA'},
                             'is_epic': False})
    elif url == 'https://api.zenhub.io/p1/repositories/123/issues/4':
        return MockResponse({'estimate': {'value': 2}, 'plus_ones': [], 'pipeline': {'name': 'In Progress'},
                             'is_epic': False})

    # Mock response for request to get ZenHub epic children
    elif url == 'https://api.zenhub.io/p1/repositories/123/epics/2':
        return MockResponse({'issues': [{'issue_number': 1}, {'issue_number': 3}]})

    elif url == 'https://api.zenhub.io/p1/repositories/123/epics/3':
        return MockResponse({'issues': []})

    # Issue events in ZenHub
    elif url == 'https://api.zenhub.io/p1/repositories/123/issues/1/events':
        return MockResponse(
            [{'created_at': '2019-05-08T22:13:43.512Z',
              'from_estimate': {'value': 8},
              'to_estimate': {'value': 4},
              'type': 'estimateIssue'},
             {'created_at': '2019-04-20T14:12:40.900Z',
              'from_estimate': {'value': 4},
              'to_estimate': {'value': 8},
              'type': 'estimateIssue'}])
    elif 'events' in url:
        return MockResponse([])

    # Mock response for getting pipeline ids
    elif url == 'https://api.zenhub.io/p1/repositories/123/board':
        return MockResponse({'pipelines': [{'id': '100', 'name': 'New Issues'},
                                           {'id': '200', 'name': 'In Progress'},
                                           {'id': '300', 'name': 'Backlog'},
                                           {'id': '400', 'name': 'Icebox'},
                                           {'id': '500', 'name': 'Epics'},
                                           {'id': '600', 'name': 'Review/QA'},
                                           {'id': '700', 'name': 'Done'}]})
    # Mock Jira issue information
    elif url == 'https://ucsc-cgl.atlassian.net/rest/api/latest/search?jql=id=TEST-1':
        return MockResponse({'issues': [{
            'fields': {
                'assignee': None,
                'created': '2019-02-05T14:52:11.501-0800',
                'customfield_10008': None,
                'customfield_10014': None,  # story points
                'description': 'synchronized with github: Repository Name: abc Issue Number: 1',
                'issuetype': {'name': 'Story'},
                'sprint': None,
                'status': {'name': 'In Progress'},
                'summary': 'a test',
                'updated': '2019-05-11T14:34:08.870-0800'},
            'key': 'TEST-1'}]})

    elif url == 'https://ucsc-cgl.atlassian.net/rest/api/latest/search?jql=id=TEST-2':
        return MockResponse({'issues': [{
            'fields': {
                'assignee': None,
                'created': '2019-02-05T14:52:11.501-0800',
                'customfield_10008': None,
                'customfield_10014': 2.0,
                'description': 'synchronized with github: Repository Name: abc Issue Number: 2',
                'issuetype': {'name': 'Story'},
                'sprint': None,
                'status': {'name': 'In Review'},
                'summary': 'Test 2',
                'updated': '2019-04-21T15:55:08.870-0800'},
            'key': 'TEST-2'}]})

    elif url == 'https://ucsc-cgl.atlassian.net/rest/api/latest/search?jql=id=TEST-3':
        return MockResponse({'issues': [{
            'fields': {
                'assignee': None,
                'created': '2019-02-05T14:52:11.501-0800',
                'customfield_10008': None,
                'customfield_10014': 3.0,
                'description': 'synchronized with github: Repository Name: abc Issue Number: 3',
                'issuetype': {'name': 'Epic'},
                'sprint': None,
                'status': {'name': 'Done'},
                'summary': 'Test 3',
                'updated': '2019-02-20T14:34:08.870-0800'},
            'key': 'TEST-3'}]})

    elif url == 'https://ucsc-cgl.atlassian.net/rest/api/latest/search?jql=id=TEST-4':
        return MockResponse({'issues': [{
            'fields': {
                'assignee': None,
                'created': '2019-02-05T14:52:11.501-0800',
                'customfield_10008': None,
                'customfield_10014': 4.0,
                'description': 'synchronized with github: Repository Name: abc Issue Number: 4',
                'issuetype': {'name': 'Story'},
                'sprint': None,
                'status': {'name': 'In Progress'},
                'summary': 'Test 4',
                'updated': '2019-02-20T14:34:08.870-0800'},
            'key': 'TEST-4'}]})

    # Get Jira epic children
    elif "https://ucsc-cgl.atlassian.net/rest/api/latest/search?jql=cf[10008]='TEST-2'" in url:
        return MockResponse({'issues': []})

    elif "https://ucsc-cgl.atlassian.net/rest/api/latest/search?jql=cf[10008]='TEST-3'" in url:
        return MockResponse({'issues': [{'key': 'TEST-2'}, {'key': 'TEST-4'}]})  # TEST-2 and TEST-4 belong to TEST-3

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
            'updated_at': '2019-04-21T22:51:33Z',
            'number': match_obj.group(1)
            })

    # Mock response for getting repo id
    elif url == 'https://api.github.com/repos/ucsc-cgp/abc':
        return MockResponse({'id': 123})

    # Return a blank response indicating a successful update. Some methods expect a 204 response on success
    elif any(x in url for x in ['transitions', 'issue/TEST-', 'epic/TEST-2/issue', 'epic/none/issue']):
        return MockResponse(None, status_code=204)

    # Others expect a 200 response
    elif any(x in url for x in ['estimate', 'moves', 'convert_to_issue', 'convert_to_epic', 'update_issues']):
        return MockResponse(None)

    else:
        raise ValueError(url)


class TestSync(unittest.TestCase):

    def setUp(self):
        """Patch all API requests with put, post, and get. Initialize test boards."""

        # NOTE it's important that the path here refers to where the method is used - the reference to it that's
        # imported in zenhub.py or jira.py, not the original location.
        self.jira_put = patch('src.jira.requests.put', side_effect=mock_response).start()
        self.jira_post = patch('src.jira.requests.post', side_effect=mock_response).start()
        self.zenhub_put = patch('src.zenhub.requests.put', side_effect=mock_response).start()
        self.zenhub_post = patch('src.zenhub.requests.post', side_effect=mock_response).start()

        self.patch_requests = patch('requests.get', side_effect=mock_response).start()
        self.patch_token = patch('src.access._get_token', return_value='token').start()

        self.ZENHUB_REPO = ZenHubRepo(repo_name='abc', org='ucsc-cgp', issues=['1', '2', '3', '4'])
        self.ZENHUB_ISSUE_1 = self.ZENHUB_REPO.issues['1']

        self.JIRA_REPO = JiraRepo(repo_name='TEST', jira_org='ucsc-cgl', issues=['TEST-1', 'TEST-2', 'TEST-3', 'TEST-4'])
        self.JIRA_ISSUE_1 = self.JIRA_REPO.issues['TEST-1']

    @patch('src.jira.JiraIssue.change_epic_membership')
    @patch('src.zenhub.ZenHubIssue.change_epic_membership')
    @patch('src.zenhub.get_repo_id', return_value={'repo_id': '123'})
    @patch('src.zenhub.ZenHubIssue.get_epic_children', return_value=['3', '4'])
    @patch('src.jira.JiraIssue.get_epic_children', return_value=['TEST-1', 'TEST-3'])
    def test_sync_epics(self, jira_children, zen_children, repo_id, change_zen_epic, change_jira_epic):
        """Test the sync_epics method in isolation"""

        j_epic = JiraIssue(repo=self.JIRA_REPO, key='TEST-2')
        z_epic = ZenHubIssue(repo=self.ZENHUB_REPO, key='2')

        Sync.sync_epics(j_epic, z_epic)  # test syncing from Jira to ZenHub
        self.assertEqual(change_zen_epic.call_args_list, [call(add='1'), call(remove='4')])

        zen_children.return_value = ['3', '4']  # Not sure why but this needs to be reset

        Sync.sync_epics(z_epic, j_epic)  # test syncing from ZenHub to Jira
        self.assertEqual(change_jira_epic.call_args_list, [call(add='TEST-4'), call(remove='TEST-1')])

    @patch('src.jira.requests.put', side_effect=mock_response)
    @patch('src.jira.requests.post', side_effect=mock_response)
    def test_sync_board_zen_to_jira(self, jira_post, jira_put):
        """Test syncing a repo from ZenHub to Jira.
        Assert that API calls are made in the correct order with correct data."""

        Sync.sync_board(self.ZENHUB_REPO, self.JIRA_REPO)

        # TEST-1 is updated
        self.assertEqual(jira_post.call_args_list[0][1]['json'], {'transition': {'id': 61}})  # TEST-1 to new issue
        self.assertEqual(jira_put.call_args_list[0][1]['json'], {'fields': {'description': 'Issue Number: TEST-1',
                                                                            'issuetype': {'name': 'Story'},
                                                                            'summary': 'a test'}})
        # TEST-2 is updated
        self.assertEqual(jira_post.call_args_list[1][1]['json'], {'transition': {'id': 21}})
        self.assertEqual(jira_put.call_args_list[1][1]['json'], {'fields': {'description': 'Issue Number: TEST-2',
                                                                            'issuetype': {'name': 'Epic'},
                                                                            'summary':'Test 2',
                                                                            'customfield_10014': 5}})
        # TEST-1 and TEST-3 are added to epic TEST-2
        self.assertEqual(jira_post.call_args_list[2][1]['json'], {'issues': ['TEST-1']})
        self.assertEqual(jira_post.call_args_list[3][1]['json'], {'issues': ['TEST-3']})

        # TEST-3 is updated to Story, causing TEST-2 and TEST-4 to no longer be its children
        self.assertEqual(jira_post.call_args_list[4][1]['json'], {'transition': {'id': 41}})
        self.assertEqual(jira_put.call_args_list[2][1]['json'], {'fields': {'description': 'Issue Number: TEST-3',
                                                                            'issuetype': {'name': 'Story'},
                                                                            'summary': 'Test 3',
                                                                            'customfield_10014': 2}})
        # TEST-4 is updated
        self.assertEqual(jira_post.call_args_list[5][1]['json'], {'transition': {'id': 21}})
        self.assertEqual(jira_put.call_args_list[3][1]['json'], {'fields': {'description': 'Issue Number: TEST-4',
                                                                            'issuetype': {'name': 'Story'},
                                                                            'summary': 'Test 4',
                                                                            'customfield_10014': 2}})

    @patch('src.github.requests.patch', side_effect=mock_response)
    @patch('src.zenhub.requests.put', side_effect=mock_response)
    @patch('src.zenhub.requests.post', side_effect=mock_response)
    def test_sync_board_jira_to_zen(self, zenhub_post, zenhub_put, github_patch):
        """Test syncing a repo from Jira to ZenHub.
        Assert that API calls are made in the correct order with correct data."""

        Sync.sync_board(self.JIRA_REPO, self.ZENHUB_REPO)

        # 1 is updated in ZenHub and GitHub
        self.assertEqual(zenhub_post.call_args_list[0][1]['json'], {'pipeline_id': '200', 'position': 'top'})
        self.assertEqual(zenhub_put.call_args_list[0][1]['json'], {'estimate': 0})
        self.assertEqual(github_patch.call_args_list[0][1]['json'], {'title': 'a test',
                                                                     'body': 'synchronized with github: Repository Name: abc Issue Number: 1',
                                                                     'labels': []})

        # 2 is converted to issue and updated in ZenHub and GitHub
        self.assertEqual(zenhub_post.call_args_list[1][1]['json'], {'issues': [{'repo_id': '123', 'issue_number': '2'}]})
        self.assertEqual(zenhub_post.call_args_list[2][1]['json'], {'pipeline_id': '600', 'position': 'top'})
        self.assertEqual(zenhub_put.call_args_list[1][1]['json'], {'estimate': 2.0})
        self.assertEqual(github_patch.call_args_list[1][1]['json'], {'title': 'Test 2',
                                                                     'body': 'synchronized with github: Repository Name: abc Issue Number: 2',
                                                                     'labels': []})
        # 3 is converted to epic and updated in ZenHub and GitHub
        self.assertEqual(zenhub_post.call_args_list[3][1]['json'], {'issues': [{'repo_id': '123', 'issue_number': '3'}]})
        self.assertEqual(zenhub_post.call_args_list[4][1]['json'], {'pipeline_id': '700', 'position': 'top'})
        self.assertEqual(zenhub_put.call_args_list[2][1]['json'], {'estimate': 3.0})
        self.assertEqual(github_patch.call_args_list[2][1]['json'], {'title': 'Test 3',
                                                                     'body': 'synchronized with github: Repository Name: abc Issue Number: 3',
                                                                     'labels': []})
        # 2 and 4 are added to epic 3 through ZenHub
        self.assertEqual(zenhub_post.call_args_list[5][1]['json'], {'add_issues': [{'repo_id': 123, 'issue_number': 2}]})
        self.assertEqual(zenhub_post.call_args_list[6][1]['json'], {'add_issues': [{'repo_id': 123, 'issue_number': 4}]})

        # 4 is updated in ZenHub and GitHub
        self.assertEqual(zenhub_post.call_args_list[7][1]['json'], {'pipeline_id': '200', 'position': 'top'})
        self.assertEqual(zenhub_put.call_args_list[3][1]['json'], {'estimate': 4.0})
        self.assertEqual(github_patch.call_args_list[3][1]['json'], {'title': 'Test 4',
                                                                     'body': 'synchronized with github: Repository Name: abc Issue Number: 4',
                                                                     'labels': []})

    @patch('src.sync.Sync.sync_from_specified_source')
    def test_mirror_sync(self, sync):
        """Assert that two issues are synced from Jira to ZenHub and two from ZenHub to Jira, based on timestamps."""
        Sync.mirror_sync(self.JIRA_REPO, self.ZENHUB_REPO)

        # Call args list has the addresses of issues being synced, which change each time, so just look at issue type
        called_with = [(call[0][0].__class__.__name__, call[0][1].__class__.__name__) for call in sync.call_args_list]
        expected = [('JiraIssue', 'ZenHubIssue'), ('JiraIssue', 'ZenHubIssue'), ('ZenHubIssue', 'JiraIssue'),
                    ('ZenHubIssue', 'JiraIssue')]
        self.assertEqual(called_with, expected)

    def tearDown(self):
        patch.stopall()  # Stop all the patches that were started in setUp





