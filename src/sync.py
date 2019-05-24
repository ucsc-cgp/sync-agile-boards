import time
import logging

logger = logging.getLogger(__name__)


class Sync:
    """Assumptions:
    - Unito has run currently, so that
        - Each issue has a counterpart in each management system
        - Each issue's description says the name of the issue it's linked with"""
    @staticmethod
    def sync_board(source: 'Board', sink: 'Board'):

        if source.__class__.__name__ == 'ZenHubRepo' and sink.__class__.__name__ == 'JiraRepo':
            for issue in source.issues.values():
                try:
                    Sync.sync_from_specified_source(issue, sink.issues[issue.jira_key])
                except KeyError as e:
                    print(e)
                    print(f'Skipping issue {issue.github_key}: {issue.jira_key} not found in Jira board')

        elif source.__class__.__name__ == 'JiraRepo' and sink.__class__.__name__ == 'ZenHubRepo':
            for key, issue in source.issues.items():
                print(f'syncing {sink.issues[issue.github_key]} from {key}')
                for i in range(3):  # Allow for 3 tries
                    try:
                        if issue.github_key:
                            try:
                                Sync.sync_from_specified_source(issue, sink.issues[issue.github_key])
                            except KeyError as e:
                                raise ValueError(f'Issue {issue.github_key} referenced from {issue.jira_key} not found in board')
                        else:
                            print("skipping this issue")
                        break

                    except RuntimeError as e:  # The API rate limit may have been reached
                        print(repr(e))
                        time.sleep(10)  # Try again in 10 seconds, hopefully the API limit will have reset
                        continue

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
            print(f'syncing {b} (updated at {b.updated}) from {a} (updated at {a.updated})')
            Sync.sync_from_specified_source(a, b)  # use a as the source
        else:
            print(f'syncing {a} (updated at {a.updated}) from {b} (updated at {b.updated})')
            Sync.sync_from_specified_source(b, a)

    @staticmethod
    def sync_epics(source: 'Issue', sink: 'Issue'):

        # Get lists of epic children
        source_children = source.get_epic_children()
        sink_children = sink.get_epic_children()

        for issue in source_children:  # It could have 0 children
            source_child = source.repo.issues[str(issue)]  # Get the Issue object by its key

            if source_child.__class__.__name__ == 'ZenHubIssue':  # Get the key of the same issue in the opposite
                twin_key = source_child.jira_key                  # management system
            else:
                twin_key = source_child.github_key

            if twin_key not in sink_children:  # issue belongs to this epic in source but not sink yet,
                sink.change_epic_membership(add=twin_key)  # so add it as a child of sink

            else:  # issue already belongs to this epic in both source and sink; remove it from the list so we can
                sink_children.remove(twin_key)  # tell if any are left at the end

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
