import re
import unittest
from unittest.mock import patch, call
from more_itertools import last


from src.jira import JiraRepo, JiraIssue
from src.sync import Sync
from src.zenhub import ZenHubIssue, ZenHubRepo

# JIRA-5 is a Jira Story corresponding to GitHub issue GHUB-5
JIRA_5 = {
    'total': 2,
    'maxResults': 50,
    'issues': [
        {
            'key': 'JIRA-5',
            'fields': {
                'assignee': {
                    'displayName': 'John Doe',
                    'key': 'awesome_programmer',
                    'name': 'awesome_programmer'},
                'description':
                    '\r\n┆{color:#707070}Issue is synchronized with a [GitHub issue|'
                    'https://github.com/ucsc-cgp/abc/issues/5]{color}\r\n'
                    '┆{color:#707070}Repository Name: abc{color}\r\n'
                    '┆{color:#707070}Issue Number: 5{color}\r\n',
                'customfield_10010': None,
                'created': '2019-02-05T14:52:11.501-0800',
                'customfield_10008': None,
                'customfield_10014': 4.0,
                'issuetype': {'name': 'Story'},
                'sprint': None,
                'status': {'name': 'In Progress'},
                'summary': 'Test 5',
                'updated': '2019-02-20T14:34:08.870-0800'
            }
        }
    ]
}

# JIRA_6 is a Jira Story corresponding to GitHub issue GHUB-6
JIRA_6 = {
    'total': 2,
    'maxResults': 50,
    'issues': [
        {
            'key': 'JIRA-6',
            'fields': {
                'assignee': {
                    'displayName': 'John Doe',
                    'key': 'awesome_programmer',
                    'name': 'awesome_programmer'},
                'description':
                    '\r\n┆{color:#707070}Issue is synchronized with a [GitHub issue|'
                    'https://github.com/ucsc-cgp/abc/issues/5]{color}\r\n'
                    '┆{color:#707070}Repository Name: abc{color}\r\n'
                    '┆{color:#707070}Milestone: testsprint1{color}\n'
                    '┆{color:#707070}Issue Number: 5{color}\r\n',
                'customfield_10010': [
                    'com.atlassian.greenhopper.service.sprint.Sprint@5c63f0b2[id=42,'
                    'rapidViewId=13,state=FUTURE,name=testsprint1,goal=,'
                    'startDate=<null>,endDate=<null>,completeDate=<null>,sequence=42]'
                ],
                'created': '2019-02-05T14:52:11.501-0800',
                'customfield_10008': None,
                'customfield_10014': 4.0,
                'issuetype': {'name': 'Story'},
                'status': {'name': 'In Progress'},
                'summary': 'JIRA 6',
                'updated': '2019-02-20T14:34:08.870-0800'
            }
        }
    ]
}

# JIRA_7 is a Jira Story corresponding to GitHub issue GHUB-7, but isn't part of a sprint
JIRA_7 = {
    'total': 2,
    'maxResults': 50,
    'issues': [
        {
            'key': 'JIRA-7',
            'fields': {
                'assignee': {
                    'displayName': 'John Doe',
                    'key': 'awesome_programmer',
                    'name': 'awesome_programmer'},
                'description':
                    '\r\n┆{color:#707070}Issue is synchronized with a [GitHub issue|'
                    'https://github.com/ucsc-cgp/abc/issues/7]{color}\r\n'
                    '┆{color:#707070}Repository Name: abc{color}\r\n'
                    '┆{color:#707070}Issue Number: 7{color}\r\n',
                'customfield_10010': None,
                'created': '2019-02-05T14:52:11.501-0800',
                'customfield_10008': None,
                'customfield_10014': 4.0,
                'issuetype': {'name': 'Story'},
                'status': {'name': 'In Progress'},
                'summary': 'JIRA 7',
                'updated': '2019-02-20T14:34:08.870-0800'
            }
        }
    ]
}

# JIRA_8 is a Jira Story corresponding to GitHub issue GHUB-8, but no sprint of same name as the GitHub milestone can
# be found in Jira.
JIRA_8 = {
    'total': 2,
    'maxResults': 50,
    'issues': [
        {
            'key': 'JIRA-8',
            'fields': {
                'assignee': {
                    'displayName': 'John Doe',
                    'key': 'awesome_programmer',
                    'name': 'awesome_programmer'},
                'description':
                    '\r\n┆{color:#707070}Issue is synchronized with a [GitHub issue|'
                    'https://github.com/ucsc-cgp/abc/issues/8]{color}\r\n'
                    '┆{color:#707070}Repository Name: abc{color}\r\n'
                    '┆{color:#707070}Issue Number: 8{color}\r\n',
                'customfield_10010': None,
                'created': '2019-02-05T14:52:11.501-0800',
                'customfield_10008': None,
                'customfield_10014': 4.0,
                'issuetype': {'name': 'Story'},
                'status': {'name': 'In Progress'},
                'summary': 'JIRA 8',
                'updated': '2019-02-20T14:34:08.870-0800'
            }
        }
    ]
}

# JIRA_9 is a Jira Story corresponding to GitHub issue GHUB-9, but no sprint of same name as the GitHub
# milestone can be found in Jira.
JIRA_9 = {
    'total': 2,
    'maxResults': 50,
    'issues': [
        {
            'key': 'JIRA-9',
            'fields': {
                'assignee': {
                    'displayName': 'John Doe',
                    'key': 'awesome_programmer',
                    'name': 'awesome_programmer'},
                'description':
                    '\r\n┆{color:#707070}Issue is synchronized with a [GitHub issue|'
                    'https://github.com/ucsc-cgp/abc/issues/9]{color}\r\n'
                    '┆{color:#707070}Repository Name: abc{color}\r\n'
                    '┆{color:#707070}Issue Number: 9{color}\r\n',
                'customfield_10010': [
                    'com.atlassian.greenhopper.service.sprint.Sprint@5c63f0b2[id=42,'
                    'rapidViewId=13,state=FUTURE,name=testsprint1,goal=,'
                    'startDate=<null>,endDate=<null>,completeDate=<null>,sequence=42]'
                ],
                'created': '2019-02-05T14:52:11.501-0800',
                'customfield_10008': None,
                'customfield_10014': 4.0,
                'issuetype': {'name': 'Story'},
                'status': {'name': 'In Progress'},
                'summary': 'JIRA 9',
                'updated': '2019-02-20T14:34:08.870-0800'
            }
        }
    ]
}

JIRA_9_remove_10010 = {  # mocks removal of ticket from sprint, thus customfield 10010 is now 'None'
    'total': 2,
    'maxResults': 50,
    'issues': [
        {
            'key': 'JIRA-9',
            'fields': {
                'assignee': {
                    'displayName': 'John Doe',
                    'key': 'awesome_programmer',
                    'name': 'awesome_programmer'},
                'description':
                    '\r\n┆{color:#707070}Issue is synchronized with a [GitHub issue|'
                    'https://github.com/ucsc-cgp/abc/issues/9]{color}\r\n'
                    '┆{color:#707070}Repository Name: abc{color}\r\n'
                    '┆{color:#707070}Issue Number: 9{color}\r\n',
                'customfield_10010': None,
                'created': '2019-02-05T14:52:11.501-0800',
                'customfield_10008': None,
                'customfield_10014': 4.0,
                'issuetype': {'name': 'Story'},
                'status': {'name': 'In Progress'},
                'summary': 'JIRA 9',
                'updated': '2019-02-20T14:34:08.870-0800'
            }
        }
    ]
}

