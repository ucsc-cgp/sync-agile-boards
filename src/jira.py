import datetime
import logging
from more_itertools import first
import re
import requests

from settings import transitions
from src.access import get_access_params
from src.issue import Repo, Issue
from src.utilities import CrypticNames, get_zenhub_pipeline

logger = logging.getLogger(__name__)


class JiraRepo(Repo):

    def __init__(self, repo_name, jira_org, jql: str = None):
        """Create a Project storing all issues belonging to the provided project key
        :param repo_name: Required. The repo to work with e.g. TEST
        :param jira_org: Required. The organization the repo belongs to, e.g. ucsc-cgl
        :param jql: Optional. If not specified, all issues in the repo will be retrieved. If specified, only will
        retrieve issues that match this Jira Query Language filter.
        """

        super().__init__()
        self.url = get_access_params('jira')['options']['server'] % jira_org
        self.alt_url = get_access_params('jira')['options']['alt_server'] % jira_org
        self.headers = {'Authorization': 'Basic ' + get_access_params('jira')['api_token']}

        self.name = repo_name
        self.org = jira_org
        self.issues = dict()

        if issues:
            for issue in issues:
                self.issues[issue] = JiraIssue(key=issue, repo=self)

        self.api_call(jql=jql)  # Get information for all issues in the project, filtered by jql if there is one

        # self.github_org, self.github_repo = board_map[jira_org][repo]

    def api_call(self, start=0, jql: str = None):
        """
        Make API calls until all results have been retrieved. Jira API responses can be paginated, defaulting to 50
        results per page, so a new call has to be made until the total is reached.

        :param start: The index in the results to start at. Always call this function with start=0
        :param jql: If specified, use this Jira query string to filter for certain issues within the repo
        """

        if jql:  # Add an 'AND' before the filter so it can be combined with the project filter
            jql_filter = f' AND {jql}'
        else:
            jql_filter = ''  # otherwise do not filter

        response = requests.get(f'{self.url}search?jql=project={self.name}{jql_filter}&startAt={str(start)}',
                                headers=self.headers).json()

        if 'issues' in response.keys():
            for issue in response['issues']:
                self.issues[issue['key']] = JiraIssue(content=issue, repo=self)

            if response['total'] >= start + response['maxResults']:  # There could be another page of results
                self.api_call(start=start + response['maxResults'], jql=jql)
        else:
            logging.info(f'No issues found matching this Jira query: {jql}')


