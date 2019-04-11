from src.jira import JiraIssue
from src.zenhub import ZenHubIssue
import sys


def main():
    """Print information about the specified Jira issue, get the corresponding GitHub issue, change its status to
    In Progress, update the remote Jira issue, and print its information after updating."""

    key = sys.argv[1]

    demo_issue = JiraIssue(key=key)

    print(f'Story number: {demo_issue.jira_key}')
    print(f'Summary: {demo_issue.summary}')
    print(f'Status: {demo_issue.status}')
    print(f'Story points: {demo_issue.story_points or None}')
    print(f'Created: {demo_issue.created}')
    print(f'Updated: {demo_issue.updated}')
    print(f'Assignee: {demo_issue.assignees}')
    print(f'Sprint: {demo_issue.jira_sprint}\n\n')

    z = ZenHubIssue(key=demo_issue.github_key, repo=demo_issue.github_repo, org='ucsc-cgp')

    demo_issue.update_from(z)

    demo_issue.update_remote()

    demo_issue = JiraIssue(key=key)  # refresh issue information
    print('After updating:')
    print(f'Story number: {demo_issue.jira_key}')
    print(f'Summary: {demo_issue.summary}')
    print(f'Status: {demo_issue.status}')
    print(f'Story points: {demo_issue.story_points or None}')
    print(f'Created: {demo_issue.created}')
    print(f'Updated: {demo_issue.updated}')
    print(f'Assignee: {demo_issue.assignees}')
    print(f'Sprint: {demo_issue.jira_sprint}\n\n')


if __name__ == '__main__':
    main()