# JIRA_10 is a Jira Story corresponding to GitHub issue GHUB-10, but its sprint name dosen't match GHUBs
# milestone milestone name.
JIRA_10 = {
    'total': 2,
    'maxResults': 50,
    'issues': [
        {
            'key': 'JIRA-10',
            'fields': {
                'assignee': {
                    'displayName': 'John Doe',
                    'key': 'awesome_programmer',
                    'name': 'awesome_programmer'},
                'description':
                    '\r\n┆{color:#707070}Issue is synchronized with a [GitHub issue|'
                    'https://github.com/ucsc-cgp/abc/issues/10]{color}\r\n'
                    '┆{color:#707070}Repository Name: abc{color}\r\n'
                    '┆{color:#707070}Issue Number: 10{color}\r\n',
                'customfield_10010': [
                    'com.atlassian.greenhopper.service.sprint.Sprint@5c63f0b2[id=42,'
                    'rapidViewId=13,state=FUTURE,name=testsprint1,goal=,'
                    'startDate=<null>,endDate=<null>,completeDate=<null>,sequence=42]'
                ],
                'created': '2019-02-05T14:52:11.501-0800',
                'customfield_10008': None,
                'customfield_10014': 4.0,
                'issuetype': {'name': 'Story'},
                'status': {'name': 'In Progress'},
                'summary': 'JIRA 10',
                'updated': '2019-02-20T14:34:08.870-0800'
            }
        }
    ]
}

# JIRA_11 is a Jira Story corresponding to GitHub issue GHUB-11, but its sprint name dosen't match GHUBs
# milestone milestone name, but JIRA has a sprint with the same name as the milestone name that ticket
# is associated with in GitHub.
JIRA_11 = {
    'total': 2,
    'maxResults': 50,
    'issues': [
        {
            'key': 'JIRA-11',
            'fields': {
                'assignee': {
                    'displayName': 'John Doe',
                    'key': 'awesome_programmer',
                    'name': 'awesome_programmer'},
                'description':
                    '\r\n┆{color:#707070}Issue is synchronized with a [GitHub issue|'
                    'https://github.com/ucsc-cgp/abc/issues/11]{color}\r\n'
                    '┆{color:#707070}Repository Name: abc{color}\r\n'
                    '┆{color:#707070}Issue Number: 11{color}\r\n',
                'customfield_10010': [
                    'com.atlassian.greenhopper.service.sprint.Sprint@5c63f0b2[id=99,'
                    'rapidViewId=13,state=FUTURE,name=testsprint3,goal=,'
                    'startDate=<null>,endDate=<null>,completeDate=<null>,sequence=99]'
                ],
                'created': '2019-02-05T14:52:11.501-0800',
                'customfield_10008': None,
                'customfield_10014': 4.0,
                'issuetype': {'name': 'Story'},
                'status': {'name': 'In Progress'},
                'summary': 'JIRA 11',
                'updated': '2019-02-20T14:34:08.870-0800'
            }
        }
    ]
}

JIRA_11_remove_10010 = {  # mocks removal of ticket from sprint, thus customfield 10010 is now 'None'
    'total': 2,
    'maxResults': 50,
    'issues': [
        {
            'key': 'JIRA-11',
            'fields': {
                'assignee': {
                    'displayName': 'John Doe',
                    'key': 'awesome_programmer',
                    'name': 'awesome_programmer'},
                'description':
                    '\r\n┆{color:#707070}Issue is synchronized with a [GitHub issue|'
                    'https://github.com/ucsc-cgp/abc/issues/11]{color}\r\n'
                    '┆{color:#707070}Repository Name: abc{color}\r\n'
                    '┆{color:#707070}Issue Number: 11{color}\r\n',
                'customfield_10010': None,
                'created': '2019-02-05T14:52:11.501-0800',
                'customfield_10008': None,
                'customfield_10014': 4.0,
                'issuetype': {'name': 'Story'},
                'status': {'name': 'In Progress'},
                'summary': 'JIRA 11',
                'updated': '2019-02-20T14:34:08.870-0800'
            }
        }
    ]
}

JIRA_ISSUES = {
    'total': 4,
    'maxResults': 50,
    'issues': [
        {  # JIRA-5 is a Jira Story corresponding to GitHub issue GHUB-5
            'key': 'JIRA-5',
            'fields': {
                'assignee': {
                    'displayName': 'John Doe',
                    'key': 'awesome_programmer',
                    'name': 'awesome_programmer'},
                'description':
                    '\r\n┆{color:#707070}Issue is synchronized with a [GitHub issue|'
                    'https://github.com/ucsc-cgp/abc/issues/5]{color}\r\n'
                    '┆{color:#707070}Repository Name: abc{color}\r\n'
                    '┆{color:#707070}Issue Number: 5{color}\r\n',
                'customfield_10010': None,
                'created': '2019-02-05T14:52:11.501-0800',
                'customfield_10008': None,
                'customfield_10014': 4.0,
                'issuetype': {'name': 'Story'},
                'sprint': None,
                'status': {'name': 'In Progress'},
                'summary': 'Test 5',
                'updated': '2019-02-20T14:34:08.870-0800'
            }
        },
        {  # JIRA_6 is a Jira Story corresponding to GitHub issue GHUB-6
            'key': 'JIRA-6',
            'fields': {
                'assignee': {
                    'displayName': 'John Doe',
                    'key': 'awesome_programmer',
                    'name': 'awesome_programmer'},
                'description':
                    '\r\n┆{color:#707070}Issue is synchronized with a [GitHub issue|'
                    'https://github.com/ucsc-cgp/abc/issues/5]{color}\r\n'
                    '┆{color:#707070}Repository Name: abc{color}\r\n'
                    '┆{color:#707070}Milestone: testsprint1{color}\n'
                    '┆{color:#707070}Issue Number: 5{color}\r\n',
                'customfield_10010': [
                    'com.atlassian.greenhopper.service.sprint.Sprint@5c63f0b2[id=42,'
                    'rapidViewId=13,state=FUTURE,name=testsprint1,goal=,'
                    'startDate=<null>,endDate=<null>,completeDate=<null>,sequence=42]'
                ],
                'created': '2019-02-05T14:52:11.501-0800',
                'customfield_10008': None,
                'customfield_10014': 4.0,
                'issuetype': {'name': 'Story'},
                'status': {'name': 'In Progress'},
                'summary': 'JIRA 6',
                'updated': '2019-02-20T14:34:08.870-0800'
            }
        },
        {  # JIRA_7 is a Jira Story corresponding to GitHub issue GHUB-7, but isn't part of a sprint
            'key': 'JIRA-7',
            'fields': {
                'assignee': {
                    'displayName': 'John Doe',
                    'key': 'awesome_programmer',
                    'name': 'awesome_programmer'},
                'description':
                    '\r\n┆{color:#707070}Issue is synchronized with a [GitHub issue|'
                    'https://github.com/ucsc-cgp/abc/issues/7]{color}\r\n'
                    '┆{color:#707070}Repository Name: abc{color}\r\n'
                    '┆{color:#707070}Issue Number: 7{color}\r\n',
                'customfield_10010': None,
                'created': '2019-02-05T14:52:11.501-0800',
                'customfield_10008': None,
                'customfield_10014': 4.0,
                'issuetype': {'name': 'Story'},
                'status': {'name': 'In Progress'},
                'summary': 'JIRA 7',
                'updated': '2019-02-20T14:34:08.870-0800'
            }
        },
        {  # JIRA_8 is a Jira Story corresponding to GitHub issue GHUB-8, but no sprint of same name as the GitHub
            # milestone can be found in Jira.
            'key': 'JIRA-8',
            'fields': {
                'assignee': {
                    'displayName': 'John Doe',
                    'key': 'awesome_programmer',
                    'name': 'awesome_programmer'},
                'description':
                    '\r\n┆{color:#707070}Issue is synchronized with a [GitHub issue|'
                    'https://github.com/ucsc-cgp/abc/issues/8]{color}\r\n'
                    '┆{color:#707070}Repository Name: abc{color}\r\n'
                    '┆{color:#707070}Issue Number: 8{color}\r\n',
                'customfield_10010': None,
                'created': '2019-02-05T14:52:11.501-0800',
                'customfield_10008': None,
                'customfield_10014': 4.0,
                'issuetype': {'name': 'Story'},
                'status': {'name': 'In Progress'},
                'summary': 'JIRA 8',
                'updated': '2019-02-20T14:34:08.870-0800'
            }
        },
        {  # JIRA_9 is a Jira Story corresponding to GitHub issue GHUB-9, but no sprint of same name as the GitHub
            # milestone can be found in Jira.
            'key': 'JIRA-9',
            'fields': {
                'assignee': {
                    'displayName': 'John Doe',
                    'key': 'awesome_programmer',
                    'name': 'awesome_programmer'},
                'description':
                    '\r\n┆{color:#707070}Issue is synchronized with a [GitHub issue|'
                    'https://github.com/ucsc-cgp/abc/issues/9]{color}\r\n'
                    '┆{color:#707070}Repository Name: abc{color}\r\n'
                    '┆{color:#707070}Issue Number: 9{color}\r\n',
                'customfield_10010': [
                    'com.atlassian.greenhopper.service.sprint.Sprint@5c63f0b2[id=42,'
                    'rapidViewId=13,state=FUTURE,name=testsprint1,goal=,'
                    'startDate=<null>,endDate=<null>,completeDate=<null>,sequence=42]'
                ],
                'created': '2019-02-05T14:52:11.501-0800',
                'customfield_10008': None,
                'customfield_10014': 4.0,
                'issuetype': {'name': 'Story'},
                'status': {'name': 'In Progress'},
                'summary': 'JIRA 9',
                'updated': '2019-02-20T14:34:08.870-0800'
            }
        }
    ]
}

