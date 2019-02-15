from jira import JiraIssue, JiraBoard
from github import GitHubIssue
import sys
import time


def main():
    key = sys.argv[1]

    print(key)
    i = JiraIssue(key=key)

    #p = JiraBoard(key.split("-")[0])

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
    #print("\nTotal issues in this project: %d" % len(p.issues))

    i.update_from(GitHubIssue(key=i.github_key, repo_name=i.github_repo_name))
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
