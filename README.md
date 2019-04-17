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

## Return information from Jira

Create a virtual environment for Python 3 and activate it, install the requirements, and in a terminal run
```bash
python src/access_jira.py <story number>
```

This should return story number, status, story point value, timestamps of when created and last updated, and the total number of issues in the project.


## Tests

To run all tests execute
```bash
python -m unittest discover -s tests
```
from the project root.