# GHUB-5 is a GitHub issue corresponding to Jira story JIRA-5
GHUB_5 = {'number': 5,
          'title': 'mock-ticket',
          'assignee': {'login': 'john doe'},
          'assignees': [{'login': 'john doe'}],
          'milestone': None,
          'created_at': '2019-04-11T21:50:07Z',
          'updated_at': '2019-04-16T20:54:38Z',
          'closed_at': None,
          'body': 'some comment\n\n┆Issue is synchronized with this [Jira Story](https://mock-jira.atlassian.net/browse/JIRA-5)\n┆Project Name: Test-Project\n┆Issue Number: JIRA-5\n',
          'closed_by': None}

# GHUB-6 is a GitHub issue corresponding to Jira story JIRA-5
GHUB_6 = {'number': 6,
          'title': 'GHUB-6',
          'assignee': {'login': 'john doe'},
          'assignees': [{'login': 'john doe'}],
          'milestone': {'url': 'https://api.github.com/repos/ucsc-cgp/abc/milestones/1',
                        'html_url': 'https://github.com/ucsc-cgp/abc/milestone/1',
                        'labels_url': 'https://api.github.com/repos/ucsc-cgp/abc/milestones/1/labels',
                        'id': 4222754,
                        'node_id': 'MDk6TWlsZXN0b25lNDIyMjc1NA==',
                        'number': 1,
                        'title': 'testsprint1',
                        'description': 'some description',
                        'creator': {'login': 'awesome hacker',
                                    'id': 15079157,
                                    'node_id': 'MDQ6VXNlcjE1MDc5MTU3',
                                    'avatar_url': 'https://avatars0.githubusercontent.com/u/15079157?v=4',
                                    'gravatar_id': '',
                                    'url': 'https://api.github.com/users/awsome_hacker',
                                    'html_url': 'https://github.com/awsome_hacker',
                                    'followers_url': 'https://api.github.com/users/awsome_hacker/followers',
                                    'following_url': 'https://api.github.com/users/awsome_hacker/following{/other_user}',
                                    'gists_url': 'https://api.github.com/users/awsome_hacker/gists{/gist_id}',
                                    'starred_url': 'https://api.github.com/users/awsome_hacker/starred{/owner}{/repo}',
                                    'subscriptions_url': 'https://api.github.com/users/awsome_hacker/subscriptions',
                                    'organizations_url': 'https://api.github.com/users/awsome_hacker/orgs',
                                    'repos_url': 'https://api.github.com/users/awsome_hacker/repos',
                                    'events_url': 'https://api.github.com/users/awsome_hacker/events{/privacy}',
                                    'received_events_url': 'https://api.github.com/users/awsome_hacker/received_events',
                                    'type': 'User',
                                    'site_admin': False},
                        'open_issues': 1,
                        'closed_issues': 0,
                        'state': 'open',
                        'created_at': '2019-04-11T21:52:08Z',
                        'updated_at': '2019-04-11T21:52:23Z',
                        'due_on': '2019-04-19T07:00:00Z',
                        'closed_at': None},
          'created_at': '2019-04-11T21:50:07Z',
          'updated_at': '2019-04-16T20:54:38Z',
          'closed_at': None,
          'body': 'some comment\n\n┆Issue is synchronized with this [Jira Story](https://mock-jira.atlassian.net/browse/JIRA-6)\n┆Project Name: Test-Project\n┆Issue Number: JIRA-6\n',
          'closed_by': None}

# GHUB-7 is a GitHub issue corresponding to Jira story JIRA-7
GHUB_7 = {'number': 7,
          'title': 'GHUB-7',
          'assignee': {'login': 'john doe'},
          'assignees': [{'login': 'john doe'}],
          'milestone': {'url': 'https://api.github.com/repos/ucsc-cgp/abc/milestones/1',
                        'html_url': 'https://github.com/ucsc-cgp/abc/milestone/1',
                        'labels_url': 'https://api.github.com/repos/ucsc-cgp/abc/milestones/1/labels',
                        'id': 4222754,
                        'node_id': 'MDk6TWlsZXN0b25lNDIyMjc1NA==',
                        'number': 1,
                        'title': 'testsprint1',
                        'description': 'some description',
                        'creator': {'login': 'awesome hacker',
                                    'id': 15079157,
                                    'node_id': 'MDQ6VXNlcjE1MDc5MTU3',
                                    'avatar_url': 'https://avatars0.githubusercontent.com/u/15079157?v=4',
                                    'gravatar_id': '',
                                    'url': 'https://api.github.com/users/awsome_hacker',
                                    'html_url': 'https://github.com/awsome_hacker',
                                    'followers_url': 'https://api.github.com/users/awsome_hacker/followers',
                                    'following_url': 'https://api.github.com/users/awsome_hacker/following{/other_user}',
                                    'gists_url': 'https://api.github.com/users/awsome_hacker/gists{/gist_id}',
                                    'starred_url': 'https://api.github.com/users/awsome_hacker/starred{/owner}{/repo}',
                                    'subscriptions_url': 'https://api.github.com/users/awsome_hacker/subscriptions',
                                    'organizations_url': 'https://api.github.com/users/awsome_hacker/orgs',
                                    'repos_url': 'https://api.github.com/users/awsome_hacker/repos',
                                    'events_url': 'https://api.github.com/users/awsome_hacker/events{/privacy}',
                                    'received_events_url': 'https://api.github.com/users/awsome_hacker/received_events',
                                    'type': 'User',
                                    'site_admin': False},
                        'open_issues': 1,
                        'closed_issues': 0,
                        'state': 'open',
                        'created_at': '2019-04-11T21:52:08Z',
                        'updated_at': '2019-04-11T21:52:23Z',
                        'due_on': '2019-04-19T07:00:00Z',
                        'closed_at': None},
          'created_at': '2019-04-11T21:50:07Z',
          'updated_at': '2019-04-16T20:54:38Z',
          'closed_at': None,
          'body': 'some comment\n\n┆Issue is synchronized with this [Jira Story](https://mock-jira.atlassian.net/browse/JIRA-7)\n┆Project Name: Test-Project\n┆Issue Number: JIRA-7\n',
          'closed_by': None}

