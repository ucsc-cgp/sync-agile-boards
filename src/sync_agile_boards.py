import argparse
import logging
import os
import shlex
import sys
sys.path.append('.')

from src.jira import JiraIssue, JiraRepo
from src.sync import Sync
from src.zenhub import ZenHubIssue, ZenHubRepo

# Set up logging
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s',
                    filename=f'{ROOT_DIR}/sync-agile-boards.log',
                    filemode='w')
# These libraries make a lot of debug-level log messages which make the log file hard to read
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def main():
    """Parse instructions from the command line and run synchronization"""

    # Make an argument parser with subparsers
    parser = argparse.ArgumentParser(description="This is a tool for synchronizing issue point values, sprints, "
                                                 "status/pipeline, epic status and membership between Jira and ZenHub. "
                                                 "See the README for more help and examples.""")
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
    filter_group.add_argument('-zi', '--zenhub_issues', help='Only sync this list of ZenHub issues e.g. "1, 5, 3"')

    no_file_parser.add_argument('-v', '--verbose', action='store_true', help='Write all log messages to the log file')

    args = parser.parse_args()  # Get the arguments that were entered

    if len(vars(args)) == 0:  # Show help message if no arguments are given
        parser.print_help()
        exit(2)

    if 'config_file' in args:  # Use a config file and parse each command in the list as if entered in the command line
        with open(args.config_file, 'r') as f:
            for command in f.readlines():  # A list of strings
                args = parser.parse_args(shlex.split(command))
                run_synchronization(args)
    else:
        run_synchronization(args)


def run_synchronization(args: 'Namespace'):
    """
    Run synchronization as specified in the given command line arguments
    :param args: an argparse Namespace object holding the values of parsed arguments
    """

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)  # Show all log messages

    logger.info(f"Running synchronization with args {str(vars(args))}")

    j_org_name, j_repo_name = args.jira.split('/')
    z_org_name, z_repo_name = args.zenhub.split('/')
    if args.zenhub_issues:
        zenhub_issues_list = args.zenhub_issues.split(",")
    else:
        zenhub_issues_list = None

    if args.open_only or args.zenhub_issues:  # Only syncing a subset of issues that is defined in ZenHub
        # Get all ZenHub issues that match the filter - are open or are in a given list
        zenhub_repo = ZenHubRepo(z_repo_name, z_org_name, issues=zenhub_issues_list, open_only=args.open_only)
        jira_repo = JiraRepo(j_repo_name, j_org_name, empty=True)  # Make a JiraRepo with no issues
        for issue in zenhub_repo.issues.values():  # Then add in each issue that has a match in the ZenHub subset
            try:
                jira_repo.issues[issue.jira_key] = JiraIssue(repo=jira_repo, key=issue.jira_key)
            except RuntimeError as e:
                logger.warning(f'Cannot get information for issue {issue.jira_key}: {e}')

    elif args.jira_query_language:  # Only syncing issues that match this Jira query
        # Get all Jira issues in the repo that match the query
        jira_repo = JiraRepo(j_repo_name, j_org_name, jql=args.jira_query_language)
        zenhub_repo = ZenHubRepo(z_repo_name, z_org_name, issues=[])  # Make a ZenHubRepo with no issues
        for issue in jira_repo.issues.values():  # Then add in each issue that has a match in the filtered Jira subset
            try:
                zenhub_repo.issues[issue.github_key] = ZenHubIssue(repo=zenhub_repo, key=issue.github_key)
            except RuntimeError as e:
                logger.warning(f'Cannot get information for issue {issue.github_key}: {e}')

    else:  # Syncing all issues in both repos
        jira_repo = JiraRepo(j_repo_name, j_org_name)
        zenhub_repo = ZenHubRepo(z_repo_name, z_org_name)

    if args.j:
        Sync.sync_board(source=jira_repo, dest=zenhub_repo)
    elif args.z:
        Sync.sync_board(source=zenhub_repo, dest=jira_repo)
    else:
        Sync.mirror_sync(jira_repo=jira_repo, zenhub_repo=zenhub_repo)
    logger.info("Synchronization finished")


if __name__ == '__main__':
    main()
