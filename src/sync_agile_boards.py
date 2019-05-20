import argparse
import json

from src.jira import JiraIssue, JiraRepo
from src.sync import Sync
from src.zenhub import ZenHubIssue, ZenHubRepo

# TODO more options that would be nice to have:
#    - should automatically add in epic children to the sync list if they are not given


def main():
    parser = argparse.ArgumentParser()  # Make an argument parser with subparsers
    subparsers = parser.add_subparsers()

    # If the first argument is 'file', the next and only other argument should be a config file
    file_parser = subparsers.add_parser('file', help='use a config file to run sync commands for one or more repos')
    file_parser.add_argument('config_file', help='specify path to a JSON config file. see README for details')

    # Alternatively if the first arg is 'repo', there are more options
    no_file_parser = subparsers.add_parser('repo', help='specify one repo to sync in the command line')

    # In this subparser a Jira repo and ZenHub repo must be specified
    no_file_parser.add_argument('jira', help='Jira organization and repo to sync separated by a forward slash')
    no_file_parser.add_argument('zenhub', help='ZenHub organization and repo to sync separated by a forward slash')

    # One of these three flags is required to indicate the direction of syncing
    source_group = no_file_parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument('-j', action='store_true', help='Use the Jira repo as the source to sync from')
    source_group.add_argument('-z', action='store_true', help='Use the ZenHub repo as the source to sync from')
    source_group.add_argument('-m', action='store_true', help='For each issue use the most current copy as the source')

    # One of these flags may be added to sync just a subset of the repo
    filter_group = no_file_parser.add_mutually_exclusive_group(required=False)
    filter_group.add_argument('-o', '--open_only', action='store_true', help='Only sync issues that are open in ZenHub')
    filter_group.add_argument('-jql', '--jira_query_language', help='Only sync issues that match this query in Jira')
    filter_group.add_argument('-zi', '--zenhub_issues', help='Only sync this list of ZenHub issue numbers e.g. "1, 5, 3"')

    args = parser.parse_args()  # Get the arguments that were entered

    if 'file' in args:  # Use a config file and parse each command in the list as if it were entered in the command line
        with open(args.config_file, 'r') as f:
            config = json.loads(f)
            for command in config['sync_configs']:  # A list of strings
                args = parser.parse_args(command.split(' '))
                run_synchronization(args)
    else:
        run_synchronization(args)


def run_synchronization(args):
    """Run synchronization as specified in the given command line arguments"""

    jira_org, jira_repo = args.jira.split('/')
    zenhub_org, zenhub_repo = args.zenhub.split('/')

    if args.open_only or args.zenhub_issues:  # Only syncing a subset of issues that is defined in ZenHub
        # Get all ZenHub issues that match the filter - are open or are in a given list
        zenhub = ZenHubRepo(repo_name=zenhub_repo, org=zenhub_org, issues=args.zenhub_issues, open_only=args.open_only)
        jira = JiraRepo(repo_name=jira_repo, jira_org=jira_org, jql='issues in ()')  # Make a JiraRepo with no issues
        for issue in zenhub.issues.values():  # Then add in each issue that has a match in the ZenHub subset
            jira.issues[issue.jira_key] = JiraIssue(repo=jira, key=issue.jira_key)

    elif args.jira_query_language:  # Only syncing issues that match this Jira query
        jira = JiraRepo(repo_name=jira_repo, jira_org=jira_org, jql=args.jira_query_language)  # Get all Jira issues in the repo that match the query
        zenhub = ZenHubRepo(repo_name=zenhub_repo, org=zenhub_org, issues=[])  # Make a ZenHubRepo with no issues
        for issue in jira.issues.values():  # Then add in each issue that has a match in the filtered Jira subset
            zenhub.issues[issue.github_key] = ZenHubIssue(repo=zenhub, key=issue.github_key)

    else:  # Syncing all issues in both repos
        jira = JiraRepo(repo_name=jira_repo, jira_org=jira_org)
        zenhub = ZenHubRepo(repo_name=zenhub_repo, org=zenhub_org, open_only=args.open_only)

    if args.j:
        Sync.sync_board(source=jira, sink=zenhub)
    elif args.z:
        Sync.sync_board(source=zenhub, sink=jira)
    else:
        pass  # replace with mirror sync when other pr is merged


if __name__ == '__main__':
    main()
