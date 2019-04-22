from src.jira import JiraBoard, JiraIssue
from src.zenhub import ZenHubBoard, ZenHubIssue
import sys


def main():
    """Print information about the specified Jira issue, get the corresponding GitHub issue, change its status to
    In Progress, update the remote Jira issue, and print its information after updating."""

    key = sys.argv[1]
    demo_board = JiraBoard(repo='TEST', org='ucsc-cgl', issues=[key])
    demo_issue = demo_board.issues[key]

    print(f'Story number: {demo_issue.jira_key}')
    print(f'Summary: {demo_issue.summary}')
    print(f'Status: {demo_issue.status}')
    print(f'Story points: {demo_issue.story_points or None}')
    print(f'Created: {demo_issue.created}')
    print(f'Updated: {demo_issue.updated}')
    print(f'Assignee: {demo_issue.assignees}')
    print(f'Sprint: {demo_issue.jira_sprint}\n\n')

    z_board = ZenHubBoard(repo=demo_issue.github_repo, org='ucsc-cgp', issues=[demo_issue.github_key])
    z = z_board.issues[demo_issue.github_key]
    z.print()

    demo_issue.update_from(z)
    demo_issue.print()
    demo_issue.update_remote()

    demo_issue = JiraIssue(key=key, org='ucsc-cgl', board=demo_board)  # refresh issue information
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
