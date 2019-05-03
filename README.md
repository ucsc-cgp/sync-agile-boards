# sync-agile-boards
This is for sync testing

## Configuration

Use token-based authorization to access the ZenHub, GitHub, and Jira APIs. Go to
* https://app.zenhub.com/dashboard/tokens to get the ZenHub token
* https://github.com/settings/tokens to get the GitHub token
* https://id.atlassian.com/manage/api-tokens to get the Jira token

The default location the code searches for the tokens are `~/.zenhub_config`, `~/.github_config`, and `~/.jira_config`, respectively.
Note that the Jira config file must contain both username and token base 64 encoded in the format `you@gmail.com:your-token`. For ZenHub and GitHub only the unencoded token is necessary.

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

## Demo
To run the demo, edit demo.py to include your repo information:

```
jira_board = JiraRepo(repo_name='<your Jira repo>', org='<your Jira organization.', issues=[])
zen_board = ZenHubRepo(repo_name='<your GitHub repo', org='<your GitHub organization', issues=[])
```
If the `issues` list is empty, all issues in the repo will be synchronized. For demo purposes, you may want to specify
just a few issues to use, like this: `issues=['TEST-1', TEST-2']`. API calls will be made only for the issues you list,
making the demo run a lot faster.

Edit line 17 to indicate the desired synchronization direction: `Sync.sync_board(jira_board, zen_board)` will update the
ZenHub board look like the Jira board. Swap the arguments to sync the other way.

From the src directory, execute

```python demo.py```

This will print out information about all the issues and synchronize the repos.
## Tests

To run all tests execute
```bash
python -m unittest discover -s tests
```
from the project root.


