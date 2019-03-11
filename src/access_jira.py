from jira import JiraIssue, JiraBoard
from github import GitHubIssue
import sys


def main():
    key = sys.argv[1]

    i = JiraIssue(key=key)

    print("Story number: %s" % i.jira_key)
    print("Status: %s" % i.status)
    print("Story points: %s" % i.story_points or None)
    print("Created: %s" % i.created)
    print("Updated: %s" % i.updated)
    print("Assignee: %s" % i.assignee)
    print("Description: %s" % i.description)
    print("Summary: %s" % i.summary)
    print("Repo: %s" % i.github_repo_name)
    print("Key: %s" % i.github_key)

    g = GitHubIssue(key=i.github_key, repo_name=i.github_repo_name)
    g.status = 'In Progress'
    i.update_from(g)
    print('new i status: ', i.status)
    i.update_remote()

    i = JiraIssue(key=key)  # refresh issue information
    print("After updating:")
    print("Story number: %s" % i.jira_key)
    print("Status: %s" % i.status)
    print("Story points: %s" % i.story_points or None)
    print("Created: %s" % i.created)
    print("Updated: %s" % i.updated)
    print("Assignee: %s" % i.assignee)
    print("Description: %s" % i.description)
    print("Summary: %s" % i.summary)


if __name__ == '__main__':
    main()

