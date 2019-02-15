repo = dict(
    AZUL = 139095537
)

org = {
    'DataBiosphere': ['azul'],
    'ucsc-cgp': ['sync-test']
}

urls = dict(
    github_api='https://api.github.com/repos'
)

url_mgmnt_sys = dict(
    jira_url='https://ucsc-cgl.atlassian.net/rest/api/latest/',
    zenhub_url='https://api.zenhub.io/p1/repositories/',
    github_url="https://api.github.com/repos/ucsc-cgp/"
    )

token_path = dict(
    api_token_jira='~/.jira_config',
    api_token_zenhub='~/.zenhub_config',
    api_token_github='~/.github_config'
    )
