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
                        j = JiraIssue(key=z.jira_key)
                        j.add_to_epic(destination.jira_key)

                    else:  # issue belongs to this epic in both ZenHub and Jira
                        dest_children.remove(z.jira_key)  # remove it from the list so we can tell if any are left at the end

            for issue in dest_children:  # any issues left in this list do not belong to the epic in ZenHub,
                j = JiraIssue(key=issue)  # so we remove them from the epic in Jira
                j.remove_from_epic(destination.jira_key)

        elif source.__class__.__name__ == 'JiraIssue' and destination.__class__.__name__ == 'ZenHubIssue':
            source_children = source.get_epic_children()  # list
            dest_children = copy.deepcopy(destination.children)  # make a copy to be edited

            if source_children:  # This issue is an epic
                for issue in source_children:
                    j = JiraIssue(key=issue)

                    if int(j.github_key) not in destination.children:  # issue belongs to this epic in Jira but not ZenHub
                        z = ZenHubIssue(key=j.github_key, repo_name=destination.repo_name)
                        z.change_epic_membership(add=destination.github_key)

                    else:  # issue belongs to this epic in both Jira and ZenHub
                        dest_children.remove(int(j.github_key))  # remove it from the list so we can tell if any are left at the end

            for issue in dest_children:  # any issues left in this list do not belong to the epic in Jira,
                z = ZenHubIssue(key=issue, repo_name=destination.repo_name)  # so we remove them from the epic in ZenHub
                z.change_epic_membership(remove=destination.github_key)


if __name__ == '__main__':
    z = ZenHubIssue(key='7', repo_name='sync-test')
    j = JiraIssue(key='TEST-42')
    j.print()
    Sync.sync_from_specified_source(j, z)
    j = JiraIssue(key='TEST-42')
    j.print()



