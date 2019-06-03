
number_of_retries = 3  # Set the number of retries allowed when syncing in case the API rate limit is reached

urls = dict(  # GitHub base URL
    github_api='https://api.github.com/repos/'
)

url_mgmnt_sys = dict(  # Jira and ZenHub base URLs
    jira_alt_url='https://%s.atlassian.net/rest/agile/1.0/',  # alternative URL, e.g. to add issues to a sprint
    jira_url='https://%s.atlassian.net/rest/api/latest/',  # string format character included to be replaced with org
    zenhub_url='https://api.zenhub.io/p1/repositories/'
    )

token_path = dict(  # Locations of API token files
    api_token_jira='~/.sync-agile-board-jira_config',
    api_token_zenhub='~/.sync-agile-board-zenhub_config',
    api_token_github='~/.sync-agile-board-github_config'
    )

transitions = {  # Jira API uses these codes to identify status changes
    'To Do': 11,
    'In Progress': 21,
    'Done': 31,
    'In Review': 41,
    'Rejected': 51,
    'New Issue': 61,
    'Merged': 71,
    'Icebox': 81
}

jira_to_zen_backlog_map = {  # Maps Jira statuses to ZenHub pipelines for issues that are not in a sprint
        'New Issue': 'New Issues',
        'Icebox': 'Icebox',
        'To Do': 'Backlog',
        'In Progress': 'In Progress',
        'In Review': 'Review/QA',
        'Merged': 'Merged',
        'Done': 'Done',
        'Rejected': 'Closed'
    }

jira_to_zen_sprint_map = {  # Maps Jira statuses to ZenHub pipelines for issues that are in a sprint
        'New Issue': 'New Issues',
        'To Do': 'Backlog',
        'Icebox': 'Icebox',
        'In Progress': 'In Progress',
        'In Review': 'Review/QA',
        'Merged': 'Merged',
        'Done': 'Done',
        'Rejected': 'Closed'
    }

zen_to_jira_map = {  # Maps ZenHub pipelines to Jira statuses for all issues
        'New Issues': 'New Issue',
        'Backlog': 'To Do',
        'Icebox': 'Icebox',
        'In Progress': 'In Progress',
        'Review/QA': 'In Review',
        'Merged': 'Merged',
        'Done': 'Done',
        'Closed': 'Done',
        'Epics': 'To Do'
    }





