#!/usr/env/python3

import pytz
import datetime
import re
import unittest
from unittest.mock import patch

from src.zenhub import ZenHubRepo


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
    if args == ('https://api.zenhub.io/p1/repositories/123456789/issues/42',):
        return MockResponse(
            {'estimate': {'value': 2},
             'plus_ones': [],
             'pipeline': {'name': 'Review/QA'},
             'is_epic': False},
            200,
            'OK'
        )

    # Issue events
    elif args == ('https://api.zenhub.io/p1/repositories/123456789/issues/42/events',):
        return MockResponse(
            [{'created_at': '2019-05-08T22:13:43.512Z',
              'from_estimate': {'value': 8},
              'to_estimate': {'value': 4},
              'type': 'estimateIssue'},
             {'created_at': '2019-04-20T14:12:40.900Z',
              'from_estimate': {'value': 4},
              'to_estimate': {'value': 8},
              'type': 'estimateIssue'}],
            200,
            'OK'
        )

    # Non-existent issue number:
    elif args == ('https://api.zenhub.io/p1/repositories/123456789/issues/55555555',):
        return MockResponse(
            {'message': 'Issue not found'},
            404,
            'Not Found'
        )
    # Non-existent repo number
    elif args == ('https://api.zenhub.io/p1/repositories/100000000/issues/55555555',):
        return MockResponse(
            {'message': 'Invalid Field for repo_id: repo_id is a required field'},
            422,
            'Unprocessable Entity'
        )
    elif '/board' in args[0]:  # The request used for determining pipeline ids in _get_pipeline_ids().
        return MockResponse({'pipelines': [{'id': 1, 'name': 'Done', 'issues': []}, {'id': 2, 'name': 'Review/QA',
                                                                                     'issues': []}]}, 200, 'OK')

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
        self.patch_repo_id = patch('src.zenhub.ZenHubRepo.get_repo_id', return_value='123456789').start()
        self.patch_requests = patch('requests.get', side_effect=mocked_response).start()
        self.patch_token = patch('src.access._get_token', return_value='99999999').start()
        self.github_patch = patch('src.github.requests.patch', side_effect=mocked_response).start()

        self.board = ZenHubRepo(repo_name='abc', org='ucsc-cgp', issues=['42'])
        self.zen = self.board.issues['42']

    def test_happy_init(self):
        self.assertEqual(self.zen.story_points, 2)
        self.assertEqual(self.zen.pipeline, 'Review/QA')
        self.assertEqual(self.zen.issue_type, 'Story')

    @patch('src.zenhub.requests.put')
    def test_update_issue_points(self, mock_put_request):
        """Test that ZenHub.update_issue_points() works."""
        mock_put_request.return_value.status_code = 200
        self.zen._update_issue_points()

        request_args = list(mock_put_request.call_args)

        # Check that the put request is made correctly.
        expected_dict = {'headers': self.board.headers.copy()}
        expected_dict.update({'json': {'estimate': 2}})
        self.assertIn(expected_dict, request_args)

    @patch('src.zenhub.ZenHubRepo.get_repo_id', return_value='123456789')
    @patch('os.path.join')
    @patch('requests.post')
    def test_update_issue_pipeline(self, mock_post_change_pipeline, mock_url_creator, mock_repo_id):
        """Test that ZenHub.update_issue_pipeline() works."""

        mock_url_creator.return_value = f'https://api.zenhub.io/p1/repositories/123456789/issues/42/moves'
        mock_post_change_pipeline.return_value.status_code = 200

        self.zen._update_issue_pipeline()

        mock_post_change_pipeline.assert_called()
        request_args = list(mock_post_change_pipeline.call_args)

        # Check that the url is in the request
        self.assertIn((mock_url_creator.return_value,), request_args)  # MagicMock stores this as a tuple.

        # Check that the json_dict is in the put request.
        expected_dict = {'headers': self.board.headers.copy()}
        expected_dict.update({'json': {'pipeline_id': 2, 'position': 'top'}})
        self.assertIn(expected_dict, request_args)

    @patch('src.zenhub.ZenHubRepo.get_repo_id', return_value='123456789')
    @patch('os.path.join')
    @patch('requests.post')
    def test_update_issue_to_epic(self, mock_requests_post, mock_url_creator, mock_repo_id):
        """Test that ZenHub.update_issue_to_epic() works."""

        mock_url_creator.return_value = \
            f'https://api.zenhub.io/p1/repositories/123456789/issues/42/convert_to_epic'
        mock_requests_post.return_value.status_code = 200

        self.zen.promote_issue_to_epic()

        mock_requests_post.assert_called()
        request_args = list(mock_requests_post.call_args)

        # Check that the url is in the request
        self.assertIn((mock_url_creator.return_value,), request_args)  # MagicMock stores this as a tuple.

        # Check that the json_dict is in the put request.
        expected_dict = {'headers': self.board.headers.copy()}
        expected_dict.update({'json': {'issues': [{'repo_id': self.board.id, 'issue_number': str(42)}]}})
        self.assertIn(expected_dict, request_args)

    @patch('requests.get', side_effect=mocked_response)
    def test_get_most_recent_event(self, get):
        """Test that get_most_recent_event() gets a correct datetime object from a list of events"""
        expected = datetime.datetime(2019, 5, 8, 22, 13, 43, tzinfo=pytz.timezone('UTC'))
        self.assertEqual(self.zen.get_most_recent_event(), expected)

    def tearDown(self):
        patch.stopall()  # Stop all patches started in setUp()


if __name__ == '__main__':
    unittest.main()
