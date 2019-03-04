from src.jira import JiraIssue
from datetime import datetime
from src.github import GitHubIssue
from src.zenhub import ZenHubIssue
import sys


def main():
    a = JiraIssue(key='TEST-20')
    b = JiraIssue(key='TEST-22')
    sync_with_most_current(a, b)


def sync_remote_issue(source, destination):
    destination.update_from(source)
    destination.update_remote()


def sync_with_most_current(a, b):
    a_date = datetime.datetime.strptime(a.updated.split('.')[0], '%Y-%m-%dT%H:%M:%S')
    b_date = datetime.datetime.strptime(b.updated.split('.')[0], '%Y-%m-%dT%H:%M:%S')

    if a_date > b_date:
        b.update_from(a)
        b.update_remote()
    else:
        a.update_from(b)
        a.update_remote()


if __name__ == '__main__':
    main()

