# sync-agile-boards
Synchronizes issues between Jira and ZenHub. It is designed to complement Unito.
Unito can only synchronize ZenHub information that is also stored in GitHub. _sync-agile-boards_
synchronizes the following attributes (which are not handled by Unito): 

* issue point values
* pipeline/status
* epic status and membership
* sprint (Jira) and milestone (ZenHub) membership 

Synchronizing sprint information depends on the existence of a sprint with identical names in both management
systems. The user needs to verify that a sprint found in the source management system exists in the destination
 management system with the identical name before invoking _sync-agile-boards_. Sprint synchronization is not mirrored. 
 That means, if the source management system contains a 
 sprint with name _sprint1_ but the destination management does not contain a sprint with that name, an issue 
 associated with a _sprint1_ will be processed but its sprint information will remain unchanged (a warning will
 be logged).  

It is assumed that Unito is being used to keep the other repository data synchronized: each issue should have
 information in the description added by Unito that links it to its match.

## Configuration

Token-based authorization is used to access the ZenHub, GitHub, and Jira APIs. Go to
* https://app.zenhub.com/dashboard/tokens to get the ZenHub token
* https://github.com/settings/tokens to get the GitHub token
* https://id.atlassian.com/manage/api-tokens to get the Jira token

The default location the code searches for the tokens are `~/.sync-agile-board-zenhub_config`, `~/.sync-agile-board-github_config`,
 and `~/.sync-agile-board-jira_config`, respectively. These locations are set in `settings.py`.
For ZenHub and GitHub only the API token is necessary.

### Jira authorization
The Jira config file must contain both username and token, in the format `you@email.com:your-token`, where `your-token` 
needs to be Base64-encoded. For instance, if your Jira API token is `your-token`, run in Python 3:
```python
import base64
my_auth = 'you@email.com:' + 'your-token'
encoded_token = base64.b64encode(my_auth.encode()).decode()
print(encoded_token)
   eW91QGVtYWlsLmNvbTp5b3VyLXRva2Vu
``` 
Write `encoded_token` to `~/.sync-agile-board-jira_config`.

## Set-up

_sync-agile-boards_ requires Python 3, `pip` and `virtualenv` installed. We tested it on Python 3.6 and 3.7. 
To install dependencies run the following in a terminal from the project root:
```bash
virtualenv --python=python3.6 .venv
source .venv/bin/activate
pip install -r requirements.txt
```
This installs a virtual environment that contains all requirements to run `sync_agile_boards.py`. To exit the virtual
environment execute `deactivate`.

## Mapping of pipeline labels

Pipelines can be semantically identical between the two management systems but they may use different labels. 
The following two tables show the correspondence between semantically identical labels for each system.

<table>
<tr><th>Table 1: Jira to ZenHub </th><th>Table 2: ZenHub to Jira </th></tr>
<tr><td>

|Jira | ZenHub|
|-----|-------|
| New Issue | New Issues |
| Icebox | Icebox |
| To Do | Backlog |
| In Progress | In Progress |
| In Review | Review/QA |
| Merged | Merged |
| Done | Done |
| Rejected | Closed |

</td><td>

| ZenHub | Jira | 
|--------|------|
| New Issues | New Issue |
| Backlog | To Do |
| Icebox | Icebox |
| In Progress | In Progress |
| Review/QA | In Review |
| Merged | Merged |
| Done | Done |
| Closed | Done |
| Epics | To Do |

</td></tr> </table> 


## Command Line Interface
The command line interface found in `sync_agile_boards.py` may be used in either of two modes. You may synchronize one repo at a 
time by entering repository information and options in the command line, or you may enter a configuration file containing information
to synchronize one or more repositories. The first argument sets which mode to use:

| First argument | Description |
|----------------|-------------|
| `repo`         | Synchronize one pair of repositories in the command line |
| `file`         | Synchronize one or more repository pairs from a configuration file | 

