
from src.jira import JiraIssue
from src.zenhub import ZenHubIssue


class Sync:

    @staticmethod
    def sync_from_specified_source(source: 'Issue', destination: 'Issue'):
        destination.update_from(source)
        destination.update_remote()

        # TODO This is a little weird because ZenHub issues don't know what epic they belong to. So updating a Jira epic
        #  from its info in ZenHub affects all child issues, not just the destination epic being updated.
        if source.__class__.__name__ == 'ZenHubIssue' and destination.__class__.__name__ == 'JiraIssue':
            if source.children:  # This issue is an epic
                for issue in source.children:
                    z = ZenHubIssue(key=issue, repo_name=source.repo_name)
                    j = JiraIssue(key=z.jira_key)
                    if j.parent != source.jira_key:  # verify that each child issue also has this parent in Jira
                        j.add_to_epic(source.jira_key)

        elif source.__class__.__name__ == 'JiraIssue' and destination.__class__.__name__ == 'ZenHubIssue':
            if source.parent:  # This issue belongs to an epic
                j = JiraIssue(key=source.parent)
                z = ZenHubIssue(key=j.github_key, repo_name=j.github_repo_name)
                if destination.github_key not in z.children:  # verify the ZenHub issue being updated belongs to the
                    destination.add_to_epic(z.github_key)  # correct epic in ZenHub

    @staticmethod
    def sync_from_most_current(a: 'Issue', b: 'Issue'):

        if a.updated > b.updated:  # a is the most current
            b.update_from(a)
            b.update_remote()
        else:
            a.update_from(b)
            a.update_remote()


