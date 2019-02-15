from jira import Jira, Issue, Project
import sys


def main():
    url = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    key = sys.argv[4]
    value = sys.argv[5]

    j = Jira(url, username, password)
    p = Project(j, key.split("-")[0])
    i = Issue(j, key)

    i.update_status(status=value)


if __name__ == '__main__':
    main()
