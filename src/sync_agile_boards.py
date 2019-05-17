import argparse
import json

from src.jira import JiraRepo
from src.sync import Sync
from src.zenhub import ZenHubRepo

# TODO more options that would be nice to have:
#  - optionally sync just a provided list of issues
#    - should only have to enter this list for one management system, the list of matching tickets should be automatically identified
#    - should automatically add in epic children to the sync list if they are not given
#  - optionally only sync open issues
#  - optionally only sync issues that are found using given jql query


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    file_parser = subparsers.add_parser('in', help='use a config file to run sync commands for one or more repos')
    file_parser.add_argument('config_file', help='specify path to a JSON config file. see README for details')

    no_file_parser = subparsers.add_parser('with', help='specify one repo to sync in the command line')
    no_file_parser.add_argument('jira', help='Jira organization and repo to sync separated by a forward slash')
    no_file_parser.add_argument('zenhub', help='ZenHub organization and repo to sync separated by a forward slash')
    group = no_file_parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-j', action='store_true', help='Use the Jira repo as the source to sync from')
    group.add_argument('-z', action='store_true', help='Use the ZenHub repo as the source to sync from')
    group.add_argument('-m', action='store_true', help='For each issue use the most current copy as the source')
    no_file_parser.add_argument('-o', '--open-only', action='store_true', help='Only sync issues that are open in ZenHub')
    no_file_parser.add_argument('-i', '--issues', action='store_true', help='Only sync issues in this list and any that are linked to them')
    no_file_parser.add_argument()

    args = parser.parse_args()

    if 'in' in args:
        with open(args.config_file, 'r') as f:
            config = json.loads(f)
            for command in config['sync_configs']:
                args = parser.parse_args(command.split(' '))
                run_synchronization(args)
    else:
        run_synchronization(args)


def run_synchronization(args):
    """Run synchronization as specified in the given command line arguments"""

    jira_org, jira_repo = args.jira.split('/')
    zenhub_org, zenhub_repo = args.zenhub.split('/')

    jira = JiraRepo(repo_name=jira_repo, jira_org=jira_org)
    zenhub = ZenHubRepo(repo_name=zenhub_repo, org=zenhub_org)

    if args.j:
        Sync.sync_board(source=jira, sink=zenhub)
    elif args.z:
        Sync.sync_board(source=zenhub, sink=jira)
    else:
        pass  # replace with mirror sync when other pr is merged


if __name__ == '__main__':
    main()
