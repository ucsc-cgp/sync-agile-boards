import copy
import time

from src.jira import JiraBoard, JiraIssue
from src.zenhub import ZenHubBoard, ZenHubIssue

import pprint


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
            pp = pprint.PrettyPrinter()
            pp.pprint(sink.issues)
            for issue in source.issues.values():
                print("syncing issue " + issue.jira_key)
                for i in range(5):  # Allow for 5 retries
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
            if source.issue_type == 'Epic' and destination.issue_type == 'Issue':
                print(source.jira_key, source.issue_type)
                print(destination.github_key, destination.issue_type)
                print("promoting")
                destination.promote_issue_to_epic()
            elif source.issue_type != 'Epic' and destination.issue_type == 'Epic':
                print(source.jira_key, source.issue_type)
                print(destination.github_key, destination.issue_type)
                print("demoting")
                destination.demote_epic_to_issue()

        destination.update_from(source)
        destination.update_remote()

        if source.issue_type == 'Epic':
            Sync.sync_epics_in_board(source, destination)

    @staticmethod
    def sync_from_most_current(a: 'Issue', b: 'Issue'):

        if a.updated > b.updated:  # a is the most current
            b.update_from(a)
            b.update_remote()
        else:
            a.update_from(b)
            a.update_remote()

    @staticmethod
    def sync_epics_in_board(source: 'Issue', sink: 'Issue'):

        if source.__class__.__name__ == 'ZenHubIssue' and sink.__class__.__name__ == 'JiraIssue':
            sink_children = sink.get_epic_children()  # list

            for issue in source.children:  # It could have 0 children
                z = source.zenhub_board.issues[issue]

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

    @staticmethod
    def sync_epics(source: 'Issue', sink: 'Issue'):
        # TODO This is a little weird because ZenHub issues don't know what epic they belong to. So updating a Jira epic
        #  from its info in ZenHub affects all child issues but not the sink epic being updated. Not sure if
        #  this is the best way to do it

        if source.__class__.__name__ == 'ZenHubIssue' and sink.__class__.__name__ == 'JiraIssue':
            dest_children = sink.get_epic_children()  # list

            if source.issue_type == 'Epic':  # This issue is an epic

                for issue in source.children:  # It could have 0 children
                    z = ZenHubIssue(key=issue, repo=source.github_repo, org=source.github_org)  # use ZenHub to get name of corresponding Jira issue

                    if z.jira_key not in dest_children:  # issue belongs to this epic in ZenHub but not Jira yet
                        sink.add_to_this_epic(z.jira_key)

                    else:  # issue belongs to this epic in both ZenHub and Jira
                        dest_children.remove(z.jira_key)  # remove it from the list so we can tell if any are left at the end

            for issue in dest_children:  # any issues left in this list do not belong to the epic in ZenHub,
                sink.remove_from_this_epic(issue)  # so we remove them from the epic in Jira

        elif source.__class__.__name__ == 'JiraIssue' and sink.__class__.__name__ == 'ZenHubIssue':
            source_children = source.get_epic_children()  # list
            dest_children = copy.deepcopy(sink.children)  # make a copy to be edited
            print("a")
            if source.issue_type == 'Epic':  # This issue is an epic
                if sink.issue_type != 'Epic':
                    sink.promote_issue_to_epic()

                for issue in source_children:
                    j = JiraIssue(key=issue, org=source.jira_org)

                    if j.github_key not in sink.children:  # issue belongs to this epic in Jira but not ZenHub
                        z = ZenHubIssue(key=j.github_key, repo=sink.github_repo, org=sink.github_org)
                        sink.change_epic_membership(add=z.github_key)

                    else:  # issue belongs to this epic in both Jira and ZenHub
                        dest_children.remove(j.github_key)  # remove it from the list so we can tell if any are left at the end

            for issue in dest_children:  # any issues left in this list do not belong to the epic in Jira,
                z = ZenHubIssue(key=issue, repo=sink.github_repo, org=sink.github_org)  # so we remove them from the epic in ZenHub
                sink.change_epic_membership(remove=z.github_key)


if __name__ == '__main__':
    a = JiraBoard(repo='TEST', org='ucsc-cgl')
    b = ZenHubBoard(repo='sync-test', org='ucsc-cgp')
    Sync.sync_board(a, b)


