#!/usr/env/python3

import unittest
from unittest.mock import patch
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
            kwargs == {'headers': {'X-Authentication-Token': 99999999}, 'verify': False}:
        return MockResponse(
            {'estimate': {'value': 2},
             'plus_ones': [],
             'pipeline': {'name': 'Review/QA'},
             'is_epic': False},
            200,
            'Ok'
        )
    elif args == ('https://api.zenhub.io/p1/repositories/123456789/issues/55555555',) and \
            kwargs == {'headers': {'X-Authentication-Token': 99999999}, 'verify': False}:
        return MockResponse(
            {'message': 'Issue not found'},
            404,
            'Not found'
        )
    elif args == ('https://api.zenhub.io/p1/repositories/100000000/issues/55555555',) and \
            kwargs == {'headers': {'X-Authentication-Token': 99999999}, 'verify': False}:
        return MockResponse(
            {'message': 'Invalid Field for repo_id: repo_id is a required field'},
            422,
            'Unprocessable Entity'
        )
    else:
        assert False



class TestZenHub(unittest.TestCase):

    @patch('src.zenhub.ZenHub._generate_url')
    @patch('src.zenhub.ZenHub._get_repo_id')
    @patch('src.zenhub.ZenHub._get_token')
    @patch('requests.get', side_effect=mocked_response)
    def test_happy_path(self, mocked_get_info, mock_get_token, mock_repo_id, mock_generate_url):
        path_to_token = '~/foo/bar/baz.txt'
        repo_name = 'azul'
        issue = 42

        mock_get_token.return_value = 99999999
        mock_repo_id.return_value = 123456789
        mock_generate_url.return_value = (
            f"https://api.zenhub.io/p1/repositories/{mock_repo_id.return_value}/issues/{issue}")

        res = ZenHub(path_to_token=path_to_token,
                     repo_name=repo_name,
                     issue=issue)

        self.assertEqual(res.token, mock_get_token.return_value, 'incorrect token')
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
    @patch('src.zenhub.ZenHub._get_token')
    @patch('requests.get', side_effect=mocked_response)
    def test_existing_repo_ID_nonexisting_issue_num(self, mocked_get_info, mock_get_token, mock_repo_id, mock_generate_url):
        path_to_token = '~/foo/bar/baz.txt'
        repo_name = 'azul'
        issue = 55555555

        mock_get_token.return_value = 99999999
        mock_repo_id.return_value = 123456789
        mock_generate_url.return_value = (
            f"https://api.zenhub.io/p1/repositories/{mock_repo_id.return_value}/issues/{issue}")

        res = ZenHub(path_to_token=path_to_token,
                     repo_name=repo_name,
                     issue=issue)

        self.assertEqual(res.token, mock_get_token.return_value, 'incorrect token')
        self.assertEqual(res.repo_id, mock_repo_id.return_value, 'incorrect repo_id')
        self.assertEqual(res.issue, str(issue), 'incorrect issue number')
        self.assertEqual(res.url, mock_generate_url.return_value, 'incorrect URL')

        # Most import assertion:
        self.assertEqual(res.get_info(), {'message': 'Issue not found'}, 'get_info has incorrect output')

    @patch('src.zenhub.ZenHub._generate_url')
    @patch('src.zenhub.ZenHub._get_repo_id')
    @patch('src.zenhub.ZenHub._get_token')
    @patch('requests.get', side_effect=mocked_response)
    def test_nonexisting_repo_ID_nonexisting_issue_num(self, mocked_get_info, mock_get_token, mock_repo_id, mock_generate_url):
        path_to_token = '~/foo/bar/baz.txt'
        repo_name = 'azul'
        issue = 55555555

        mock_get_token.return_value = 99999999
        mock_repo_id.return_value = 100000000
        mock_generate_url.return_value = (
            f"https://api.zenhub.io/p1/repositories/{mock_repo_id.return_value}/issues/{issue}")

        res = ZenHub(path_to_token=path_to_token,
                     repo_name=repo_name,
                     issue=issue)

        self.assertEqual(res.token, mock_get_token.return_value, 'incorrect token')
        self.assertEqual(res.repo_id, mock_repo_id.return_value, 'incorrect repo_id')
        self.assertEqual(res.issue, str(issue), 'incorrect issue number')
        self.assertEqual(res.url, mock_generate_url.return_value, 'incorrect URL')

        # Most import assertion:
        self.assertEqual(res.get_info(), {'message': 'Invalid Field for repo_id: repo_id is a required field'},
                         'get_info has incorrect output')

    @patch('src.zenhub.ZenHub._generate_url', return_value='https://foo.bar')
    def test_generate_url(self, mock_generate_url):

        zen = ZenHub(path_to_token='foo/bar.txt',
                     repo_name='baz',
                     issue=42)
        self.assertEqual(zen.url, 'https://foo.bar', 'URL not generated correctly')



if __name__ == '__main__':
    unittest.main()
