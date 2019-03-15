import copy

from src.jira import JiraIssue
from src.zenhub import ZenHubIssue


class Sync:

    @staticmethod
    def sync_from_specified_source(source: 'Issue', destination: 'Issue'):
        destination.update_from(source)
        destination.update_remote()
        Sync.sync_epics(source, destination)


    @staticmethod
    def sync_from_most_current(a: 'Issue', b: 'Issue'):

        if a.updated > b.updated:  # a is the most current
            b.update_from(a)
            b.update_remote()
        else:
            a.update_from(b)
            a.update_remote()

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

            if source.issue_type == 'Epic':  # This issue is an epic
                if sink.issue_type != 'Epic':
                    sink.update_issue_to_epic()

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





