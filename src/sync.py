import copy
import time

from src.jira import JiraBoard, JiraIssue
from src.zenhub import ZenHubBoard, ZenHubIssue


class Sync:
    """Assumptions:
    - Unito has run currently, so that
        - Each issue has a counterpart in each management system
        - Each issue's description says the name of the issue it's linked with"""
    @staticmethod
    def sync_board(source: 'Board', sink: 'Board'):

        if source.__class__.__name__ == 'ZenHubBoard' and sink.__class__.__name__ == 'JiraBoard':
            for issue in source.issues.values():
                Sync.sync_from_specified_source(issue, sink.issues[issue.jira_key])

        elif source.__class__.__name__ == 'JiraBoard' and sink.__class__.__name__ == 'ZenHubBoard':
            for issue in source.issues.values():
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

                    except RuntimeError as e:
                        print(repr(e))
                        time.sleep(10)  # The API rate limit may have been reached
                        continue

    @staticmethod
    def sync_from_specified_source(source: 'Issue', destination: 'Issue'):

        # ZenHub issue types have to be changed through a separate request
        if destination.__class__.__name__ == 'ZenHubIssue':
            if source.issue_type == 'Epic' and destination.issue_type != 'Epic':
                destination.promote_issue_to_epic()
            elif source.issue_type != 'Epic' and destination.issue_type == 'Epic':
                destination.demote_epic_to_issue()

            # Some fields like description and title have to be updated thru GitHub
            destination.github_equivalent.update_from(source)
            destination.github_equivalent.update_remote()

        destination.update_from(source)
        destination.update_remote()

        if source.issue_type == 'Epic':  # By this point destination will also be an Epic
            Sync.sync_epics(source, destination)

    @staticmethod
    def sync_from_most_current(a: 'Issue', b: 'Issue'):

        if a.updated > b.updated:  # a is the most current
            Sync.sync_from_specified_source(a, b)  # use a as the source
        else:
            Sync.sync_from_specified_source(b, a)

    @staticmethod
    def sync_epics(source: 'Issue', sink: 'Issue'):

        # TODO condense

        if source.__class__.__name__ == 'ZenHubIssue' and sink.__class__.__name__ == 'JiraIssue':
            sink_children = sink.get_epic_children()  # list

            for issue in source.children:  # It could have 0 children
                z = source.zenhub_board.issues[str(issue)]

                if z.jira_key not in sink_children:  # issue belongs to this epic in ZenHub but not Jira yet
                    sink.add_to_this_epic(z.jira_key)
                else:  # issue belongs to this epic in both ZenHub and Jira
                    sink_children.remove(z.jira_key)  # remove it from the list so we can tell if any are left at the end

            for issue in sink_children:  # any issues left in this list do not belong to the epic in ZenHub,
                sink.remove_from_this_epic(issue)  # so we remove them from the epic in Jira

        elif source.__class__.__name__ == 'JiraIssue' and sink.__class__.__name__ == 'ZenHubIssue':
            source_children = source.get_epic_children()  # list
            sink_children = copy.deepcopy(sink.children)  # make a copy to be edited

            for issue in source_children:
                j = source.jira_board.issues[issue]

                if j.github_key not in sink.children:  # issue belongs to this epic in Jira but not ZenHub
                    sink.change_epic_membership(add=j.github_key)
                else:  # issue belongs to this epic in both Jira and ZenHub
                    sink_children.remove(j.github_key)  # remove it from the list so we can tell if any are left at the end

            for issue in sink_children:  # any issues left in this list do not belong to the epic in Jira,
                sink.change_epic_membership(remove=issue)  # so we remove them from the epic in ZenHub


if __name__ == '__main__':
    a = JiraBoard(repo='TEST', org='ucsc-cgl')
    b = ZenHubBoard(repo='sync-test', org='ucsc-cgp')
    Sync.sync_board(a, b)


