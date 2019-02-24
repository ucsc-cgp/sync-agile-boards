#!/usr/bin/env python3

import requests
import os
import errno
import logging
from settings import org, urls
from more_itertools import one
from urllib.parse import urljoin

logger = logging.getLogger()
logger.setLevel(logging.INFO)
FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format=FORMAT)


def get_repo_id(repo_name):
    check_for_git_config('.gitconfig')
    url = _get_repo_url(repo_name)
    response = requests.get(url)
    if response.status_code == 200:
        response_json = response.json()
        return {'repo_id': response_json['id']}
    else:
        return {'repo_id': response.reason}


def check_for_git_config(git_config_file):
    """
    User must have ~/.gitconfig in home directory in order to use this function.
    """
    logging.info('Checking whether .gitconfig exists on local system')
    user_home = os.path.expanduser('~')
    if not os.path.isfile(os.path.join(user_home, git_config_file)):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), git_config_file)


def _get_repo_url(repo_name):
    """
    Return URL using GitHub API for repo_name
    (use look-up-table to return GitHub organization from repo name)
    """
    base_url = urls['github_api']
    _org = [k for k, v in org.items() if repo_name in v]
    if _org == []:
        raise ValueError(f'Cannot find organization for {repo_name}')
    assert len(_org) == 1
    organization = one(_org)
    url = f'{organization}/{repo_name}'

    return urljoin(base=base_url, url=url)
