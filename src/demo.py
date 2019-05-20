from src.jira import JiraRepo
from src.sync import Sync
from src.zenhub import ZenHubRepo


def main():
    """Print information about the specified Jira issue, get the corresponding GitHub issue, update the remote
    Jira issue, and print its information after updating."""

    print('sync-agile-boards')
    jira_org = input('Enter the name of your Jira organization: ')
    jira_repo = input('Enter the name of your Jira repo to sync: ')
    jira_keys = input('Enter the Jira issues to sync (comma-separated list or leave blank for all): ').split(', ')
    zenhub_org = input('Enter the name of your ZenHub/GitHub organization: ')
    zenhub_repo = input('Enter the name of your ZenHub/GitHub repo to sync: ')
    zenhub_keys = input('Enter the ZenHub issues to sync (comma-separated list or leave blank for all): ').split(', ')
    source = input('Which repo do you want to make the source to sync from? (jira/zenhub/mirror) ')

    print('Getting Jira data...')
    j = JiraRepo(repo_name=jira_repo, jira_org=jira_org, issues=jira_keys)
    print('Getting ZenHub/GitHub data...')
    z = ZenHubRepo(repo_name=zenhub_repo, org=zenhub_org, issues=zenhub_keys)
    print('Starting synchronization...')
    if source == 'jira':
        Sync.sync_board(j, z)
    elif source == 'zenhub':
        Sync.sync_board(z, j)
    elif source == 'mirror':
        Sync.mirror_sync(j, z)
    else:
        print('Invalid input')
        exit(0)

if __name__ == '__main__':
    main()