# GHUB-8 is a GitHub issue corresponding to Jira story JIRA-8
GHUB_8 = {'number': 8,
          'title': 'GHUB-8',
          'assignee': {'login': 'john doe'},
          'assignees': [{'login': 'john doe'}],
          'milestone': {'url': 'https://api.github.com/repos/ucsc-cgp/abc/milestones/2',
                        'html_url': 'https://github.com/ucsc-cgp/abc/milestone/2',
                        'labels_url': 'https://api.github.com/repos/ucsc-cgp/abc/milestones/2/labels',
                        'id': 4222754,
                        'node_id': 'MDk6TWlsZXN0b25lNDIyMjc1NA==',
                        'number': 2,
                        'title': 'testsprint2',
                        'description': 'some description',
                        'creator': {'login': 'awesome hacker',
                                    'id': 15079157,
                                    'node_id': 'MDQ6VXNlcjE1MDc5MTU3',
                                    'avatar_url': 'https://avatars0.githubusercontent.com/u/15079157?v=4',
                                    'gravatar_id': '',
                                    'url': 'https://api.github.com/users/awsome_hacker',
                                    'html_url': 'https://github.com/awsome_hacker',
                                    'followers_url': 'https://api.github.com/users/awsome_hacker/followers',
                                    'following_url': 'https://api.github.com/users/awsome_hacker/following{/other_user}',
                                    'gists_url': 'https://api.github.com/users/awsome_hacker/gists{/gist_id}',
                                    'starred_url': 'https://api.github.com/users/awsome_hacker/starred{/owner}{/repo}',
                                    'subscriptions_url': 'https://api.github.com/users/awsome_hacker/subscriptions',
                                    'organizations_url': 'https://api.github.com/users/awsome_hacker/orgs',
                                    'repos_url': 'https://api.github.com/users/awsome_hacker/repos',
                                    'events_url': 'https://api.github.com/users/awsome_hacker/events{/privacy}',
                                    'received_events_url': 'https://api.github.com/users/awsome_hacker/received_events',
                                    'type': 'User',
                                    'site_admin': False},
                        'open_issues': 1,
                        'closed_issues': 0,
                        'state': 'open',
                        'created_at': '2019-04-11T21:52:08Z',
                        'updated_at': '2019-04-11T21:52:23Z',
                        'due_on': '2019-04-19T07:00:00Z',
                        'closed_at': None},
          'created_at': '2019-04-11T21:50:07Z',
          'updated_at': '2019-04-16T20:54:38Z',
          'closed_at': None,
          'body': 'some comment\n\n┆Issue is synchronized with this [Jira Story](https://mock-jira.atlassian.net/browse/JIRA-8)\n┆Project Name: Test-Project\n┆Issue Number: JIRA-8\n',
          'closed_by': None}

# GHUB-9 is a GitHub issue corresponding to Jira story JIRA-9
GHUB_9 = {'number': 9,
          'title': 'mock-ticket',
          'assignee': {'login': 'john doe'},
          'assignees': [{'login': 'john doe'}],
          'milestone': None,
          'created_at': '2019-04-11T21:50:07Z',
          'updated_at': '2019-04-16T20:54:38Z',
          'closed_at': None,
          'body': 'some comment\n\n┆Issue is synchronized with this [Jira Story](https://mock-jira.atlassian.net/browse/JIRA-9)\n┆Project Name: Test-Project\n┆Issue Number: JIRA-9\n',
          'closed_by': None}

# GHUB-10 is a GitHub issue corresponding to Jira story JIRA-10
GHUB_10 = {'number': 10,
          'title': 'GHUB-10',
          'assignee': {'login': 'john doe'},
          'assignees': [{'login': 'john doe'}],
          'milestone': {'url': 'https://api.github.com/repos/ucsc-cgp/abc/milestones/2',
                        'html_url': 'https://github.com/ucsc-cgp/abc/milestone/2',
                        'labels_url': 'https://api.github.com/repos/ucsc-cgp/abc/milestones/2/labels',
                        'id': 4222754,
                        'node_id': 'MDk6TWlsZXN0b25lNDIyMjc1NA==',
                        'number': 2,
                        'title': 'testsprint2',
                        'description': 'some description',
                        'creator': {'login': 'awesome hacker',
                                    'id': 15079157,
                                    'node_id': 'MDQ6VXNlcjE1MDc5MTU3',
                                    'avatar_url': 'https://avatars0.githubusercontent.com/u/15079157?v=4',
                                    'gravatar_id': '',
                                    'url': 'https://api.github.com/users/awsome_hacker',
                                    'html_url': 'https://github.com/awsome_hacker',
                                    'followers_url': 'https://api.github.com/users/awsome_hacker/followers',
                                    'following_url': 'https://api.github.com/users/awsome_hacker/following{/other_user}',
                                    'gists_url': 'https://api.github.com/users/awsome_hacker/gists{/gist_id}',
                                    'starred_url': 'https://api.github.com/users/awsome_hacker/starred{/owner}{/repo}',
                                    'subscriptions_url': 'https://api.github.com/users/awsome_hacker/subscriptions',
                                    'organizations_url': 'https://api.github.com/users/awsome_hacker/orgs',
                                    'repos_url': 'https://api.github.com/users/awsome_hacker/repos',
                                    'events_url': 'https://api.github.com/users/awsome_hacker/events{/privacy}',
                                    'received_events_url': 'https://api.github.com/users/awsome_hacker/received_events',
                                    'type': 'User',
                                    'site_admin': False},
                        'open_issues': 1,
                        'closed_issues': 0,
                        'state': 'open',
                        'created_at': '2019-04-11T21:52:08Z',
                        'updated_at': '2019-04-11T21:52:23Z',
                        'due_on': '2019-04-19T07:00:00Z',
                        'closed_at': None},
          'created_at': '2019-04-11T21:50:07Z',
          'updated_at': '2019-04-16T20:54:38Z',
          'closed_at': None,
          'body': 'some comment\n\n┆Issue is synchronized with this [Jira Story](https://mock-jira.atlassian.net/browse/JIRA-10)\n┆Project Name: Test-Project\n┆Issue Number: JIRA-10\n',
          'closed_by': None}

