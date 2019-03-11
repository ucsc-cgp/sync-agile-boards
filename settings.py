
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
    api_token_jira='~/.jira_config',
    api_token_zenhub='~/.zenhub_config',
    api_token_github='~/.github_config'
    )
