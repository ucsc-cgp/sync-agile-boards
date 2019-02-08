#!/usr/env/python3

from unittest import TestCase
import zenhub

class TestSyncAgile(TestCase):

    def setUp(self):
        path_to_token = '~/foo/bar/baz.txt'
        repo_name = 'azul'
        issue = 42

        zen = zenhub.ZenHub(path_to_token=path_to_token,
                            repo_name=repo_name,
                            issue=issue)


    def test_access_zenhub(self):
        pass

