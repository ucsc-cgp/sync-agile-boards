#!/usr/env/python3

from unittest import TestCase
import zenhub

class TestSyncAgile(TestCase):

    def setUp(self):
        self.path_to_token = '~/foo/bar/baz.txt'
        self.repo_name = 'azul'
        self.issue = 42



    def test_access_zenhub(self):
        zen = zenhub.ZenHub(path_to_token=self.path_to_token,
                            repo_name=self.repo_name,
                            issue=self.issue)

        print(zen.get_storypoints())

