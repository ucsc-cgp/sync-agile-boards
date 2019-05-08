from src.jira import JiraRepo
from src.sync import Sync
from src.zenhub import ZenHubRepo


def main():
    """Print information about the specified Jira issue, get the corresponding GitHub issue, update the remote
    Jira issue, and print its information after updating."""

    print('sync-agile-boards')
    jira_org = input('Enter the name of your Jira organization: ')
    jira_repo = input('Enter the name of your Jira repo to sync: ')
    zenhub_org = input('Enter the name of your ZenHub/GitHub organization: ')
    zenhub_repo = input('Enter the name of your ZenHub/GitHub repo to sync: ')
    source = input('Which repo do you want to make the source to sync from? (jira/zenhub/mirror) ')

    print('Getting Jira data...')
    j = JiraRepo(repo_name=jira_repo, jira_org=jira_org)
    print('Getting ZenHub/GitHub data...')
    z = ZenHubRepo(repo_name=zenhub_repo, org=zenhub_org)
    print('Starting synchronization...')
    if source == 'jira':
        Sync.sync_board(j, z)
    elif source == 'zenhub':
        Sync.sync_board(z, j)
    else:
        print('This is not supported')
        exit(0)

if __name__ == '__main__':
    main()
