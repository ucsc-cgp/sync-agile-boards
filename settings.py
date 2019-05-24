# TODO how to map orgs and repos between jira and zenhub?


org = {
    'DataBiosphere': ['azul'],
    'ucsc-cgp': ['sync-test']
}

urls = dict(
    github_api='https://api.github.com/repos/'
)

url_mgmnt_sys = dict(
    jira_alt_url='https://%s.atlassian.net/rest/agile/1.0/',  # alternative URL, e.g. to add issues to a sprint
    jira_url='https://%s.atlassian.net/rest/api/latest/',  # string format character included to be replaced with org
    zenhub_url='https://api.zenhub.io/p1/repositories/'
    )

token_path = dict(
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
    'Merged': 71
}

board_map = {
    'ucsc-cgp':  # ZenHub to Jira
        {'sync-test': 'ucsc-cgl'},
    'ucsc-cgl':  # Jira to ZenHub
        {'TEST': ('ucsc-cgp', 'sync-test')}
}


