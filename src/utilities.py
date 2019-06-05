#!/usr/bin/env python3

import os
import errno
import logging

from src.issue import Issue
from settings import jira_to_zen_backlog_map, jira_to_zen_sprint_map, zen_to_jira_map, urls

logger = logging.getLogger(__name__)


def check_for_git_config(git_config_file):
    """
    User must have ~/.gitconfig in home directory in order to use this function.
    """
    logging.info('Checking whether .gitconfig exists on local system')
    user_home = os.path.expanduser('~')
    if not os.path.isfile(os.path.join(user_home, git_config_file)):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), git_config_file)


def _get_repo_url(repo_name, org_name):
    """
    Return URL using GitHub API.

    Example:
        If repo_name = 'bar' and org_name is 'foo', this returns
        'https://api.github.com/repos/foo/bar'
    """

    base_url = urls['github_api']
    return f'{base_url}{org_name}/{repo_name}'


def get_zenhub_pipeline(i: 'Issue'):
    """Return the corresponding ZenHub pipeline for a Jira issue using the mapping in settings.py"""

    if i.sprint_id is None:  # issue is in the backlog
        return jira_to_zen_backlog_map[i.status]
    else:
        return jira_to_zen_sprint_map[i.status]


def get_jira_status(i: 'Issue'):
    """Return the corresponding Jira status for a ZenHub issue using the mapping in settings.py"""

    return zen_to_jira_map[i.pipeline]


class CustomFieldNames:
    """A class to hold field ids with names that aren't self-explanatory"""

    sprint = 'customfield_10010'
    story_points = 'customfield_10014'