# GHUB-11 is a GitHub issue corresponding to Jira story JIRA-11
GHUB_11 = {'number': 11,
          'title': 'GHUB-11',
          'assignee': {'login': 'john doe'},
          'assignees': [{'login': 'john doe'}],
          'milestone': {'url': 'https://api.github.com/repos/ucsc-cgp/abc/milestones/1',
                        'html_url': 'https://github.com/ucsc-cgp/abc/milestone/1',
                        'labels_url': 'https://api.github.com/repos/ucsc-cgp/abc/milestones/1/labels',
                        'id': 4222754,
                        'node_id': 'MDk6TWlsZXN0b25lNDIyMjc1NA==',
                        'number': 1,
                        'title': 'testsprint1',
                        'description': 'some description',
                        'creator': {'login': 'awesome hacker',
                                    'id': 15079157,
                                    'node_id': 'MDQ6VXNlcjE1MDc5MTU3',
                                    'avatar_url': 'https://avatars0.githubusercontent.com/u/15079157?v=4',
                                    'gravatar_id': '',
                                    'url': 'https://api.github.com/users/awsome_hacker',
                                    'html_url': 'https://github.com/awsome_hacker',
                                    'followers_url': 'https://api.github.com/users/awsome_hacker/followers',
                                    'following_url': 'https://api.github.com/users/awsome_hacker/following{/other_user}',
                                    'gists_url': 'https://api.github.com/users/awsome_hacker/gists{/gist_id}',
                                    'starred_url': 'https://api.github.com/users/awsome_hacker/starred{/owner}{/repo}',
                                    'subscriptions_url': 'https://api.github.com/users/awsome_hacker/subscriptions',
                                    'organizations_url': 'https://api.github.com/users/awsome_hacker/orgs',
                                    'repos_url': 'https://api.github.com/users/awsome_hacker/repos',
                                    'events_url': 'https://api.github.com/users/awsome_hacker/events{/privacy}',
                                    'received_events_url': 'https://api.github.com/users/awsome_hacker/received_events',
                                    'type': 'User',
                                    'site_admin': False},
                        'open_issues': 1,
                        'closed_issues': 0,
                        'state': 'open',
                        'created_at': '2019-04-11T21:52:08Z',
                        'updated_at': '2019-04-11T21:52:23Z',
                        'due_on': '2019-04-19T07:00:00Z',
                        'closed_at': None},
          'created_at': '2019-04-11T21:50:07Z',
          'updated_at': '2019-04-16T20:54:38Z',
          'closed_at': None,
          'body': 'some comment\n\n┆Issue is synchronized with this [Jira Story](https://mock-jira.atlassian.net/browse/JIRA-11)\n┆Project Name: Test-Project\n┆Issue Number: JIRA-11\n',
          'closed_by': None}

# Response following re-association of a GitHub/ZenHub ticket with a different sprint.
GHUB_11_patched = {'milestone': {'title': 'testsprint3', 'number': 3}}

