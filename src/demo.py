from src.jira import JiraRepo, JiraIssue
from src.sync import Sync
from src.zenhub import ZenHubRepo, ZenHubIssue
import sys


def main():
    """Print information about the specified Jira issue, get the corresponding GitHub issue, update the remote
    Jira issue, and print its information after updating."""

    jira_board = JiraRepo(repo_name='TEST', org='ucsc-cgl', issues=['TEST-97', 'TEST-98', 'TEST-42', 'TEST-43'])
    zen_board = ZenHubRepo(repo_name='sync-test', org='ucsc-cgp', issues=['14', '63', '7', '8'])
    for i in jira_board.issues.values():
        i.print()
    for j in zen_board.issues.values():
        j.print()

    Sync.sync_board(jira_board, zen_board)


if __name__ == '__main__':
    main()
