import logging
import time
from tqdm import tqdm

from settings import number_of_retries

logger = logging.getLogger(__name__)


class Sync:
    """Assumptions:
    - Unito has run currently, so that
        - Each issue has a counterpart in each management system
        - Each issue's description says the name of the issue it's linked with"""
    @staticmethod
    def sync_board(source: 'Repo', dest: 'Repo'):
        """
        For each pair of repos, sync from the issue in the source repo to that in the dest repo.
        Alternative to mirror_sync.
        :param source: This repo's issues will be replicated in the sink repo
        :param dest: This repo's issues will be updated to match those in the source
        """

        if source.__class__.__name__ == 'ZenHubRepo' and dest.__class__.__name__ == 'JiraRepo':
            for key, issue in tqdm(source.issues.items(), desc='syncing'):  # progress bar
                try:
                    if issue.jira_key:
                        logging.info(f'Syncing from {source.name} issue {key} to issue {issue.jira_key}')
                        Sync.sync_from_specified_source(issue, dest.issues[issue.jira_key])
                    else:
                        logging.warning(f'Skipping issue {key}: no Jira link found')

                except RuntimeError as e:
                    logging.warning(f'Skipping issue {key}: {repr(e)}')

                except KeyError as e:
                    logging.warning(repr(e) + f'Skipping this issue - matching issue in Jira not found')

        elif source.__class__.__name__ == 'JiraRepo' and dest.__class__.__name__ == 'ZenHubRepo':
            for key, issue in tqdm(source.issues.items(), desc='syncing'):  # progress bar
                for i in range(number_of_retries):  # Allow for 3 tries
                    try:
                        if issue.github_key:
                            logging.info(f'Syncing from issue {key} to {dest.name} issue {issue.github_key}')
                            Sync.sync_from_specified_source(issue, dest.issues[issue.github_key])
                        else:
                            logging.warning(f'Skipping issue {key}: no GitHub link found')
                        break

                    except RuntimeError as e:
                        logging.warning(repr(e) + f' (attempt {i+1} of {number_of_retries}). '
                                        f'Waiting 10 seconds before retrying...')
                        time.sleep(10)  # The API rate limit may have been reached
                        continue
                    except KeyError as e:
                        logging.warning(repr(e) + f'Issue not found. Going to next issue')

    @staticmethod
    def mirror_sync(jira_repo: 'JiraRepo', zenhub_repo: 'ZenHubRepo'):
        """
        For each pair of issues in the repos, sync based on which is most recently updated. Alternative to sync_board.
        :param jira_repo: JiraRepo to use
        :param zenhub_repo: ZenHubRepo to use
        """

        for key, issue in tqdm(jira_repo.issues.items(), desc='syncing'):  # progress bar
            for i in range(number_of_retries):  # Allow for a fixed number of tries
                try:
                    if issue.github_key:
                        Sync.sync_from_most_current(issue, zenhub_repo.issues[issue.github_key])
                    else:
                        logging.warning(f'Skipping issue {key}: no link to matching issue found')
                    break

                except RuntimeError as e:
                    logging.warning(repr(e) + f' (attempt {i+1} of {number_of_retries}). '
                                    f'Waiting 10 seconds before retrying...')
                    time.sleep(10)  # The API rate limit may have been reached
                    continue
                except KeyError as e:
                    logging.warning(repr(e) + f'Issue not found. Going to next issue')

    @staticmethod
    def sync_from_specified_source(source: 'Issue', dest: 'Issue'):
        """Sync two issues unidirectionally. Calls epic sync and sprint sync methods.
        :param source: This issue's data will be replicated in the dest issue
        :param dest: This issue's data will be updated to match the source
        """
        # ZenHub issue types have to be changed through a separate request
        if dest.__class__.__name__ == 'ZenHubIssue':
            if source.issue_type == 'Epic' and dest.issue_type != 'Epic':
                dest.promote_issue_to_epic()
            elif source.issue_type != 'Epic' and dest.issue_type == 'Epic':
                dest.demote_epic_to_issue()

        Sync.sync_sprints(source, dest)

        dest.update_from(source)
        dest.update_remote()

        if source.issue_type == 'Epic':  # By this point dest will also be an Epic
            Sync.sync_epics(source, dest)

    @staticmethod
    def sync_from_most_current(a: 'Issue', b: 'Issue'):
        """Compare timestamps of two issues sync them, using the most recently updated as the source"""

        if a.updated > b.updated:  # a is the most current
            logging.info(f'Syncing {b} (updated at {b.updated}) from {a} (updated at {a.updated})')
            Sync.sync_from_specified_source(a, b)  # use a as the source
        else:
            logging.info(f'Syncing {a} (updated at {a.updated}) from {b} (updated at {b.updated})')
            Sync.sync_from_specified_source(b, a)

    @staticmethod
    def sync_epics(source: 'Issue', dest: 'Issue'):
        """Sync epic membership of two issues
        :param source: This issue's epic membership will be replicated in the sink issue
        :param dest: This issue's epic membership will be updated to match the source
        """
        logger.info('This is an epic. Synchronizing epic membership of all its issues...')
        # Get lists of epic children
        source_children = source.get_epic_children()
        sink_children = dest.get_epic_children()

        for issue in source_children:  # It could have 0 children

            # If a subset of all issues is being synced, it's possible that epics in the subset have children that
            # aren't in the subset. To avoid KeyErrors, check if each child issue is in the subset we already have
            # information for:
            if issue in source.repo.issues:
                source_child = source.repo.issues[str(issue)]  # If so, get the Issue object by its key
            else:
                logging.info(f'No information for {issue}. Getting information to update epic membership')
                source_child = type(source)(key=issue, repo=source.repo)  # If not, make a new Issue object for it

            if source_child.__class__.__name__ == 'ZenHubIssue':  # Get the key of the same issue in the opposite
                twin_key = source_child.jira_key                  # management system
            else:
                twin_key = source_child.github_key

            if twin_key:
                if twin_key not in sink_children:  # issue belongs to this epic in source but not dest yet,
                    dest.change_epic_membership(add=twin_key)  # so add it as a child of dest

                else:  # issue already belongs to this epic in both source and dest; remove it from the list so we can
                    sink_children.remove(twin_key)  # tell if any are left at the end
            else:
                logging.warning(f'Cannot update issue {issue} epic membership in other management system - '
                                f'no link identified')

        for issue in sink_children:  # any issues left in this list do not belong to the epic in source,
            dest.change_epic_membership(remove=issue)  # so they are removed from the epic in dest.

    @staticmethod
    def sync_sprints(source: 'Issue', dest: 'Issue'):
        """
        Sync sprint membership of two issues
        :param source: This issue's sprint status will be replicated in the dest issue
        :param dest: This issue's sprint status will be updated to match the source
        """

        if source.__class__.__name__ == 'ZenHubIssue':
            if source.milestone_name is None:
                logger.debug(f'Sync sprint: Issue {source.github_key} does not belong to any milestone')
                if dest.sprint_id:
                    dest.remove_from_sprint()

            elif dest.sprint_name == source.milestone_name:
                logger.debug(f'Sync sprint: Issue {dest.jira_key} is already in sprint {source.milestone_name}')

            else:
                assert dest.__class__.__name__ == 'JiraIssue'
                if dest.sprint_id is None:
                    milestone_title = source.milestone_name
                    sprint_id = dest.get_sprint_id(milestone_title)
                    if sprint_id:
                        logger.debug(f'Sync sprint: Added issue {dest.jira_key} to sprint {milestone_title}')
                        dest.add_to_sprint(sprint_id)
                    else:
                        logger.warning(
                            f'Sync sprint: No Sprint ID found for {dest.jira_key} and sprint title {milestone_title}')
                else:
                    assert dest.sprint_name != source.milestone_name
                    # Check if any sprint in dest has same name as source.milestone_name. If so, swap.
                    sprint_id = dest.get_sprint_id(source.milestone_name)
                    if sprint_id is not None:
                        logger.info(f'Sync sprint: Found sprint name {source.milestone_name} in Jira project')
                        dest.remove_from_sprint()  # old sprint
                        dest.sprint_name = source.milestone_name
                        dest.sprint_id = sprint_id
                        logger.info(f'Jira issue {dest.jira_key} now part of sprint {dest.sprint_name}')
                        dest.add_to_sprint(sprint_id)  # new sprint
                    else:
                        logger.warning(
                            f'Sync sprint: Cannot find sprint name {source.milestone_name} in the destination. '
                            f'Association of issue {dest.jira_key} will remain unchanged. Sprint name {dest.sprint_name}'
                            f' does not match milestone name {source.milestone_name} - sprint and milestone names '
                            f'must match!')

        elif source.__class__.__name__ == 'JiraIssue':
            if source.sprint_name is None:
                logger.debug(f'Sync sprint: Issue {source.github_key} does not belong to any milestone')
                if dest.milestone_name:
                    dest.remove_from_milestone()

            elif dest.milestone_name == source.sprint_name:
                logger.debug(f'Sync sprint: Issue {dest.github_key} is already in sprint {source.sprint_name}')

            else:
                assert dest.__class__.__name__ == 'ZenHubIssue'
                if dest.milestone_name is None:
                    sprint_title = source.sprint_name
                    milestone_id = dest.get_milestone_id(sprint_title)
                    if milestone_id:
                        logger.debug(f'Sync sprint: Adding issue {dest.github_key} to sprint {sprint_title}')
                        dest.add_to_milestone(milestone_id)
                    else:
                        logger.warning(
                            f'Sync sprint: No Sprint ID found for {dest.github_key} and sprint title {sprint_title}')
                else:
                    assert dest.milestone_name != source.sprint_name
                    # Logic same as in above leg of conditional.
                    milestone_id = dest.get_milestone_id(source.sprint_name)
                    if milestone_id:
                        logger.info(f'Sync sprint: Found sprint name {source.sprint_name} in GitHub repo')
                        dest.remove_from_milestone()
                        dest.milestone_name = source.sprint_name
                        dest.milestone_id = milestone_id
                        logger.info(f'GitHub issue {dest.github_key} now part of milestone {dest.milestone_name}')
                        dest.add_to_milestone(milestone_id)
                    else:
                        logger.warning(
                            f'Sync sprint: Cannot find sprint name {source.sprint_name} in the destination. '
                            f'Association of issue {dest.milestone_id} will remain unchanged. Milestone name '
                            f'{dest.milestone_name} does not match sprint name {source.sprint_name} - sprint and '
                            f'milestone names must match!')
