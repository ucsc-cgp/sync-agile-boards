from src.jira import JiraBoard, JiraIssue
from src.sync import Sync
from src.zenhub import ZenHubBoard, ZenHubIssue
import sys


def main():
    """Print information about the specified Jira issue, get the corresponding GitHub issue, update the remote
    Jira issue, and print its information after updating."""

    jira_board = JiraBoard(repo='TEST', org='ucsc-cgl', issues=['TEST-97', 'TEST-98', 'TEST-42', 'TEST-43'])
    zen_board = ZenHubBoard(repo='sync-test', org='ucsc-cgp', issues=['14', '63', '7', '8'])
    for i in jira_board.issues.values():
        i.print()
    for j in zen_board.issues.values():
        j.print()

    Sync.sync_board(zen_board, jira_board)


if __name__ == '__main__':
    main()
