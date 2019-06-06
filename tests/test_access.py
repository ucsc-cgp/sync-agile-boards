#!/usr/bin/env python3

import unittest
from unittest.mock import patch
import os
from src.access import get_access_params, _get_token


class TestAccess(unittest.TestCase):

    def setUp(self):

        # Happy token file.
        with open('/tmp/tok0', 'w') as fh:
            fh.write('foo')

        # Token file contains linefeed.
        with open('/tmp/tok1', 'w') as fh:
            fh.write('foo\n')

        # Token file contains whitespace.
        with open('/tmp/tok2', 'w') as fh:
            fh.write('foo ')

        # Token file contains Windows style newline.
        with open('/tmp/tok3', 'w') as fh:
            fh.write('foo\r\n')

    def tearDown(self):
        os.remove('/tmp/tok0')
        os.remove('/tmp/tok1')
        os.remove('/tmp/tok2')
        os.remove('/tmp/tok3')

    @patch('src.access._get_token')
    def test_get_access_params_check_argsin(self, mock_get_token):
        mock_get_token.return_value = 'mock token'

        mgmnt_sys = 'jira'
        access = get_access_params(mgmnt_sys=mgmnt_sys)
        self.assertDictEqual(access['options'], {'server': 'https://%s.atlassian.net/rest/api/latest/',
                                                 'alt_server': 'https://%s.atlassian.net/rest/agile/1.0/'})

        mgmnt_sys = 'zen'
        access = get_access_params(mgmnt_sys=mgmnt_sys)
        self.assertDictEqual(access['options'], {'server': 'https://api.zenhub.io/p1/repositories/'})

        mgmnt_sys = 'zenhub'
        access = get_access_params(mgmnt_sys=mgmnt_sys)
        self.assertDictEqual(access['options'], {'server': 'https://api.zenhub.io/p1/repositories/'})

        mgmnt_sys = 'ZenHub'
        access = get_access_params(mgmnt_sys=mgmnt_sys)
        self.assertDictEqual(access['options'], {'server': 'https://api.zenhub.io/p1/repositories/'})

        mgmnt_sys = 'foo'
        self.assertRaises(ValueError, get_access_params, mgmnt_sys=mgmnt_sys)

        mgmnt_sys = 'xjirax'
        self.assertRaises(ValueError, get_access_params, mgmnt_sys=mgmnt_sys)

        mgmnt_sys = 'xzenx'
        self.assertRaises(ValueError, get_access_params, mgmnt_sys=mgmnt_sys)

    def test_get_token(self):

        path_to_token = '/tmp/tok0'
        tok = _get_token(path_to_token)
        self.assertEqual(tok, 'foo', 'linefeed not removed')

        path_to_token = '/tmp/tok1'
        tok = _get_token(path_to_token)
        self.assertEqual(tok, 'foo', 'linefeed not removed')

        path_to_token = '/tmp/tok2'
        tok = _get_token(path_to_token)
        self.assertEqual(tok, 'foo', 'whitespace not removed')

        path_to_token = '/tmp/tok3'
        tok = _get_token(path_to_token)
        self.assertEqual(tok, 'foo', 'newline characters not removed')


if __name__ == '__main__':
    unittest.main()
