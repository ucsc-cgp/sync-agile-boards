
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
            if source.children:  # This issue is an epic
                for issue in source.children:
                    # use ZenHub to get the key for corresponding Jira issue
                    z = ZenHubIssue(key=issue, repo_name=source.repo_name)
                    j = JiraIssue(key=z.jira_key)
                    if j.parent != source.jira_key:  # verify that each child issue also has this parent in Jira
                        j.add_to_epic(source.jira_key)

        elif source.__class__.__name__ == 'JiraIssue' and destination.__class__.__name__ == 'ZenHubIssue':
            print("from jira to zenhub")
            if source.parent:  # This issue belongs to an epic
                j = JiraIssue(key=source.parent)  # use Jira to get corresponding ZenHub parent issue
                z = ZenHubIssue(key=j.github_key, repo_name=j.github_repo_name)

                if z.is_epic is False:  # the issue is an epic in Jira but not yet in ZenHub
                    z._update_issue_to_epic()  # make it an epic in ZenHub

                if destination.github_key not in z.children:  # verify the ZenHub issue being updated belongs to the
                    destination.add_to_epic(z.github_key)  # correct epic in ZenHub


if __name__ == '__main__':
    j = JiraIssue(key='TEST-43')
    j.print()
    z = ZenHubIssue(key=j.github_key, repo_name=j.github_repo_name)
    z.print()
    Sync.sync_from_specified_source(j, z)
    print("After syncing: ")
    j.print()
    z.print()



