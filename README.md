# sync-agile-boards
This is for sync testing

## Return information from ZenHub

Create a virtual environment for Python 3 and activate it, install the requirements, and in a terminal run

```bash
python src/zenhub.py $PATH_TO_ZENHUB_TOKEN $REPONAME $STORYNUMBER | jq '.'
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
