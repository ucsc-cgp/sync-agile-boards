#!/usr/bin/env python3

import base64
import logging
import os
from pathlib import Path
from settings import url_mgmnt_sys, token_path

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s',
                    filename=f'{ROOT_DIR}.log',
                    filemode='w')


def get_access_params(mgmnt_sys):
    """Get authorization parameters.

    :parameter mgmnt_sys: string to indicate the management systems, either 'zen', 'zenhub', 'jira', or 'atlassian'
    :return: dict containing management system URL and API token to authenticate
    """

    mgmnt_sys = mgmnt_sys.lower()

    if mgmnt_sys in ['jira', 'atlassian']:
        options = {'server': url_mgmnt_sys['jira_url']}
        path_to_token = token_path['api_token_jira']
        logging.info('Accessing Jira')
    elif mgmnt_sys in ['zen', 'zenhub']:
        options = {'server': url_mgmnt_sys['zenhub_url']}
        path_to_token = token_path['api_token_zenhub']
        logging.info('Accessing ZenHub')
    elif mgmnt_sys in ['git', 'github']:
        options = {'server': url_mgmnt_sys['github_url']}
        path_to_token = token_path['api_token_github']
        logging.info('Accessing GitHub')
    else:
        raise ValueError(f'{mgmnt_sys} not a valid input.')

    api_token = base64.b64encode(_get_token(path_to_token).encode())

    return {'options': options, 'api_token': api_token.decode()}  # turn the encoded token back into a string


def _get_token(path_to_token):
    home = str(Path.home())
    path_to_token = path_to_token.replace('~', home)
    try:
        with open(path_to_token, 'r') as fh:
            tok = fh.readline()
            tok = ''.join(tok.split())
            return tok
    except FileNotFoundError as e:
        logging.info(e.strerror)
