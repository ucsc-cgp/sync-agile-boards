
org = {
    'DataBiosphere': ['azul'],
    'ucsc-cgp': ['sync-test']
}

default_orgs = dict(
    github='ucsc-cgp',
    jira='ucsc-cgl'
)

urls = dict(
    github_api='https://api.github.com/repos/'
)

url_mgmnt_sys = dict(
    jira_url='https://%s.atlassian.net/rest/api/latest/',  # string format character included to be replaced with repo
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

