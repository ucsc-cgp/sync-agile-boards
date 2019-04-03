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
    def sync_epics(source: 'Issue', destination: 'Issue'):
        # TODO This is a little weird because ZenHub issues don't know what epic they belong to. So updating a Jira epic
        #  from its info in ZenHub affects all child issues but not the destination epic being updated. Not sure if
        #  this is the best way to do it
        if source.__class__.__name__ == 'ZenHubIssue' and destination.__class__.__name__ == 'JiraIssue':
            print("from zenhub to jira")
            dest_children = destination.get_epic_children()  # list

            print(source.children)
            if source.children:  # This issue is an epic
                for issue in source.children:
                    z = ZenHubIssue(key=issue, repo_name=source.repo_name)  # use ZenHub to get name of corresponding Jira issue
                    if z.jira_key not in dest_children:  # issue belongs to this epic in ZenHub but not Jira yet
                        print("adding %s to epic %s" % (z.jira_key, destination.jira_key))
                        j = JiraIssue(key=z.jira_key)
                        j.add_to_epic(destination.jira_key)
                    else:  # issue belongs to this epic in both ZenHub and Jira
                        print("no change needed")
                        dest_children.remove(z.jira_key)  # remove it from the list so we can tell if any are left at the end

                for issue in dest_children:  # any issues left in this list do not belong to the epic in ZenHub,
                    print("removing %s from epic %s" % (issue, destination.jira_key))
                    j = JiraIssue(key=issue)  # so we remove them from the epic in Jira
                    j.remove_from_epic(destination.jira_key)

        elif source.__class__.__name__ == 'JiraIssue' and destination.__class__.__name__ == 'ZenHubIssue':
            print("from jira to zenhub")
            # TODO this is inefficient and the whole board should be done at one time
            parent_name = None
            if source.parent:
                j_parent = JiraIssue(key=source.parent)  # use Jira to get corresponding ZenHub parent issue
                parent_name = j_parent.github_key
                z_parent = ZenHubIssue(key=j_parent.github_key, repo_name=j_parent.github_repo_name)

            # Make sure this issue belongs to the correct epic, if any, and no others
            for e in destination.get_all_epics_in_this_repo():
                if str(e) == parent_name:  # if issue doesn't belong to any epic, parent=None, and this never gets called

                    if z_parent.is_epic is False:  # the parent issue is an epic in Jira but not yet in ZenHub
                        z_parent.update_issue_to_epic()  # make it an epic in ZenHub

                    if destination.github_key not in z_parent.children:  # verify the ZenHub issue being updated belongs to the
                        destination.change_epic_membership(z_parent.github_key, action='add')  # correct epic in ZenHub

                else:  # Make sure this issue doesn't belong to any other epics
                    epic = ZenHubIssue(key=e, repo_name=destination.github_repo_name)
                    if int(destination.github_key) in epic.children:
                        destination.change_epic_membership(epic.github_key, action='remove')
        else:
            raise ValueError("You should not be syncing two issues of the same type")


if __name__ == '__main__':
    z = ZenHubIssue(key=7, repo_name='sync-test')
    j = JiraIssue(key='TEST-42')
    j.print()
    Sync.sync_from_specified_source(z, j)
    j = JiraIssue(key='TEST-42')
    j.print()



