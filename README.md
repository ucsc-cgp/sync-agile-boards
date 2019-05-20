# sync-agile-boards
This is for sync testing

## Configuration

Use token-based authorization to access the ZenHub, GitHub, and Jira APIs. Go to
* https://app.zenhub.com/dashboard/tokens to get the ZenHub token
* https://github.com/settings/tokens to get the GitHub token
* https://id.atlassian.com/manage/api-tokens to get the Jira token

The default location the code searches for the tokens are `~/.sync-agile-board-zenhub_config`, `~/.sync-agile-board-github_config`, and `~/.sync-agile-board-jira_config`, respectively.
For ZenHub and GitHub only the API token is necessary.

### Jira authorization
The Jira config file must contain both, username and token, in the format `you@email.com:your-token`, where `your-token` 
needs to be Base64-encoded. For instance, if your Jira API token is `your-token`, run in Python 3:
```python
import base64
my_auth = 'you@email.com:' + 'your-token'
encoded_token = base64.b64encode(my_auth.encode()).decode()
print(encoded_token)
   eW91QGVtYWlsLmNvbTp5b3VyLXRva2Vu
``` 
Write `encoded_token` to `~/.sync-agile-board-jira_config`.

## Return information from ZenHub

Create a virtual environment for Python 3 and activate it, install the requirements, and in a terminal run

```bash
python src/zenhub.py $ORGNAME $REPONAME $STORYNUMBER | jq '.'
```

This should return the following output:
```bash
{
  "Story number": <some number>,
  "Repository": <some repo>,
  "Pipeline": <the pipeline name>,
  "Storypoints": <the story points>,
  "Timestamp": <the timestamp>
}
```

## Command Line Interface
The command line interface found in `sync_agile_boards.py` may be used in either of two ways. You may either sync one repo at a 
time by entering repo information and options in the command line, or you may enter a config file containing information
to sync one or more repos.

### Sync one pair of repos in the command line
This mode is indicated using the positional argument `repo`. For example:

```bash
python sync_agile_boards.py repo ucsc-cgl/TEST ucsc-cgp/sync-test -j
```
After `repo` there are two required arguments that say where to find the repos to sync. This is in the format
`<jira-organization>/<jira-repo-name> <zenhub-organization>/<zenhub-repo-name>`. Note that ZenHub may have additional
names for boards etc., but you should use the name that is shared between ZenHub and GitHub. The third argument is a
flag that says what the direction of synchronization is. Exactly one of these three flags is required:

| Flag | Description |
| ---- | ----------- |
| -j   | Use the Jira repo as the source. Make all ZenHub issues look like they do in Jira.|
| -z   | Use the ZenHub repo as the source. Make all Jira issues look like they do in ZenHub.|
| -m   | Use the most current issue as the source. For each issue, sync based on updated timestamp.|

Next there is an optional filtering flag. This is helpful if you only want to sync certain issues in the repos.
`--open_only` may be especially helpful to reduce execution time if your closed issues are rarely updated or not important.  
Use up to one of the three options below:

| Flag | Description |
| ---- | ----------- |
| -o, --open_only | Only retrieve and synchronize issues that are open in ZenHub. This flag takes no argument.|
| -zi, --zenhub_issues | Only retrieve and synchronize this list of ZenHub issues e.g. '1, 3, 5'|
| -jql, --jira-query-language | Only retrieve and synchronize issues that match this Jira query|

#### Jira Query Language
Jira uses the same syntax, called Jira Query Language (JQL), for advanced searching in the UI and for API requests. 
The repo name you enter in the command line is formatted as a JQL query and appended to the request URL. Using the optional
-jql flag, you can add additional filters, like assignee, or updated timestamp, to the request URL and only synchronize 
tickets that match. For example:
```bash
$ python sync_agile_boards.py test-org/TEST zen/zen-repo -z -jql assignee=you
```
will make a request using the URL `https://test-org.atlassian.net/rest/api/latest/search?jql=project=TEST AND assignee=you`
that will return all issues in the TEST repo that are assigned to 'you'. Jira queries may contain spaces separating
keywords like `AND` and `OR`. If your query that you enter after `-jql` contains spaces, it must be enclosed in double quotes.
Any quotes used withing the query must then be single quotes. If your query does not contain spaces, it must not be enclosed in quotes.

The complete documentation for Jira Query Language is here: https://confluence.atlassian.com/jirasoftwarecloud/advanced-searching-764478330.html
If you have difficulty getting a query to work, it is helpful to first make a query in the advanced search page in the UI,
which has autocomplete and help with syntax. You can then copy and paste into the command line.


### Sync one or more repo pairs from a config file
This mode is indicated using the positional argument `file`. For example:

```bash
python sync_agile_boards.py file config.json
```
will iterate over the sync commands listed in `config.json` and run them in order as if they were done in the command 
line sequentially.

#### Config file format
The config file must be in JSON format. It must consist of a dictionary with a top-level key named `sync_configs`. 
The value of `sync_configs` must be a list of strings that represent command line arguments. For example:

```json
{
  "sync_configs": [
    "your-jira-org/your-jira-repo your-zenhub-org/your-zenhub-repo -j",
    "another-jira-org/another-jira-repo another-zenhub-org/another-zenhub-repo -z"
  ]
}
```
Each string is formatted exactly as if you entered it in the command line as described above.

## Tests

To run all tests execute
```bash
python -m unittest discover -s tests
```
from the project root.


