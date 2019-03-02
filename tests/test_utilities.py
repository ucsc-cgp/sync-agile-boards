#!/usr/bin/env python3


import unittest
import os
from unittest.mock import patch
from settings import org, urls
from src.utilities import get_repo_id, _get_repo_url, check_for_git_config


def mocked_response(*args):
    """Create class to mock requests response."""

    class MockResponse:
        def __init__(self, json_data, status_code, reason):
            self.json_data = json_data
            self.status_code = status_code
            self.reason = reason

        def json(self):
            return self.json_data

    # Careful, args needs to be a tuple, and that always ends with a "," character in Python!!
    if args == ('https://api.github.com/repos/DataBiosphere/azul',):
        return MockResponse(
            {'id': 42,
             'node_id': 'MDEwOlJlcG9zaXRvcnkxMzkwOTU1Mzc=',
             'name': 'azul',
             'full_name': 'DataBiosphere/azul',
             'private': False,
             'owner': {'login': 'DataBiosphere',
                       'id': 32805087
                       }
             },
            200,
            'OK'
        )
    elif args == ('https://api.github.com/repos/DataBiosphere/foobar',):
        return MockResponse(
            {'message': 'Not Found',
             'documentation_url': 'https://developer.github.com/v3/repos/#get'},
            404,
            'Not Found'
        )


class TestUtilities(unittest.TestCase):

    @patch.dict(urls, {'github_api': 'http://foo.bar'}, clear=True)
    def test_get_repo_url(self):
        url_expected = 'http://foo.bar/someorg/somerepo'
        url_observed = _get_repo_url('somerepo', 'someorg')
        self.assertEqual(url_expected, url_observed, 'GitHub repo URL malformed')

    @patch('requests.get', side_effect=mocked_response)
    def test_get_repo_id(self, mocked_resp):
        mocked_resp = mocked_response('https://api.github.com/repos/DataBiosphere/azul',)
        repo_id = get_repo_id('azul', 'DataBiosphere')
        self.assertEqual(mocked_resp.json_data['id'], repo_id['repo_id'])

    @patch('src.utilities._get_repo_url')
    @patch('requests.get', side_effect=mocked_response)
    def test_get_repo_id_non_existent_repo(self, mocked_resp, mock_get_repo_url):
        mocked_resp = mocked_response('https://api.github.com/repos/DataBiosphere/foobar',)
        mock_get_repo_url.return_value = 'https://api.github.com/repos/DataBiosphere/foobar'
        repo_id = get_repo_id('foobar', 'DataBiosphere')
        self.assertEqual(mocked_resp.reason, repo_id['repo_id'])
        self.assertEqual(mocked_resp.status_code, repo_id['status_code'])

    def test_check_for_git_config(self):
        config_file = '/tmp/foobar'
        if os.path.isfile(config_file):
            os.remove(config_file)
        self.assertRaises(FileNotFoundError, check_for_git_config, config_file)









