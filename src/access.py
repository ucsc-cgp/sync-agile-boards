#!/usr/bin/env python3

import logging
from pathlib import Path
from settings import urls, url_mgmnt_sys, token_path

logger = logging.getLogger(__name__)


def get_access_params(mgmnt_sys: str) -> dict:
    """
    Get authorization parameters.

    :parameter mgmnt_sys: string to indicate the management systems, either 'zen', 'zenhub', 'jira', or 'atlassian'
    :return: dict containing management system URL and API token to authenticate
    """

    mgmnt_sys = mgmnt_sys.lower()

    if mgmnt_sys in ['jira', 'atlassian']:
        options = {'server': url_mgmnt_sys['jira_url'],
                   'alt_server': url_mgmnt_sys['jira_alt_url']}
        path_to_token = token_path['api_token_jira']
        # logging.info('Accessing Jira')
    elif mgmnt_sys in ['zen', 'zenhub']:
        options = {'server': url_mgmnt_sys['zenhub_url']}
        path_to_token = token_path['api_token_zenhub']
        # logging.info('Accessing ZenHub')
    elif mgmnt_sys in ['git', 'github']:
        options = {'server': urls['github_api']}
        path_to_token = token_path['api_token_github']
        # logging.info('Accessing GitHub')
    else:
        raise ValueError(f'{mgmnt_sys} not a valid input.')

    api_token = _get_token(path_to_token)

    return {'options': options, 'api_token': api_token}


def _get_token(path_to_token: str) -> str:
    """
    Read an API token from its location
    :param path_to_token: Path to the file holding the token
    """
    home = str(Path.home())
    path_to_token = path_to_token.replace('~', home)
    try:
        with open(path_to_token, 'r') as fh:
            tok = fh.readline()
            tok = ''.join(tok.split())
            return tok
    except FileNotFoundError as e:
        logging.error(f'Failed to open file, {e.strerror}', exc_info=True)