class JiraIssue(Issue):

    # TODO break up this huge method
    def __init__(self, repo: 'JiraRepo', key: str = None, content: dict = None):
        """
        Create an Issue object from an issue key or from a portion of an API response

        :param repo: The JiraRepo object representing the repo this issue belongs to
        :param key: If specified, make an API call searching by this issue key
        :param content: If specified, don't make a new API call but use this response from an earlier one
        """

        super().__init__()

        self.repo = repo

        if key:
            response = requests.get(f'{self.repo.url}search?jql=id={key}', headers=self.repo.headers)

            if response.status_code == 200:
                json = response.json()
            else:
                raise ValueError(f'{response.status_code} Error: {response.text}')

            if 'issues' in json.keys():  # If the key doesn't match any issues, this will be an empty list
                content = json['issues'][0]  # Get the one and only issue in the response
            else:
                raise ValueError('No issue matching this id was found')

        if content['fields']['assignee']:
            self.assignees = [content['fields']['assignee']['name']]
        self.description = content['fields']['description']
        self.issue_type = content['fields']['issuetype']['name']
        self.jira_key = content['key']
        self.status = content['fields']['status']['name']

        self.summary = content['fields']['summary']

        # Convert the timestamps into datetime objects and localize them to PST time
        self.updated = datetime.datetime.strptime(content['fields']['updated'].split('.')[0],
                                                  '%Y-%m-%dT%H:%M:%S').replace(
            tzinfo=JiraIssue.get_utc_offset(content['fields']['updated']))

        # Not all issue descriptions have the corresponding github issue listed in them
        # self.github_repo, self.github_key = self.get_github_equivalent() or (None, None)
        self.get_github_equivalent()

        if CrypticNames.story_points in content['fields'].keys():
            self.story_points = content['fields'][CrypticNames.story_points]

        if CrypticNames.sprint in content['fields']:  # This custom field holds sprint information
            if content['fields'][CrypticNames.sprint]:
                # This field is a list containing a dictionary that's been put in string format.
                # Sprints can have duplicate names. id is the unique identifier used by the API.

                sprint_info = first(content['fields'][CrypticNames.sprint])

                match_obj = re.search(r'id=(\w*),', sprint_info)
                if match_obj:
                    self.jira_sprint_id = int(match_obj.group(1))
                    logger.info(f'No sprint ID was found in {CrypticNames.sprint}'
                                ' - trying different way to find sprint ID...')

        self.pipeline = get_zenhub_pipeline(self)  # This must be done after sprint status is set

    @staticmethod
    def get_utc_offset(timestamp):
        """Return a timezone object representing the UTC offset found in the timestamp"""
        offset_direction = timestamp[-5]  # A plus or minus sign
        offset_hours = int(timestamp[-4:-2])
        offset_minutes = int(timestamp[-2:])
        offset_seconds = offset_hours * 3600 + offset_minutes * 60
        return datetime.timezone(datetime.timedelta(seconds=int(offset_direction + str(offset_seconds))))

    def get_github_equivalent(self):
        """Find the equivalent Github issue key, repository name, milestone name and number if listed in the
        description field. Issues synchronized by Unito will have this information, but not all issue descriptions
        have the corresponding GitHub issue listed in them."""
        if self.description:
            match_obj1 = re.search(r'(?<=Repository Name: )(.*?)(?={color})', self.description)
            match_obj2 = re.search(r'(?<=Issue Number: )(.*?)(?={color})', self.description)
            match_obj3 = re.search(r'(?<=Milestone: )(.*?)(?={color})', self.description)
            match_obj4 = re.search(r'(?<=github.com/)(.*?)(?=/)', self.description)
            if not any([match_obj1, match_obj2, match_obj3, match_obj4]):
                print('No match was found in the description.')
            self.github_repo = match_obj1.group(0) if match_obj1 else None
            self.github_key = match_obj2.group(0) if match_obj2 else None
            self.github_milestone = match_obj3.group(0) if match_obj3 else None
            self.github_org = match_obj4.group(0) if match_obj4 else None

    def dict_format(self) -> dict:
        """Describe this issue in a dictionary that can be posted to Jira"""

        d = {
            'fields': {  # these fields can be updated
                'description': self.description,
                'issuetype': {'name': self.issue_type},
                'summary': self.summary
            }
        }

        if self.story_points:
            d['fields']['customfield_10014'] = self.story_points

        if self.assignees:
            d['fields']['assignee'] = {'name': self.assignees[0]}

        if self.jira_sprint_id:
            d['fields']['customfield_10010'] = self.jira_sprint_id

        return d

    def update_remote(self):
        """Update the remote issue. The issue must already exist in Jira."""

        transition = {'transition': {'id': transitions[self.status]}}

        # Issue status has to be updated as a transition
        r = requests.post(f'{self.repo.url}issue/{self.jira_key}/transitions',
                          headers=self.repo.headers, json=transition)

        if r.status_code != 204:  # HTTP 204 No Content on success
            logging.warning(f'{r.status_code} Error transitioning Jira status')

        # story points fields can be updated from a dictionary
        r = requests.put(f'{self.repo.url}issue/{self.jira_key}', headers=self.repo.headers,
                         json={'fields': {'customfield_10014': self.story_points}})

        if r.status_code != 204:  # HTTP 204 No Content on success
            logging.warning(f'{r.status_code} Error updating Jira: {r.text}')

    def post_new_issue(self):
        """Post this issue to Jira for the first time. The issue must not already exist."""

        r = requests.post(f'{self.repo.url}issue/', headers=self.repo.headers, json=self.dict_format())

        if r.status_code != 201:  # HTTP 201 means created
            print(f'{r.status_code} Error posting to Jira: {r.text}')

        self.jira_key = r.json()['key']  # keep the key that Jira assigned to this issue when creating it

    def change_epic_membership(self, add: str = None, remove: str = None):
        """Add or remove given issue from this epic (self). Specify one issue to add or remove as a kwarg"""

        if add and not remove:
            epic_name = self.jira_key
        elif remove and not add:
            epic_name = 'none'
        else:
            raise RuntimeError('change_epic_membership must be called with exactly one argument')

        issues = {'issues': [add or remove]}
        old_api_url = first(self.repo.url.split('api'))  # remove 'api/latest' from the url
        r = requests.post(f'{old_api_url}agile/1.0/epic/{epic_name}/issue', json=issues, headers=self.repo.headers)

        if r.status_code != 204:  # HTTP 204 on success
            print(f'{r.status_code} Error changing Jira epic membership: {r.text}')

    def get_epic_children(self):
        """If this issue is an epic, get all its children"""
        r = requests.get(f"{self.repo.url}search?jql=cf[10008]='{self.jira_key}'", headers=self.repo.headers)

        if r.status_code == 200:  # HTTP 200 OK
            children = [i['key'] for i in r.json()['issues']]
            return children
        else:
            print(f'{r.status_code} Error getting Jira epic children: {r.text}')

    def add_to_sprint(self):
        url = self.repo.alt_url + f'sprint/{self.jira_sprint_id}/issue'
        response = requests.post(url, headers=self.repo.headers, json={'issues': [self.jira_key]})
        if response.status_code != 204:  # HTTP 204 is OK
            logger.warning(f'{response.status_code}: '
                           f'Sync sprint: Error adding {self.jira_key} to '
                           f'sprint {self.jira_sprint_id}: {response.text}')

    def _get_sprint_id(self, sprint_title: str):
        base_url = self.repo.url
        url = base_url + f'search?jql=sprint="{sprint_title}"'
        response = requests.get(url, headers=self.repo.headers)
        if response.status_code == 200:
            data = response.json()['issues'][0]['fields']['customfield_10010']
            # The following attempts to extract the sprint ID from a string wrapped in a list, which contains one "["
            # character. It is very cryptic. Please see test in for Sync class for an example of "data".
            sprint_info = data[0].split('[')[1].split(',')
            self.jira_sprint_id = int(re.search('\d+', sprint_info[0]).group(0))
            logger.info(f'Sync sprint: Found sprint ID for sprint {sprint_title}')
        return response.status_code


if __name__ == '__main__':
    j = JiraRepo(repo_name='TEST', jira_org='ucsc-cgl', issues=['TEST-3'])
