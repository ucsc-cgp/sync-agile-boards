from src.jira import JiraIssue
from src.github import GitHubIssue
from src.zenhub import ZenHubIssue
import sys


def main():
    """Print information about the specified Jira issue, get the corresponding GitHub issue, change its status to
    In Progress, update the remote Jira issue, and print its information after updating."""

    key = sys.argv[1]

    i = JiraIssue(key=key)

    print(f"Story number: {i.jira_key}")
    print(f"Summary: {i.summary}")
    print(f"Status: {i.status}")
    print(f"Story points: {i.story_points or None}")
    print(f"Created: {i.created}")
    print(f"Updated: {i.updated}")
    print(f"Assignee: {i.assignees}")
    print(f"Sprint: {i.jira_sprint}\n\n")

    z = ZenHubIssue(key=i.github_key, repo_name=i.github_repo_name)

    i.update_from(z)

    #  i.jira_sprint = 58

    i.update_remote()

    i = JiraIssue(key=key)  # refresh issue information
    print("After updating:")
    print(f"Story number: {i.jira_key}")
    print(f"Summary: {i.summary}")
    print(f"Status: {i.status}")
    print(f"Story points: {i.story_points or None}")
    print(f"Created: {i.created}")
    print(f"Updated: {i.updated}")
    print(f"Assignee: {i.assignees}")
    print(f"Sprint: {i.jira_sprint}\n\n")


if __name__ == '__main__':
    main()

