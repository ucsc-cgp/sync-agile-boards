#!/usr/env/python3

from unittest import TestCase
from unittest.mock import Mock, patch
from src import zenhub


def mocked_requests_get(*args, **kwargs):
    """Create class to mocked response to GET."""

    class MockHappyResponse:
        def __init__(self, json_data, status_code, reason):
            self.json_data = json_data
            self.status_code = status_code
            self.reason = reason

        def json(self):
            return self.json_data

    if args[0] == '"https://api.zenhub.io/p1/repositories/123456789/issues/42"':
        return MockHappyResponse(
            {'estimate': {'value': 55},
             'plus_ones': [],
             'pipeline': {'name': 'Done'},
             'is_epic': False},
            200
            )
    return MockHappyResponse(
        {'message': 'Issue not found'},
        404,
        {'reason': 'Not found'}
    )

def mocked_get_token(path_to_token):
    return '123456789'


class TestZenHub(TestCase):

    def setUp(self):
        self.path_to_token = '~/foo/bar/baz.txt'
        self.repo_name = 'azul'
        self.issue = 42

    @patch('src.zenhub.ZenHub._get_token')  #side_effect=mocked_get_token)
    @patch('src.zenhub.Zenhub.get_storypoints', side_effect=mocked_requests_get)
    def test_happy_path(self, mock_get, mock_get_token):

        mock_get_token.return_value = 123456789
        path_to_token = '~/foo/bar/baz.txt'
        repo_name = 'azul'
        issue = 42

        zen = zenhub.ZenHub(path_to_token=path_to_token,
                            repo_name=repo_name,
                            issue=issue)

        print(zen._generate_url())
        #print(zen.get_storypoints())

    @patch('src.zenhub.ZenHub._get_token')
    def test_get_token(self, mock_get_token):

        mock_get_token.return_value = 123456789
        zen = zenhub.ZenHub(path_to_token='foo/bar.txt',
                            repo_name='baz',
                            issue=42)

        print(zen.repo_id())


