#!/usr/env/python3

import re
import unittest
from unittest.mock import patch
from src.zenhub import ZenHub, ZenHubBoard, ZenHubIssue


def mocked_response(*args, **kwargs):
    """Create class to mock response in _get_info method."""

    class MockResponse:
        def __init__(self, json_data, status_code, reason):
            self.json_data = json_data
            self.status_code = status_code
            self.reason = reason

        def json(self):
            return self.json_data

    # Careful, args needs to be a tuple, and that always ends with a ',' character in Python!!
    # Happy Path:
    if args == ('https://api.zenhub.io/p1/repositories/123456789/issues/42',) and \
            kwargs == {'headers': {'X-Authentication-Token': '99999999', 'Content-Type': 'application/json'}}:
        return MockResponse(
            {'estimate': {'value': 2},
             'plus_ones': [],
             'pipeline': {'name': 'Review/QA'},
             'is_epic': False},
            200,
            'Ok'
        )
    # Non-existent issue number:
    elif args == ('https://api.zenhub.io/p1/repositories/123456789/issues/55555555',) and \
            kwargs == {'headers': {'X-Authentication-Token': '99999999', 'Content-Type': 'application/json'}}:
        return MockResponse(
            {'message': 'Issue not found'},
            404,
            'Not found'
        )
    # Non-existent repo number
    elif args == ('https://api.zenhub.io/p1/repositories/100000000/issues/55555555',) and \
            kwargs == {'headers': {'X-Authentication-Token': '99999999', 'Content-Type': 'application/json'}}:
        return MockResponse(
            {'message': 'Invalid Field for repo_id: repo_id is a required field'},
            422,
            'Unprocessable Entity'
        )
    elif '/board' in args[0]:  # The request used for determining pipeline ids in _get_pipeline_ids().
        return MockResponse({'pipelines': [{'id': 1, 'name': 'Done', 'issues': []}, {'id': 2, 'name': 'Icebox', 'issues': []}]}, 200, 'OK')

    elif 'https://api.github.com/repos/ucsc-cgp/abc/issues/' in args[0]:  # Mock GitHub issue information
        match_obj = re.search(r'issues/(\d*)', args[0])
        return MockResponse({
            'assignee': None,
            'assignees': [],
            'body': 'Issue Number: TEST-' + match_obj.group(1),  # We just want this to fill in the issue number field
            'created_at': '2019-02-20T22:51:33Z',
            'milestone': None,
            'title': None,
            'updated_at': '2019-02-20T22:51:33Z',
            'number': match_obj.group(1)
        }, 200, 'OK')
    else:
        raise RuntimeError(args, kwargs)


