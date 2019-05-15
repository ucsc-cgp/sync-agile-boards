from src.jira import JiraRepo
from src.sync import Sync
from src.zenhub import ZenHubRepo


def main():
    """Print information about the specified Jira issue, get the corresponding GitHub issue, update the remote
    Jira issue, and print its information after updating."""

    jira_board = JiraRepo(repo_name='TEST', jira_org='ucsc-cgl')
    zen_board = ZenHubRepo(repo_name='sync-test', org='ucsc-cgp')

    Sync.sync_board(jira_board, zen_board)


if __name__ == '__main__':
    main()
