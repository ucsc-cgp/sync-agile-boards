#!/usr/env/python3

import unittest
from unittest.mock import patch, MagicMock
from src.zenhub import ZenHub


def mocked_response(*args, **kwargs):
    """Create class to mock response in _get_info method."""

    class MockResponse:
        def __init__(self, json_data, status_code, reason):
            self.json_data = json_data
            self.status_code = status_code
            self.reason = reason

        def json(self):
            return self.json_data

    # Careful, args needs to be a tuple, and that always ends with a "," character in Python!!
    if args == ('https://api.zenhub.io/p1/repositories/123456789/issues/42',) and \
            kwargs == {'headers': {'X-Authentication-Token': 99999999, 'Content-Type': 'application/json'}, 'verify': False}:

        return MockResponse(
            {'estimate': {'value': 2},
             'plus_ones': [],
             'pipeline': {'name': 'Review/QA'},
             'is_epic': False},
            200,
            'Ok'
        )
    elif args == ('https://api.zenhub.io/p1/repositories/123456789/issues/55555555',) and \
            kwargs == {'headers': {'X-Authentication-Token': 99999999, 'Content-Type': 'application/json'}, 'verify': False}:
        return MockResponse(
            {'message': 'Issue not found'},
            404,
            'Not found'
        )
    elif args == ('https://api.zenhub.io/p1/repositories/100000000/issues/55555555',) and \
            kwargs == {'headers': {'X-Authentication-Token': 99999999, 'Content-Type': 'application/json'}, 'verify': False}:
        return MockResponse(
            {'message': 'Invalid Field for repo_id: repo_id is a required field'},
            422,
            'Unprocessable Entity'
        )
    elif '/board' in args[0]:  # The request used for determining pipeline ids in _get_pipeline_ids().
        return MockResponse({'pipelines': [{'id': 12345, 'name': 'Done', 'issues': []}]}, 200, 'OK')
    else:
        raise RuntimeError(args, kwargs)


class ZenHub_with_mocked_token(ZenHub):
    def __init__(self, repo_name=None, issue=None):
        self.access_params = {'options': 'https://api.zenhub.io/p1/repositories', 'api_token': 99999999}
        self.headers = {'X-Authentication-Token': self.access_params['api_token'], 'Content-Type': 'application/json'}
        self.repo_name = repo_name
        self.repo_id = self._get_repo_id(repo_name)
        self.issue = str(issue)
        self.url = self._generate_url()