class TestZenHub(unittest.TestCase):

    def setUp(self):
        self.patch_repo_id = patch('src.zenhub.get_repo_id', return_value={'repo_id': '123456789'})
        self.patch_requests = patch('requests.get', side_effect=mocked_response)
        self.patch_token = patch('src.access._get_token', return_value='99999999')
        for p in [self.patch_repo_id, self.patch_requests, self.patch_token]:
            p.start()
            self.addCleanup(p.stop)

        self.board = ZenHubBoard(repo='abc', org='ucsc-cgp', issues=['42'])
        self.zen = self.board.issues['42']

    @patch('src.zenhub.get_access_params')
    @patch('src.zenhub.get_repo_id')
    @patch('src.zenhub.ZenHub._generate_url')
    @patch('src.zenhub.requests.get', side_effect=mocked_response)
    def test_happy_path(self, mocked_get_info, mock_generate_url, mock_repo_id, mock_access_params):
        org_name = 'foo'
        repo_name = 'bar'
        issue = 42

        # Construct all mocked return values used in instance of class ZenHub:
        mock_repo_id.return_value = {'repo_id': '123456789', 'status_code': 200}
        mock_generate_url.return_value = (
            f"https://api.zenhub.io/p1/repositories/{mock_repo_id.return_value['repo_id']}/issues/{issue}")
        mock_access_params.return_value = {'api_token': '99999999'}

        res = ZenHub(org_name, repo_name, issue)

        self.assertEqual(res.repo_id, mock_repo_id.return_value['repo_id'], 'incorrect repo_id')
        self.assertEqual(res.issue, str(issue), 'incorrect issue number')
        self.assertEqual(res.url, mock_generate_url.return_value, 'incorrect URL')

        # Most import assertion:
        self.assertEqual(res.get_info(), {'Story number': str(issue),
                                          'Repository': repo_name,
                                          'Pipeline': 'Review/QA',
                                          'Storypoints': 2,
                                          'Timestamp': 'Not available'},
                         'get_info has incorrect output')

    @patch('src.zenhub.get_access_params')
    @patch('src.zenhub.get_repo_id')
    @patch('src.zenhub.ZenHub._generate_url')
    @patch('requests.get', side_effect=mocked_response)
    def test_existing_repo_ID_nonexisting_issue_num(self, mocked_get_info,
                                                    mock_generate_url, mock_repo_id, mock_access_params):
        org_name = 'foo'
        repo_name = 'bar'
        issue = 55555555

        # Construct all mocked return values used in instance of class ZenHub:
        mock_repo_id.return_value = {'repo_id': '123456789', 'status_code': 200}
        mock_generate_url.return_value = (
            f"https://api.zenhub.io/p1/repositories/{mock_repo_id.return_value['repo_id']}/issues/{issue}")
        mock_access_params.return_value = {'api_token': '99999999'}

        res = ZenHub(org_name=org_name, repo_name=repo_name, issue=issue)

        self.assertEqual(res.repo_id, mock_repo_id.return_value['repo_id'], 'incorrect repo_id')
        self.assertEqual(res.issue, str(issue), 'incorrect issue number')
        self.assertEqual(res.url, mock_generate_url.return_value, 'incorrect URL')

        # Most import assertion:
        self.assertEqual(res.get_info(), {'message': 'Issue not found'}, 'get_info has incorrect output')

    @patch('src.zenhub.ZenHub._generate_url')
    @patch('src.zenhub.get_repo_id')
    @patch('requests.get', side_effect=mocked_response)
    def test_nonexisting_repo_ID_nonexisting_issue_num(self, mocked_get_info, mock_repo_id, mock_generate_url):
        org_name = 'foo'
        repo_name = 'baz'
        issue = 55555555

        mock_repo_id.return_value = {'repo_id':100000000, 'status_code': 404}

        self.assertRaises(ValueError, ZenHub, org_name=org_name, repo_name=repo_name, issue=issue)

    @patch('src.zenhub.get_repo_id', return_value={'repo_id': 101, 'status_code': 200})
    @patch('src.zenhub.ZenHub._generate_url', return_value='https://foo.bar')
    def test_generate_url(self, mock_generate_url, mock_repo_id):

        zen = ZenHub(org_name='foo', repo_name='bar', issue=42)
        self.assertEqual(zen.org_name, 'foo')
        self.assertEqual(zen.repo_name, 'bar')
        self.assertTrue(isinstance(zen.repo_id, str), 'instance attribute repo_id must be of type str')
        self.assertEqual(zen.url, 'https://foo.bar', 'URL not generated correctly')

    @patch('src.zenhub.requests.put')
    def test_update_issue_points(self, mock_put_request):
        """Test that ZenHub.update_issue_points() works."""
        mock_put_request.return_value.status_code = 200
        self.zen._update_issue_points(3)

        request_args = list(mock_put_request.call_args)

        # Check that the put request is made correctly.
        expected_dict = {'headers': self.zen.headers.copy()}
        expected_dict.update({'json': {'estimate': 3}})
        self.assertIn(expected_dict, request_args)

    @patch('src.zenhub.get_repo_id', return_value={'repo_id': 123456789, 'status_code': 200})
    @patch('os.path.join')
    @patch('requests.post')
    def test_update_issue_pipeline(self, mock_post_change_pipeline, mock_url_creator, mock_repo_id):
        """Test that ZenHub.update_issue_pipeline() works."""

        mock_url_creator.return_value = f'https://api.zenhub.io/p1/repositories/123456789/issues/42/moves'
        mock_post_change_pipeline.return_value.status_code = 200

        self.zen._update_issue_pipeline('Icebox')

        mock_post_change_pipeline.assert_called()
        request_args = list(mock_post_change_pipeline.call_args)

        # Check that the url is in the request
        self.assertIn((mock_url_creator.return_value,), request_args)  # MagicMock stores this as a tuple.

        # Check that the json_dict is in the put request.
        expected_dict = {'headers': self.zen.headers.copy()}
        expected_dict.update({'json': {'pipeline_id': 2, 'position': 'top'}})
        self.assertIn(expected_dict, request_args)

    @patch('src.zenhub.get_repo_id', return_value={'repo_id': 123456789, 'status_code': 200})
    @patch('os.path.join')
    @patch('requests.post')
    def test_update_issue_to_epic(self, mock_requests_post, mock_url_creator, mock_repo_id):
        """Test that ZenHub.update_issue_to_epic() works."""

        mock_url_creator.return_value = f'https://api.zenhub.io/p1/repositories/123456789/issues/42/convert_to_epic'
        mock_requests_post.return_value.status_code = 200

        self.zen.promote_issue_to_epic()

        mock_requests_post.assert_called()
        request_args = list(mock_requests_post.call_args)

        # Check that the url is in the request
        self.assertIn((mock_url_creator.return_value,), request_args)  # MagicMock stores this as a tuple.

        # Check that the json_dict is in the put request.
        expected_dict = {'headers': self.zen.headers.copy()}
        expected_dict.update({'json': {'issues': [{'repo_id': self.zen.repo_id, 'issue_number': str(42)}]}})
        self.assertIn(expected_dict, request_args)


if __name__ == '__main__':
    unittest.main()
