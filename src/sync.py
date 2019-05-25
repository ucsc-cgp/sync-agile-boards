import logging
import time

logger = logging.getLogger(__name__)


class Sync:
    """Assumptions:
    - Unito has run currently, so that
        - Each issue has a counterpart in each management system
        - Each issue's description says the name of the issue it's linked with"""
    @staticmethod
    def sync_board(source: 'Repo', sink: 'Repo'):

        if source.__class__.__name__ == 'ZenHubRepo' and sink.__class__.__name__ == 'JiraRepo':
            for key, issue in source.issues.items():
                try:
                    if issue.jira_key:
                        logging.info(f'Syncing from {source.name} issue {key} to issue {issue.jira_key}')
                        Sync.sync_from_specified_source(issue, sink.issues[issue.jira_key])
                    else:
                        logging.warning(f'Skipping issue {key}: no Jira link found')

                except RuntimeError as e:
                    logging.warning(f'Skipping issue {key}: {repr(e)}')

                except KeyError as e:
                    logging.warning(repr(e) + f'Skipping this issue - matching issue in Jira not found')

        elif source.__class__.__name__ == 'JiraRepo' and sink.__class__.__name__ == 'ZenHubRepo':
            for key, issue in source.issues.items():
                for i in range(3):  # Allow for 3 tries
                    try:
                        if issue.github_key:
                            logging.info(f'Syncing from issue {key} to {sink.name} issue {issue.github_key}')
                            Sync.sync_from_specified_source(issue, sink.issues[issue.github_key])
                        else:
                            logging.warning(f'Skipping issue {key}: no GitHub link found')
                        break

                    except RuntimeError as e:
                        logging.warning(repr(e) + f' (attempt {i+1} of 3). Waiting 10 seconds before retrying...')
                        time.sleep(10)  # The API rate limit may have been reached
                        continue
                    except KeyError as e:
                        logging.warning(repr(e) + f'Issue not found. Going to next issue')

    @staticmethod
    def mirror_sync(jira_repo: 'JiraRepo', zenhub_repo: 'ZenHubRepo'):
        for issue in jira_repo.issues.values():
            twin = zenhub_repo.issues[issue.github_key]
            Sync.sync_from_most_current(issue, twin)

    @staticmethod
    def sync_from_specified_source(source: 'Issue', destination: 'Issue'):
        # ZenHub issue types have to be changed through a separate request
        if destination.__class__.__name__ == 'ZenHubIssue':
            if source.issue_type == 'Epic' and destination.issue_type != 'Epic':
                destination.promote_issue_to_epic()
            elif source.issue_type != 'Epic' and destination.issue_type == 'Epic':
                destination.demote_epic_to_issue()

        destination.update_from(source)
        destination.update_remote()

        if source.issue_type == 'Epic':  # By this point destination will also be an Epic
            Sync.sync_epics(source, destination)

    @staticmethod
    def sync_from_most_current(a: 'Issue', b: 'Issue'):

        if a.updated > b.updated:  # a is the most current
            logging.info(f'Syncing {b} (updated at {b.updated}) from {a} (updated at {a.updated})')
            Sync.sync_from_specified_source(a, b)  # use a as the source
        else:
            logging.info(f'Syncing {a} (updated at {a.updated}) from {b} (updated at {b.updated})')
            Sync.sync_from_specified_source(b, a)

    @staticmethod
    def sync_epics(source: 'Issue', sink: 'Issue'):
        logger.info('This is an epic. Synchronizing epic membership of all its issues...')
        # Get lists of epic children
        source_children = source.get_epic_children()
        sink_children = sink.get_epic_children()

        for issue in source_children:  # It could have 0 children

            # If a subset of all issues is being synced, it's possible that epics in the subset have children that
            # aren't in the subset. To avoid KeyErrors, check if each child issue is in the subset we already have
            if issue in source.repo.issues:  # information for:
                source_child = source.repo.issues[str(issue)]             # If so, get the Issue object by its key
            else:
                logging.info(f'No information for {issue}. Getting information to update epic membership')
                source_child = type(source)(key=issue, repo=source.repo)  # If not, make a new Issue object for it

            if source_child.__class__.__name__ == 'ZenHubIssue':  # Get the key of the same issue in the opposite
                twin_key = source_child.jira_key                  # management system
            else:
                twin_key = source_child.github_key

            if twin_key:
                if twin_key not in sink_children:  # issue belongs to this epic in source but not sink yet,
                    sink.change_epic_membership(add=twin_key)  # so add it as a child of sink

                else:  # issue already belongs to this epic in both source and sink; remove it from the list so we can
                    sink_children.remove(twin_key)  # tell if any are left at the end
            else:
                logging.warning(f'Cannot update issue {issue} epic membership in other management system - no link identified')

        for issue in sink_children:              # any issues left in this list do not belong to the epic in source,
            sink.change_epic_membership(remove=issue)  # so they are removed from the epic in sink.

    @staticmethod
    def sync_sprints(source: 'Issue', sink: 'Issue'):

        if source.__class__.__name__ == 'ZenHubIssue':
            if source.github_milestone is None:
                logger.info(f'Sync sprint: Issue {source.github_key} does not belong to any sprint')
                return
            elif sink.github_milestone == source.github_milestone:
                logger.info(f'Sync sprint: Issue {sink.jira_key} is in sprint {source.github_milestone}')
                return
            else:
                assert sink.__class__.__name__ == 'JiraIssue'
                if sink.jira_sprint_id is None:
                    sprint_title = source.github_milestone
                    status_code = sink._get_sprint_id(sprint_title)
                    if status_code == 200:
                        logger.info(f'Sync sprint: Added issue {sink.jira_key} to sprint {sprint_title}')
                        sink.add_to_sprint()
                    else:
                        logger.warning(
                            f'Sync sprint: No Sprint ID found for {sink.jira_key} and sprint title {sprint_title}')
                        return