@patch('requests.Response')
def mock_response(url, *args, **kwargs):
    """This test uses four mock issues to simulate a repo to sync. For test_sync_epics, the methods that make API calls
     are mocked out in order to test this method in isolation. For testing syncing an entire repo, all API responses
    are mocked accurately to the format of an actual API response to thoroughly test everything."""

    class MockResponse:
        def __init__(self, json_data, status_code=200):
            self.json_data = json_data
            self.status_code = status_code
            self.text = 'placeholder response text'

        def json(self):
            return self.json_data

    # Mock ZenHub issue information
    if url == 'https://api.zenhub.io/p1/repositories/123/issues/1':
        return MockResponse({'plus_ones': [], 'pipeline': {'name': 'New Issues'},  # no estimate set
                             'is_epic': False})
    elif url == 'https://api.zenhub.io/p1/repositories/123/issues/2':
        return MockResponse({'estimate': {'value': 5}, 'plus_ones': [], 'pipeline': {'name': 'In Progress'},
                             'is_epic': True})
    elif url == 'https://api.zenhub.io/p1/repositories/123/issues/3':
        return MockResponse({'estimate': {'value': 2}, 'plus_ones': [], 'pipeline': {'name': 'Review/QA'},
                             'is_epic': False})
    elif url == 'https://api.zenhub.io/p1/repositories/123/issues/4':
        return MockResponse({'estimate': {'value': 2}, 'plus_ones': [], 'pipeline': {'name': 'In Progress'},
                             'is_epic': False})
    elif url == 'https://api.zenhub.io/p1/repositories/123/issues/5':
        return MockResponse({'estimate': {'value': 2}, 'plus_ones': [], 'pipeline': {'name': 'In Progress'},
                             'is_epic': False})
    elif url == 'https://api.zenhub.io/p1/repositories/123/issues/6':
        return MockResponse({'estimate': {'value': 2}, 'plus_ones': [], 'pipeline': {'name': 'In Progress'},
                             'is_epic': False})
    elif url == 'https://api.zenhub.io/p1/repositories/123/issues/7':
        return MockResponse({'estimate': {'value': 2}, 'plus_ones': [], 'pipeline': {'name': 'In Progress'},
                             'is_epic': False})
    elif url == 'https://api.zenhub.io/p1/repositories/123/issues/8':
        return MockResponse({'estimate': {'value': 2}, 'plus_ones': [], 'pipeline': {'name': 'In Progress'},
                             'is_epic': False})
    elif url == 'https://api.zenhub.io/p1/repositories/123/issues/9':
        return MockResponse({'estimate': {'value': 2}, 'plus_ones': [], 'pipeline': {'name': 'In Progress'},
                             'is_epic': False})
    elif url == 'https://api.zenhub.io/p1/repositories/123/issues/10':
        return MockResponse({'estimate': {'value': 2}, 'plus_ones': [], 'pipeline': {'name': 'In Progress'},
                             'is_epic': False})
    elif url == 'https://api.zenhub.io/p1/repositories/123/issues/11':
        return MockResponse({'estimate': {'value': 2}, 'plus_ones': [], 'pipeline': {'name': 'In Progress'},
                             'is_epic': False})

    # Mock response for request to get ZenHub epic children
    elif url == 'https://api.zenhub.io/p1/repositories/123/epics/2':
        return MockResponse({'issues': [{'issue_number': 1}, {'issue_number': 3}]})

    elif url == 'https://api.zenhub.io/p1/repositories/123/epics/3':
        return MockResponse({'issues': []})

    # Issue events in ZenHub
    elif url == 'https://api.zenhub.io/p1/repositories/123/issues/1/events':
        return MockResponse(
            [{'created_at': '2019-05-08T22:13:43.512Z',
              'from_estimate': {'value': 8},
              'to_estimate': {'value': 4},
              'type': 'estimateIssue'},
             {'created_at': '2019-04-20T14:12:40.900Z',
              'from_estimate': {'value': 4},
              'to_estimate': {'value': 8},
              'type': 'estimateIssue'}])
    elif 'events' in url:
        return MockResponse([])

    # Mock response for getting pipeline ids
    elif url == 'https://api.zenhub.io/p1/repositories/123/board':
        return MockResponse({'pipelines': [{'id': '100', 'name': 'New Issues'},
                                           {'id': '200', 'name': 'In Progress'},
                                           {'id': '300', 'name': 'Backlog'},
                                           {'id': '400', 'name': 'Icebox'},
                                           {'id': '500', 'name': 'Epics'},
                                           {'id': '600', 'name': 'Review/QA'},
                                           {'id': '700', 'name': 'Done'}]})

    # Mock Jira issue information
    elif url == 'https://ucsc-cgl.atlassian.net/rest/api/latest/search?jql=project=TEST&startAt=0':
        return MockResponse({'issues': [
            {'fields': {
                'assignee': None,
                'created': '2019-02-05T14:52:11.501-0800',
                'customfield_10008': None,
                'customfield_10014': None,  # story points
                # 'description': 'synchronized with github: Repository Name: abc Issue Number: 1',
                'description': '┆{color:#707070}Issue is synchronized with a [GitHub '
                               'issue|https://github.com/ucsc-cgp/abc/issues/1]{color}\n'
                               '┆{color:#707070}Repository Name: abc{color}\n'
                               '┆{color:#707070}Milestone: testsprint1{color}\n'
                               '┆{color:#707070}Issue Number: 1{color}',
                'issuetype': {'name': 'Story'},
                'sprint': None,
                'status': {'name': 'In Progress'},
                'summary': 'a test',
                'updated': '2019-05-11T14:34:08.870-0800'},
             'key': 'TEST-1'},
            {'fields': {
                'assignee': None,
                'created': '2019-02-05T14:52:11.501-0800',
                'customfield_10008': None,
                'customfield_10014': 2.0,
                'description': '┆{color:#707070}Issue is synchronized with a [GitHub '
                               'issue|https://github.com/ucsc-cgp/abc/issues/2]{color}\n'
                               '┆{color:#707070}Repository Name: abc{color}\n'
                               '┆{color:#707070}Milestone: testsprint1{color}\n'
                               '┆{color:#707070}Issue Number: 2{color}',
                'issuetype': {'name': 'Story'},
                'sprint': None,
                'status': {'name': 'In Review'},
                'summary': 'Test 2',
                'updated': '2019-04-21T15:55:08.870-0800'},
             'key': 'TEST-2'},
            {'fields': {
                'assignee': None,
                'created': '2019-02-05T14:52:11.501-0800',
                'customfield_10008': None,
                'customfield_10014': 3.0,
                'description': '┆{color:#707070}Issue is synchronized with a [GitHub '
                               'issue|https://github.com/ucsc-cgp/abc/issues/3]{color}\n'
                               '┆{color:#707070}Repository Name: abc{color}\n'
                               '┆{color:#707070}Milestone: testsprint1{color}\n'
                               '┆{color:#707070}Issue Number: 3{color}',
                'issuetype': {'name': 'Epic'},
                'sprint': None,
                'status': {'name': 'Done'},
                'summary': 'Test 3',
                'updated': '2019-02-20T14:34:08.870-0800'},
             'key': 'TEST-3'},
            {'fields': {
                'assignee': None,
                'created': '2019-02-05T14:52:11.501-0800',
                'customfield_10008': None,
                'customfield_10014': 4.0,
                'description': '┆{color:#707070}Issue is synchronized with a [GitHub '
                               'issue|https://github.com/ucsc-cgp/abc/issues/4]{color}\n'
                               '┆{color:#707070}Repository Name: abc{color}\n'
                               '┆{color:#707070}Issue Number: 4{color}',
                'issuetype': {'name': 'Story'},
                'sprint': None,
                'status': {'name': 'In Progress'},
                'summary': 'Test 4',
                'updated': '2019-02-20T14:34:08.870-0800'},
             'key': 'TEST-4'}],
        'total': 4,
        'maxResults': 50})

    elif url == 'https://ucsc-cgl.atlassian.net/rest/api/latest/search?jql=project=JIRA&startAt=0':
        return MockResponse(JIRA_ISSUES)

    elif url == 'https://ucsc-cgl.atlassian.net/rest/api/latest/search?jql=id=JIRA-5':
        return MockResponse(JIRA_5)

    elif url == 'https://ucsc-cgl.atlassian.net/rest/api/latest/search?jql=id=JIRA-6':
        return MockResponse(JIRA_6)

    elif url == 'https://ucsc-cgl.atlassian.net/rest/api/latest/search?jql=id=JIRA-7':
        return MockResponse(JIRA_7)

    elif url == 'https://ucsc-cgl.atlassian.net/rest/api/latest/search?jql=id=JIRA-8':
        return MockResponse(JIRA_8)

    elif url == 'https://ucsc-cgl.atlassian.net/rest/api/latest/search?jql=id=JIRA-9':
        return MockResponse(JIRA_9)

    elif url == 'https://ucsc-cgl.atlassian.net/rest/api/latest/issue/JIRA-9':
        return MockResponse(JIRA_9_remove_10010, status_code=204)

    elif url == 'https://ucsc-cgl.atlassian.net/rest/api/latest/issue/JIRA-11':
        return MockResponse(JIRA_11_remove_10010, status_code=204)

    elif url == 'https://ucsc-cgl.atlassian.net/rest/api/latest/search?jql=id=JIRA-10':
        return MockResponse(JIRA_10)

    elif url == 'https://ucsc-cgl.atlassian.net/rest/api/latest/search?jql=id=JIRA-11':
        return MockResponse(JIRA_11)

    elif url == 'https://ucsc-cgl.atlassian.net/rest/api/latest/search?jql=sprint="testsprint1"':
        return MockResponse({'issues': [{'fields': {'customfield_10010':
                                                        ['com.atlassian.greenhopper.service.sprint.Sprint@377a0916'
                                                         '[id=42,rapidViewId=82,state=ACTIVE,name=testsprint1,goal=,'
                                                         'startDate=2019-04-25T21:51:28.028Z,endDate=2019-05-31T21:51:00.000Z,'
                                                         'completeDate=<null>,sequence=42]']}}]}, status_code=200)

    elif url == 'https://ucsc-cgl.atlassian.net/rest/api/latest/search?jql=sprint="testsprint2"':
        return MockResponse(
            {'errorMessages':
                 ["Sprint with name 'testsprint2' does not exist or you do not have permission to view it."],
             'warningMessages': []},
            status_code=400)

    elif url == 'https://ucsc-cgl.atlassian.net/rest/api/latest/search?jql=sprint="testsprint3"':
        return MockResponse({'issues': [{'fields': {'customfield_10010':
                                                        ['com.atlassian.greenhopper.service.sprint.Sprint@377a0916'
                                                         '[id=99,rapidViewId=82,state=ACTIVE,name=testsprint3,goal=,'
                                                         'startDate=2019-04-25T21:51:28.028Z,endDate=2019-05-31T21:51:00.000Z,'
                                                         'completeDate=<null>,sequence=99]']}}]}, status_code=200)

    # Get Jira epic children
    elif "https://ucsc-cgl.atlassian.net/rest/api/latest/search?jql=cf[10008]='TEST-2'" in url:
        return MockResponse({'issues': []})

    elif "https://ucsc-cgl.atlassian.net/rest/api/latest/search?jql=cf[10008]='TEST-3'" in url:
        return MockResponse({'issues': [{'key': 'TEST-2'}, {'key': 'TEST-4'}]})  # TEST-2 and TEST-4 belong to TEST-3

    # Mock GitHub issue information
    elif url == 'https://api.github.com/repos/ucsc-cgp/abc/issues/5':
        return MockResponse(GHUB_5)

    # Mock GitHub issue information
    elif url == 'https://api.github.com/repos/ucsc-cgp/abc/issues/6':
        return MockResponse(GHUB_6)

    # Mock GitHub issue information
    elif url == 'https://api.github.com/repos/ucsc-cgp/abc/issues/7':
        return MockResponse(GHUB_7)

    # Mock GitHub issue information
    elif url == 'https://api.github.com/repos/ucsc-cgp/abc/issues/8':
        return MockResponse(GHUB_8)

    elif url == 'https://api.github.com/repos/ucsc-cgp/abc/issues/9':
        return MockResponse(GHUB_9)

    elif url == 'https://api.github.com/repos/ucsc-cgp/abc/issues/10':
        return MockResponse(GHUB_10)

    elif url == 'https://api.github.com/repos/ucsc-cgp/abc/issues/11':
        return MockResponse(GHUB_11)

    # Mock to patch a GitHib issue to reassociate it with a different milestone.
    elif args == ('https://api.github.com/repos/ucsc-cgp/abc/issues/11',) and \
            kwargs == {'headers': {'Authorization': 'token token'}, 'json': {'milestone': 3}}:
        return MockResponse(GHUB_11_patched, status_code=200)

    # Mock sprints
    # testsprint1
    elif url == 'https://ucsc-cgl.atlassian.net/rest/agile/1.0/sprint/42/issue':
        return MockResponse(None, status_code=204)

    # testsprint2
    elif url == 'https://ucsc-cgl.atlassian.net/rest/agile/1.0/sprint/13/issue':
        return MockResponse(None, status_code=204)

    # testsprint3
    elif url == 'https://ucsc-cgl.atlassian.net/rest/agile/1.0/sprint/99/issue':
        return MockResponse(None, status_code=204)

    elif 'https://api.github.com/repos/ucsc-cgp/abc/issues/' in url:
        match_obj = re.search(r'issues/(\d*)', url)
        return MockResponse({
            'assignee': None,
            'assignees': [],
            'body': 'Issue Number: TEST-' + match_obj.group(1),  # We just want this to fill in the issue number field
            'created_at': '2019-02-20T22:51:33Z',
            'milestone': None,
            'title': None,
            'updated_at': '2019-04-21T22:51:33Z',
            'number': match_obj.group(1)
            })

    # Mock response for getting milestones of repo:
    elif url == 'https://api.github.com/repos/ucsc-cgp/abc/milestones':
        return MockResponse(
            [{'title': 'testsprint1', 'number': 1}, {'title': 'testsprint2', 'number': 2},
             {'title': 'testsprint3', 'number': 3}], status_code=200)

    # Mock response for getting repo id
    elif url == 'https://api.github.com/repos/ucsc-cgp/abc':
        return MockResponse({'id': 123})

    # Return a blank response indicating a successful update. Some methods expect a 204 response on success
    elif any(x in url for x in ['transitions', 'issue/TEST-', 'epic/TEST-2/issue', 'epic/none/issue']):
        return MockResponse(None, status_code=204)

    # Others expect a 200 response
    elif any(x in url for x in ['estimate', 'moves', 'convert_to_issue', 'convert_to_epic', 'update_issues']):
        return MockResponse(None)

    else:
        raise ValueError(url)


