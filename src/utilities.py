#!/usr/bin/env python3

import requests
import os
import errno
import logging
from settings import urls


logger = logging.getLogger()
logger.setLevel(logging.INFO)
FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format=FORMAT)


def get_repo_id(repo_name, org_name):
    url = _get_repo_url(repo_name, org_name)
    response = requests.get(url)
    r = {'status_code': response.status_code}
    if response.status_code == 200:
        response_json = response.json()
        r['repo_id'] = response_json['id']
    else:
        r['repo_id'] = response.reason
    return r


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
        "https://api.github.com/repos/foo/bar"
    """

    base_url = urls['github_api']
    return  f'{base_url}/{org_name}/{repo_name}'