class TestZenHub(unittest.TestCase):

    @patch('src.zenhub.ZenHub._generate_url')
    @patch('src.zenhub.ZenHub._get_repo_id')
    @patch('requests.get', side_effect=mocked_response)
    def test_happy_path(self, mocked_get_info, mock_repo_id, mock_generate_url):
        repo_name = 'azul'
        issue = 42

        mock_repo_id.return_value = 123456789
        mock_generate_url.return_value = (
            f"https://api.zenhub.io/p1/repositories/{mock_repo_id.return_value}/issues/{issue}")

        res = ZenHub_with_mocked_token(repo_name=repo_name, issue=issue)

        self.assertEqual(res.repo_id, mock_repo_id.return_value, 'incorrect repo_id')
        self.assertEqual(res.issue, str(issue), 'incorrect issue number')
        self.assertEqual(res.url, mock_generate_url.return_value, 'incorrect URL')

        # Most import assertion:
        self.assertEqual(res.get_info(), {'Story number': str(issue),
                                          'Repository': repo_name,
                                          'Pipeline': 'Review/QA',
                                          'Storypoints': 2,
                                          'Timestamp': 'Not available'},
                         'get_info has incorrect output')

    @patch('src.zenhub.ZenHub._generate_url')
    @patch('src.zenhub.ZenHub._get_repo_id')
    @patch('requests.get', side_effect=mocked_response)
    def test_existing_repo_ID_nonexisting_issue_num(self, mocked_get_info, mock_repo_id, mock_generate_url):
        repo_name = 'azul'
        issue = 55555555

        mock_repo_id.return_value = 123456789
        mock_generate_url.return_value = (
            f"https://api.zenhub.io/p1/repositories/{mock_repo_id.return_value}/issues/{issue}")

        res = ZenHub_with_mocked_token(repo_name=repo_name, issue=issue)

        self.assertEqual(res.repo_id, mock_repo_id.return_value, 'incorrect repo_id')
        self.assertEqual(res.issue, str(issue), 'incorrect issue number')
        self.assertEqual(res.url, mock_generate_url.return_value, 'incorrect URL')

        # Most import assertion:
        self.assertEqual(res.get_info(), {'message': 'Issue not found'}, 'get_info has incorrect output')

    @patch('src.zenhub.ZenHub._generate_url')
    @patch('src.zenhub.ZenHub._get_repo_id')
    @patch('requests.get', side_effect=mocked_response)
    def test_nonexisting_repo_ID_nonexisting_issue_num(self, mocked_get_info, mock_repo_id, mock_generate_url):
        repo_name = 'azul'
        issue = 55555555

        mock_repo_id.return_value = 100000000
        mock_generate_url.return_value = (
            f"https://api.zenhub.io/p1/repositories/{mock_repo_id.return_value}/issues/{issue}")

        res = ZenHub_with_mocked_token(repo_name=repo_name, issue=issue)

        self.assertEqual(res.repo_id, mock_repo_id.return_value, 'incorrect repo_id')
        self.assertEqual(res.issue, str(issue), 'incorrect issue number')
        self.assertEqual(res.url, mock_generate_url.return_value, 'incorrect URL')

        # Most import assertion:
        self.assertEqual(res.get_info(), {'message': 'Invalid Field for repo_id: repo_id is a required field'},
                         'get_info has incorrect output')

    @patch('src.zenhub.ZenHub._get_repo_id')
    @patch('src.zenhub.ZenHub._generate_url', return_value='https://foo.bar')
    def test_generate_url(self, mock_generate_url, mock_repo_id):

        mock_repo_id.return_value = '100000000'  # Needed for generating repo_ids in init.
        zen = ZenHub(repo_name='baz', issue=42)
        self.assertEqual(zen.url, 'https://foo.bar', 'URL not generated correctly')

    @patch('os.path.join')
    @patch('requests.put')
    def test_update_issue_points(self, mock_put_change_points, mock_url_creator):
        """Test that ZenHub.update_issue_points() works."""
        issue_num = 42
        new_points = 3
        mock_url_creator.return_value = f'https://api.zenhub.io/p1/repositories/issues/{issue_num}/estimate'

        zen = ZenHub(repo_name='azul', issue=issue_num)
        zen._update_issue_points(new_points)

        mock_put_change_points.assert_called()
        request_args = list(mock_put_change_points.call_args)

        # Check that the url is in the request
        self.assertIn((mock_url_creator.return_value,), request_args)  # MagicMock stores this as a tuple.

        # Check that the json_dict is in the put request.
        expected_dict = {'headers': zen.headers.copy()}
        expected_dict.update({'json': {'estimate': new_points}})
        self.assertIn(expected_dict, request_args)

    @patch('os.path.join')
    @patch('requests.post')
    def test_update_issue_pipeline(self, mock_post_change_pipeline, mock_url_creator):
        """Test that ZenHub.update_issue_pipeline() works."""
        issue_num = 42
        mock_url_creator.return_value = f'https://api.zenhub.io/p1/repositories/issues/{issue_num}/moves'

        zen = ZenHub(repo_name='azul', issue=issue_num)
        zen.pipeline_ids = {'Icebox': 12345}
        zen._update_issue_pipeline('Icebox')

        mock_post_change_pipeline.assert_called()
        request_args = list(mock_post_change_pipeline.call_args)

        # Check that the url is in the request
        self.assertIn((mock_url_creator.return_value,), request_args)  # MagicMock stores this as a tuple.

        # Check that the json_dict is in the put request.
        expected_dict = {'headers': zen.headers.copy()}
        expected_dict.update({'json': {'pipeline_id': 12345, 'position': 'top'}})
        self.assertIn(expected_dict, request_args)

    @patch('os.path.join')
    @patch('requests.put')
    def test_update_issue_to_epic(self, mock_put_make_epic, mock_url_creator):
        """Test that ZenHub.update_issue_to_epic() works."""
        issue_num = 42
        repo_name = 'azul'
        mock_url_creator.return_value = f'https://api.zenhub.io/p1/repositories/issues/{issue_num}/convert_to_epic'

        zen = ZenHub(repo_name=repo_name, issue=issue_num)
        zen.repo_id = 12345
        zen._update_issue_to_epic()

        mock_put_make_epic.assert_called()
        request_args = list(mock_put_make_epic.call_args)

        # Check that the url is in the request
        self.assertIn((mock_url_creator.return_value,), request_args)  # MagicMock stores this as a tuple.

        # Check that the json_dict is in the put request.
        expected_dict = {'headers': zen.headers.copy()}
        expected_dict.update({'json': {'issues': [{'repo_id': zen.repo_id, 'issue_number': str(issue_num)}]}})
        self.assertIn(expected_dict, request_args)

    @patch('src.zenhub.ZenHub._update_issue_to_epic')
    @patch('src.zenhub.ZenHub._update_issue_pipeline')
    @patch('src.zenhub.ZenHub._update_issue_points')
    def test_update_issue(self, mock_update_issue_points, mock_update_issue_pipeline, mock_update_issue_to_epic):
        """Test that ZenHub.update_ticket() works."""
        issue_num = 42
        repo_name = 'azul'

        zen = ZenHub(repo_name=repo_name, issue=issue_num)
        zen.update_issue(points=3, pipeline='Icebox', to_epic=True)

        mock_update_issue_points.assert_called()
        mock_update_issue_pipeline.assert_called()
        mock_update_issue_to_epic.assert_called()

    @patch('requests.get', side_effect=mocked_response)
    def test_get_pipeline_ids(self, mocked_get_info):
        """Test that ZenHub._get_pipeline_ids() works."""
        path_to_token = '~/foo/bar/baz.txt'
        repo_name = 'azul'
        issue = 55555555

        res = ZenHub(repo_name=repo_name, issue=issue)

        self.assertEqual(res._get_pipeline_ids(), {'Done': 12345})


if __name__ == '__main__':
    unittest.main()