### Synchronize one pair of repositories in the command line
After the positional argument `repo` there are two required arguments that say 
where to find the repositories to synchronize. This is in the format
`<jira-organization>/<jira-repo-name> <zenhub-organization>/<zenhub-repo-name>`. For example:

```bash
ucsc-cgl/TEST ucsc-cgp/sync-test
```
Note that ZenHub may have additional
names for boards etc., but you should use the name that is shared between ZenHub and GitHub. The third argument is a
flag that says what the direction of synchronization is. Exactly one of these three flags is required:

| Flag | Description |
| ---- | ----------- |
| `-j` | Use Jira as the source. Synchronize all issues from Jira to ZenHub.|
| `-z` | Use ZenHub as the source. Synchronize all issues from ZenHub to Jira.|
| `-m` | Use the most current issue as the source. For each issue, synchronize based on updated timestamp.|

Next there is an optional filtering flag. This is helpful if you only want to sync certain issues.
`--open_only` may be especially helpful to reduce execution time if your closed issues are rarely updated or not important.  
Use up to one of the three options below:

| Flag | Description |
| ---- | ----------- |
| `-o, --open_only` | Only retrieve and synchronize issues that are open in ZenHub. This flag takes no argument.|
| `-zi, --zenhub_issues` | Only retrieve and synchronize this list of ZenHub issues e.g. '1, 3, 5'|
| `-jql, --jira-query-language` | Only retrieve and synchronize issues that match this Jira query e.g. assignee=you|

Note that these may be used in any combination with the synchronization direction flags. Finally there is an optional
verbose setting:

| Flag | Description |
| ---- | ----------- |
| `-v, --verbose` | Turn on verbose logging. Include all messages in the log file. |

This will include log messages for every time an issue is edited in Jira or ZenHub.

A complete example:

```bash
$ python sync_agile_boards.py repo ucsc-cgl/TEST ucsc-cgp/sync-test -j -o -v
```
This will get all issues that are open in the `ucsc-cgp` ZenHub repo `sync-test`, get their matching issues in Jira,
and synchronize their information from each Jira issue to each ZenHub issue, storing all messages in the log file.

#### Jira Query Language
Jira uses the same syntax, called Jira Query Language (JQL), for advanced searching in the UI and for API requests. 
Using the optional
-jql flag, you can add additional JQL filters, like assignee, or updated timestamp, to the request URL and only synchronize 
tickets that match. For example:
```bash
$ python sync_agile_boards.py repo test-org/TEST zen/zen-repo -z -jql assignee=you
```
will make a request using the URL `https://test-org.atlassian.net/rest/api/latest/search?jql=project=TEST AND assignee=you`
that will return all issues in the TEST repo that are assigned to 'you'. Jira queries should contain spaces separating
keywords like `AND` and `OR`. If your query that you enter after `-jql` contains spaces, it must be enclosed in double quotes.
Any quotes used withing the query must then be single quotes. If your query does not contain spaces, it must not be enclosed in quotes.

The complete documentation for Jira Query Language is here: https://confluence.atlassian.com/jirasoftwarecloud/advanced-searching-764478330.html
If you have difficulty getting a query to work, it is helpful to first make a query in the advanced search page in the UI,
which has autocomplete and help with syntax. You can then copy and paste into the command line.


### Synchronize one or more repository pairs from a configuration file
This mode is indicated using the positional argument `file`. For example:

```bash
python sync_agile_boards.py file config.txt
```
will iterate over the synchronization commands listed in `config.txt` and run them in order as if they were done in the command 
line sequentially.

#### Configuration file format
The configuration file is a plaintext file. Each line represents one sequence of command line arguments. For example:

```text
repo your-jira-org/your-jira-repo your-zenhub-org/your-zenhub-repo -j
repo another-jira-org/another-jira-repo another-zenhub-org/another-zenhub-repo -z
```
Each string is formatted exactly as if you entered it in the command line as described above.

## Tests

To run all tests activate the virtual environment as described in _Set-up_ above and execute
```bash
python -m unittest discover -s tests
```
from the project root.


