#!/usr/bin/env python3

import requests
import os
import errno
import logging

from src.issue import Issue
from settings import default_orgs, urls

logger = logging.getLogger()
logger.setLevel(logging.INFO)
FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format=FORMAT)


def get_repo_id(repo_name, org_name=default_orgs['github']):
    url = _get_repo_url(repo_name, org_name)
    print(url)
    r = requests.get(url)

    response = {'status_code': r.status_code}
    if r.status_code == 200:
        response_json = r.json()
        response['repo_id'] = response_json['id']
    else:
        response['repo_id'] = r.reason
    return response


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
    backlog_map = {
        'New Issue': 'New Issue',
        'Icebox': 'Icebox',
        'To Do': 'Epic',
        'In Progress': 'Product Backlog',
        'In Review': 'Product Backlog',
        'Merged': 'Product Backlog',
        'Done': 'Done',
        'Closed': 'Closed'
    }
    sprint_map = {
        'New Issue': 'New Issue',
        'To Do': 'Sprint Backlog',
        'In Progress': 'In Progress',
        'In Review': 'Review/QA',
        'Merged': 'Merged',
        'Done': 'Done',
        'Rejected': 'Closed'
    }
    if i.jira_sprint is None:  # issue is in the backlog
        return backlog_map[i.status]
    else:
        return sprint_map[i.status]


def get_jira_status(i: 'Issue'):
    map = {
        'New Issues': 'New Issue',
        'Product Backlog': 'To Do',
        'Icebox': 'Rejected',  # ??
        'Sprint Backlog': 'To Do',
        'In Progress': 'In Progress',
        'Review/QA': 'In Review',
        'Merged': 'Merged',
        'Done': 'Done',
        'Closed': 'Done',
        'Epics': 'To Do'
    }

    return map[i.pipeline]


