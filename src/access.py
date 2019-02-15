#!/usr/bin/env python3

import logging
import os
from pathlib import Path
from settings import url_mgmnt_sys, auth

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

    if 'jira' in mgmnt_sys or 'atlassian' in mgmnt_sys:
        options = {'server': url_mgmnt_sys['jira_url']}
        logging.info('Accessing Jira')
    elif 'zen' in mgmnt_sys or 'zenhub' in mgmnt_sys:
        options = {'server': url_mgmnt_sys['zenhub_url']}
        logging.info('Accessing ZenHub')
    else:
        raise TypeError(f'{mgmnt_sys} not a valid input.')

    if options['server'] == url_mgmnt_sys['jira_url']:
        path_to_token = auth['api_token_jira']
    elif options['server'] == url_mgmnt_sys['zenhub_url']:
        path_to_token = auth['api_token_zenhub']
    else:
        assert False
    api_token = _get_token(path_to_token)
    return {'options': options, 'api_token': api_token}


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
