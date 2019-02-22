# sync-agile-boards
This is for sync testing

## Configuration

Use token-based authorization to access both, the ZenHub and the 
Jira, APIs. Go to
* https://app.zenhub.com/dashboard/tokens to get the ZenHub token
* https://id.atlassian.com/manage/api-tokens to get the Jira token

The default location the code searches for the ZenHub token is `~/.zenhub_config` and
 or the Jira token it is `~/.jira_config`.
 

## Return information from ZenHub

Create a virtual environment for Python 3 and activate it, install the requirements, and in a terminal run

```bash
python src/zenhub.py $REPONAME $STORYNUMBER | jq '.'
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

## Tests

To run all tests execute
```bash
python -m unittest discover -s tests
```
from the project root.