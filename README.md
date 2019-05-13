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

## Demo

From the `src` directory, execute

```
python demo.py
```
to sync a repo.

## Tests

To run all tests execute
```bash
python -m unittest discover -s tests
```
from the project root.