class TestSync(unittest.TestCase):

    def setUp(self):
        """Patch all API requests with put, post, and get. Initialize test boards."""

        # NOTE it's important that the path here refers to where the method is used - the reference to it that's
        # imported in zenhub.py or jira.py, not the original location.
        self.jira_put = patch('src.jira.requests.put', side_effect=mock_response).start()
        self.jira_post = patch('src.jira.requests.post', side_effect=mock_response).start()
        self.zenhub_put = patch('src.zenhub.requests.put', side_effect=mock_response).start()
        self.zenhub_post = patch('src.zenhub.requests.post', side_effect=mock_response).start()
        self.github_patch = patch('src.github.requests.patch', side_effect=mock_response).start()

        self.patch_requests = patch('requests.get', side_effect=mock_response).start()
        self.patch_token = patch('src.access._get_token', return_value='token').start()
        
        self.ZENHUB_REPO = ZenHubRepo(repo_name='abc', org='ucsc-cgp', issues=[str(x) for x in range(1, 5)])
        self.ZENHUB_REPO_SYNC = ZenHubRepo(repo_name='abc', org='ucsc-cgp', issues=[str(x) for x in range(5, 12)])
        self.ZENHUB_ISSUE_1 = self.ZENHUB_REPO.issues['1']

        self.JIRA_REPO = JiraRepo(repo_name='TEST', jira_org='ucsc-cgl')
        self.JIRA_ISSUE_1 = self.JIRA_REPO.issues['TEST-1']

    def tearDown(self):
        patch.stopall()  # Stop all the patches that were started in setUp

    @patch('src.jira.JiraIssue.change_epic_membership')
    @patch('src.zenhub.ZenHubIssue.change_epic_membership')
    @patch('src.zenhub.ZenHubRepo.get_repo_id', return_value={'repo_id': '123'})
    @patch('src.zenhub.ZenHubIssue.get_epic_children', return_value=['3', '4'])
    @patch('src.jira.JiraIssue.get_epic_children', return_value=['TEST-1', 'TEST-3'])
    def test_sync_epics(self, jira_children, zen_children, repo_id, change_zen_epic, change_jira_epic):
        """Test the sync_epics method in isolation"""

        j_epic = self.JIRA_REPO.issues['TEST-2']
        z_epic = self.ZENHUB_REPO.issues['2']

        Sync.sync_epics(j_epic, z_epic)  # test syncing from Jira to ZenHub
        self.assertEqual(change_zen_epic.call_args_list, [call(add='1'), call(remove='4')])

        zen_children.return_value = ['3', '4']  # Not sure why but this needs to be reset

        Sync.sync_epics(z_epic, j_epic)  # test syncing from ZenHub to Jira
        self.assertEqual(change_jira_epic.call_args_list, [call(add='TEST-4'), call(remove='TEST-1')])

    @patch('src.jira.requests.put', side_effect=mock_response)
    @patch('src.jira.requests.post', side_effect=mock_response)
    def test_sync_board_zen_to_jira(self, jira_post, jira_put):
        """Test syncing a repo from ZenHub to Jira.
        Assert that API calls are made in the correct order with correct data."""

        Sync.sync_board(self.ZENHUB_REPO, self.JIRA_REPO)

        # TEST-1 is updated
        self.assertEqual(jira_post.call_args_list[0][1]['json'], {'transition': {'id': 61}})  # TEST-1 to new issue
        self.assertEqual(jira_put.call_args_list[0][1]['json'],
                         {'fields': {'customfield_10014': None}})

        # TEST-2 is updated
        self.assertEqual(jira_post.call_args_list[1][1]['json'], {'transition': {'id': 21}})
        self.assertEqual(jira_put.call_args_list[1][1]['json'],
                         {'fields': {'customfield_10014': 5}})

        # TEST-1 and TEST-3 are added to epic TEST-2
        self.assertEqual(jira_post.call_args_list[2][1]['json'], {'issues': ['TEST-1']})
        self.assertEqual(jira_post.call_args_list[3][1]['json'], {'issues': ['TEST-3']})

        # TEST-3 is updated to Story, causing TEST-2 and TEST-4 to no longer be its children
        self.assertEqual(jira_post.call_args_list[4][1]['json'], {'transition': {'id': 41}})
        self.assertEqual(jira_put.call_args_list[2][1]['json'],
                         {'fields': {'customfield_10014': 2}})

        # TEST-4 is updated
        self.assertEqual(jira_post.call_args_list[5][1]['json'], {'transition': {'id': 21}})
        self.assertEqual(jira_put.call_args_list[3][1]['json'],
                         {'fields': {'customfield_10014': 2}})

    @patch('src.github.requests.patch', side_effect=mock_response)
    @patch('src.zenhub.requests.put', side_effect=mock_response)
    @patch('src.zenhub.requests.post', side_effect=mock_response)
    def test_sync_board_jira_to_zen(self, zenhub_post, zenhub_put, github_patch):
        """Test syncing a repo from Jira to ZenHub.
        Assert that API calls are made in the correct order with correct data."""

        Sync.sync_board(self.JIRA_REPO, self.ZENHUB_REPO)

        # 1 is updated in ZenHub and GitHub
        self.assertEqual(zenhub_post.call_args_list[0][1]['json'], {'pipeline_id': '200', 'position': 'top'})
        self.assertEqual(zenhub_put.call_args_list[0][1]['json'], {'estimate': 0})

        # 2 is converted to issue and updated in ZenHub and GitHub
        self.assertEqual(zenhub_post.call_args_list[1][1]['json'], {'issues': [{'repo_id': '123', 'issue_number': '2'}]})
        self.assertEqual(zenhub_post.call_args_list[2][1]['json'], {'pipeline_id': '600', 'position': 'top'})
        self.assertEqual(zenhub_put.call_args_list[1][1]['json'], {'estimate': 2.0})

        # 3 is converted to epic and updated in ZenHub and GitHub
        self.assertEqual(zenhub_post.call_args_list[3][1]['json'], {'issues': [{'repo_id': '123', 'issue_number': '3'}]})
        self.assertEqual(zenhub_post.call_args_list[4][1]['json'], {'pipeline_id': '700', 'position': 'top'})
        self.assertEqual(zenhub_put.call_args_list[2][1]['json'], {'estimate': 3.0})

        # 2 and 4 are added to epic 3 through ZenHub
        self.assertEqual(zenhub_post.call_args_list[5][1]['json'], {'add_issues': [{'repo_id': 123, 'issue_number': 2}]})
        self.assertEqual(zenhub_post.call_args_list[6][1]['json'], {'add_issues': [{'repo_id': 123, 'issue_number': 4}]})

        # 4 is updated in ZenHub and GitHub
        self.assertEqual(zenhub_post.call_args_list[7][1]['json'], {'pipeline_id': '200', 'position': 'top'})
        self.assertEqual(zenhub_put.call_args_list[3][1]['json'], {'estimate': 4.0})

    @patch('src.sync.Sync.sync_from_specified_source')
    def test_mirror_sync(self, sync):
        """Assert that two issues are synced from Jira to ZenHub and two from ZenHub to Jira, based on timestamps."""
        Sync.mirror_sync(self.JIRA_REPO, self.ZENHUB_REPO)

        # Call args list has the addresses of issues being synced, which change each time, so just look at issue type
        called_with = [(call[0][0].__class__.__name__, call[0][1].__class__.__name__) for call in sync.call_args_list]
        expected = [('JiraIssue', 'ZenHubIssue'), ('JiraIssue', 'ZenHubIssue'), ('ZenHubIssue', 'JiraIssue'),
                    ('ZenHubIssue', 'JiraIssue')]
        self.assertEqual(called_with, expected)

    @patch('src.github.requests.patch', side_effect=mock_response)
    @patch('src.jira.requests.put', side_effect=mock_response)
    @patch('src.jira.requests.get', side_effect=mock_response)
    @patch('src.jira.requests.post', side_effect=mock_response)
    def test_sync_sprint(self, jira_post, jira_get, jira_put, git_patch):
        # This only test from ZenHub to Jira. Tests from Jira to ZenHub are logically identical and therefore
        # tests don't cover most of the Jira -> Zen, except for the last test.

        # Trivial test: Zen issue not part of a milestone, the corresponding Jira story is not part of a sprint.
        # No action required.
        zen = ZenHubIssue(repo=self.ZENHUB_REPO_SYNC, key='5')
        jira = JiraIssue(repo=self.JIRA_REPO, key='JIRA-5')
        assert zen.milestone_name is None
        assert jira.sprint_id is None
        Sync.sync_sprints(zen, jira)
        self.assertTrue(zen.milestone_name is None)
        self.assertEqual(jira_post.call_args_list, [])

        # Zen issue is part of a milestone, and its title is same as the equivalent Jira story. Again, no action needed.
        zen = ZenHubIssue(repo=self.ZENHUB_REPO_SYNC, key='6')
        jira = JiraIssue(repo=self.JIRA_REPO, key='JIRA-6')
        assert zen.milestone_name == 'testsprint1'
        assert jira.sprint_name == 'testsprint1'
        Sync.sync_sprints(zen, jira)
        self.assertEqual(zen.milestone_name, 'testsprint1')
        self.assertEqual(jira.sprint_name, 'testsprint1')
        self.assertEqual(jira_post.call_args_list, [])

        # Zen issue is part of a milestone, but corresponding Jira issue is not. Tests whether Jira issue has been added
        # to the Jira sprint of the equivalent name.
        zen = ZenHubIssue(repo=self.ZENHUB_REPO_SYNC, key='7')
        jira = JiraIssue(repo=self.JIRA_REPO, key='JIRA-7')
        assert zen.milestone_name == 'testsprint1'
        assert jira.sprint_name is None
        Sync.sync_sprints(zen, jira)
        self.assertEqual('https://ucsc-cgl.atlassian.net/rest/agile/1.0/sprint/42/issue', jira_post.mock_calls[0][1][0])
        expected = {'headers': {'Authorization': 'Basic token'}, 'json': {'issues': ['JIRA-7']}}
        observed = jira_post.mock_calls[0][2]
        self.assertEqual(expected, observed)

        # Zen issue is part of a milestone, but no corresponding sprint with the milestone title exists in Jira.
        zen = ZenHubIssue(repo=self.ZENHUB_REPO_SYNC, key='8')
        assert zen.milestone_name == 'testsprint2'
        jira = JiraIssue(repo=self.JIRA_REPO, key='JIRA-8')
        assert jira.sprint_name is None
        Sync.sync_sprints(zen, jira)
        self.assertEqual(jira.sprint_id, None)

        # Zen issue is not part of a milestone, but corresponding Jira issue is part of a sprint.
        zen = ZenHubIssue(repo=self.ZENHUB_REPO_SYNC, key='9')
        assert zen.milestone_name == None
        jira = JiraIssue(repo=self.JIRA_REPO, key='JIRA-9')
        assert jira.sprint_name == 'testsprint1'
        assert jira.sprint_id == 42
        Sync.sync_sprints(zen, jira)
        self.assertTrue(jira_put.called)
        self.assertEqual(jira_put.call_args[0][0], 'https://ucsc-cgl.atlassian.net/rest/api/latest/issue/JIRA-9')
        self.assertEqual(jira_put.mock_calls[0][2]['json']['fields']['customfield_10010'], None)
        self.assertEqual(jira.sprint_id, None)
        self.assertEqual(jira.sprint_name, None)
        self.assertEqual(zen.milestone_name, None)

        # Zen issue is part of a milestone, and Jira issue is part of sprint, but milestone name and sprint name
        # do not match. Assert no HTTP calls are made.
        zen = ZenHubIssue(repo=self.ZENHUB_REPO_SYNC, key='10')
        assert zen.milestone_name == 'testsprint2'
        jira = JiraIssue(repo=self.JIRA_REPO, key='JIRA-10')
        assert jira.sprint_name == 'testsprint1'
        assert jira.sprint_id == 42
        expected = (27, 1, 1)  # counts of get, post and put calls up to this point
        Sync.sync_sprints(zen, jira)
        observed = (jira_get.call_count, jira_post.call_count, jira_put.call_count)
        self.assertEqual(expected, observed)

        # Zen issue is part of a milestone, and Jira issue is part of sprint, but milestone name and sprint name
        # do not match. But sprint in Jira with the same name as in Zen exists.
        zen = ZenHubIssue(repo=self.ZENHUB_REPO_SYNC, key='11')
        assert zen.milestone_name == 'testsprint1'
        jira = JiraIssue(repo=self.JIRA_REPO, key='JIRA-11')
        assert jira.sprint_name == 'testsprint3'
        assert jira.sprint_id == 99
        expected = (32, 2, 2)  # counts of get, post and put calls up to this point
        Sync.sync_sprints(zen, jira)
        self.assertEqual('testsprint1', jira.sprint_name)
        self.assertTrue(jira.sprint_name == zen.milestone_name)
        self.assertEqual(42, jira.sprint_id)
        self.assertEqual('https://ucsc-cgl.atlassian.net/rest/agile/1.0/sprint/42/issue', jira_post.mock_calls[2][1][0])
        self.assertEqual('JIRA-11', jira_post.mock_calls[2][2]['json']['issues'][0])
        observed = (jira_get.call_count, jira_post.call_count, jira_put.call_count)
        self.assertEqual(expected, observed)

        # Jira issue is part of a sprint, and Zen issue is part of milestone, but sprint name and milestone name
        # do not match. But milestone in Zen with the same name as Jira sprint exists.
        jira = JiraIssue(repo=self.JIRA_REPO, key='JIRA-11')
        assert jira.sprint_name == 'testsprint3'
        zen = ZenHubIssue(repo=self.ZENHUB_REPO_SYNC, key='11')
        assert zen.milestone_name == 'testsprint1'
        assert zen.milestone_id == 1
        Sync.sync_sprints(jira, zen)
        self.assertEqual('testsprint3', zen.milestone_name)
        self.assertTrue(jira.sprint_name == zen.milestone_name)
        self.assertEqual(3, zen.milestone_id)
        self.assertEqual('https://api.github.com/repos/ucsc-cgp/abc/issues/11', git_patch.call_args[0][0])
        self.assertEqual({'milestone': 3}, git_patch.call_args[1]['json'])
