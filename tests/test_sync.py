import unittest
from unittest.mock import patch, call

from src.fake_class import FakeClass
from src.github import GitHubIssue
from src.issue import Issue
from src.jira import JiraIssue
from src.sync import Sync
from src.zenhub import ZenHubIssue


def side_effect(*args, **kwargs):
    print("side effect")
    pass


@patch('requests.Response')
def mock_response(url, mock_response, headers):
    r = mock_response
    if url == "https://api.zenhub.io/p1/repositories/abc/issues/1":
        r.json.return_value = {"estimate": {"value": 2}, "plus_ones": [], "pipeline": {"name": "Review/QA"} , "is_epic": True}
    elif url == "https://api.zenhub.io/p1/repositories/abc/issues/2":
        r.json.return_value = {"estimate": {"value": 2}, "plus_ones": [], "pipeline": {"name": "In Progress"} , "is_epic": False}
    elif url == "https://api.zenhub.io/p1/repositories/abc/issues/3":
        print("called")
        r.json.return_value = {"estimate": {"value": 2}, "plus_ones": [], "pipeline": {"name": "In Progress"} , "is_epic": False}
    elif url == "https://api.zenhub.io/p1/repositories/abc/issues/4":
        r.json.return_value = {"estimate": {"value": 2}, "plus_ones": [], "pipeline": {"name": "In Progress"} , "is_epic": False}
    elif url == "https://ucsc-cgl.atlassian.net/rest/api/latest/search?jql=id=TEST-1":
        r.json.return_value = {'issues': [{
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
            'key': 'TEST-1'}]}
    elif url == "https://ucsc-cgl.atlassian.net/rest/api/latest/search?jql=id=TEST-2":
        r.json.return_value = {'issues': [{
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
                    'key': 'TEST-2'}]}
    elif url == "https://ucsc-cgl.atlassian.net/rest/api/latest/search?jql=id=TEST-3":
        r.json.return_value = {'issues': [{'fields': {
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
                    'key': 'TEST-3'}]}
    elif url == "https://ucsc-cgl.atlassian.net/rest/api/latest/search?jql=id=TEST-4":
        r.json.return_value = {'issues': [{'fields': {
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
    'key': 'TEST-4'}]}
    else:
        raise ValueError(url)
    return r


class TestSync(unittest.TestCase):

    def setUp(self):

        self.patch_github = patch('src.zenhub.GitHubIssue')
        self.patch_ZenHubIssue = patch('requests.get', side_effect=mock_response)
        self.patch_get_repo_id = patch('src.utilities.get_repo_id', return_value='abc')
        self.patch_pipeline_ids = patch('src.zenhub.ZenHubIssue._get_pipeline_ids', return_value={'Done': 1})
        self.patch_epic_children = patch('src.zenhub.ZenHubIssue.get_epic_children', return_value=['3', '4'])

        self.mock_github = self.patch_github.start()
        instance = self.mock_github.return_value
        print(instance)
        instance.jira_key = 'TEST-1'

        self.mock_pipeline_ids = self.patch_pipeline_ids.start()
        self.patch_epic_children.start()
        self.patch_ZenHubIssue.start()
        self.patch_get_repo_id.start()

        self.addCleanup(self.patch_github.stop)
        self.addCleanup(self.patch_pipeline_ids.stop)
        self.addCleanup(self.patch_epic_children.stop)
        self.addCleanup(self.patch_ZenHubIssue.stop)
        self.addCleanup(self.patch_get_repo_id.stop)

        #self.mock_epic_children.return_value = ['3', '4']

        self.ZENHUB_ISSUE_1 = ZenHubIssue(key='1', repo_name='abc')

        self.JIRA_ISSUE_1 = JiraIssue(key='TEST-1')

    @patch('src.jira.JiraIssue.get_epic_children')
    @patch('src.zenhub.ZenHubIssue.get_epic_children')
    @patch('src.jira.JiraIssue.add_to_this_epic', side_effect=side_effect())
    @patch('src.jira.JiraIssue.remove_from_this_epic', side_effect=side_effect())
    @patch('src.zenhub.ZenHubIssue.change_epic_membership', side_effect=side_effect())
    def test_sync_epics(self, change_mock_zenhub_epic_membership, remove_from_mock_jira_epic, add_to_mock_jira_epic,
                        get_mock_zenhub_children, get_mock_jira_children):
        get_mock_jira_children.return_value = ['TEST-2', 'TEST-3']

        # Sync.sync_epics(self.JIRA_ISSUE_1, self.ZENHUB_ISSUE_1)  # test syncing from jira to zenhub
        # print(change_mock_zenhub_epic_membership.mock_calls)
        # change_mock_zenhub_epic_membership.assert_has_calls([call(add='2'), call(remove='4')])

        Sync.sync_epics(self.ZENHUB_ISSUE_1, self.JIRA_ISSUE_1)  # test syncing from zenhub to jira
        add_to_mock_jira_epic.assert_called_with('TEST-4')
        remove_from_mock_jira_epic.assert_called_with('TEST-2')

    def tearDown(self):
        pass

if __name__ == '__main__':
    with patch('__main__.FakeClass') as mock:
        instance = mock.return_value
        instance.jira_key = 'TEST'
        instance.method.return_value = "different value"
        f = FakeClass()
        print(f)
        print(f.method())
        print(f.jira_key)