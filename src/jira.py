import datetime
import logging
from more_itertools import first
import re
import requests
from tqdm import tqdm

from settings import transitions
from src.access import get_access_params
from src.issue import Repo, Issue
from src.utilities import CustomFieldNames, get_zenhub_pipeline

logger = logging.getLogger(__name__)


class JiraRepo(Repo):

    def __init__(self, repo_name: str, jira_org: str, jql: str = None, empty: bool = False):
        """Create a Project storing all issues belonging to the provided project key
        :param repo_name: Required. The repo to work with e.g. TEST
        :param jira_org: Required. The organization the repo belongs to, e.g. ucsc-cgl
        :param jql: Optional. If not specified, all issues in the repo will be retrieved. If specified, only will
        retrieve issues that match this Jira Query Language filter
        :param empty: Optional. If true, initialize this repo without any issues
        """

        super().__init__()
        self.url = get_access_params('jira')['options']['server'] % jira_org
        self.alt_url = get_access_params('jira')['options']['alt_server'] % jira_org
        self.headers = {'Authorization': 'Basic ' + get_access_params('jira')['api_token']}

        self.name = repo_name
        self.org = jira_org

        if empty:
            return

        if jql:  # Add an 'AND' before the filter so it can be combined with the project filter
            jql_filter = f' AND {jql}'
        else:
            jql_filter = ''  # otherwise do not filter

        # By default, get all issues
        content = self.api_call(requests.get, f'search?jql=project={self.name}{jql_filter}&startAt=', page=0)
        for issue in tqdm(content['issues'], desc='getting Jira issues'):  # progress bar
            self.issues[issue['key']] = JiraIssue(content=issue, repo=self)


class JiraIssue(Issue):

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
            json = self.repo.api_call(requests.get, f'search?jql=id={key}')

            if 'issues' in json.keys():  # If the key doesn't match any issues, this will be an empty list
                content = json['issues'][0]  # Get the one and only issue in the response
            else:
                raise ValueError(f'No issue matching Jira ID {key} was found')

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

        if CustomFieldNames.story_points in content['fields'].keys():
            self.story_points = content['fields'][CustomFieldNames.story_points]

        if CustomFieldNames.sprint in content['fields']:  # This custom field holds sprint information
            if content['fields'][CustomFieldNames.sprint]:
                # This field is a list containing a dictionary that's been put in string format.
                # Sprints can have duplicate names. id is the unique identifier used by the API.

                sprint_info = first(content['fields'][CustomFieldNames.sprint])

                match_obj = re.search(r'id=(\w*),.*name=([\w-]*),', sprint_info)
                if match_obj:
                    self.sprint_id = int(match_obj.group(1))
                    self.sprint_name = match_obj.group(2)
                else:
                    logger.info(f'No sprint ID was found in {CustomFieldNames.sprint}'
                                ' - trying different way to find sprint ID...')

        self.pipeline = get_zenhub_pipeline(self)  # This must be done after sprint status is set

    @staticmethod
    def get_utc_offset(timestamp: str):
        """
        Return a timezone object representing the UTC offset found in the timestamp
        :param timestamp: a string with a timestamp in the format (+/-)HHMM at the end
        """
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
                logging.warning(f'No GitHub link information was found in the description of issue {self.jira_key}')
            self.github_repo = match_obj1.group(0) if match_obj1 else None
            self.github_key = match_obj2.group(0) if match_obj2 else None
            self.milestone_name = match_obj3.group(0) if match_obj3 else None
            self.github_org = match_obj4.group(0) if match_obj4 else None

    def update_remote(self):
        """Update the remote issue. The issue must already exist in Jira."""

        logger.debug(f'Updating Jira issue {self.jira_key} status to {self.status}')
        # Issue status has to be updated as a transition
        transition = {'transition': {'id': transitions[self.status]}}
        self.repo.api_call(requests.post, f'issue/{self.jira_key}/transitions', json=transition, success_code=204)

        logger.debug(f'Updating Jira issue {self.jira_key} story points to {self.story_points}')
        # Issue story points field can be updated from a dictionary
        try:
            self.repo.api_call(requests.put, f'issue/{self.jira_key}',
                               json={'fields': {CustomFieldNames.story_points: self.story_points}}, success_code=204)
        except RuntimeError as e:
            logger.warning(f'{repr(e)} error updating issue {self.jira_key} story points. '
                           f'Check that the issue is not a task')

    def change_epic_membership(self, add: str = None, remove: str = None):
        """Add or remove given issue from this epic (self). Specify one issue to add or remove as a kwarg"""

        if add and not remove:
            logger.debug(f'Adding Jira issue {add} to epic {self.jira_key}')
            epic_name = self.jira_key
        elif remove and not add:
            logger.debug(f'Removing Jira issue {remove} from epic {self.jira_key}')
            epic_name = 'none'
        else:
            raise RuntimeError('change_epic_membership must be called with exactly one argument')

        issues = {'issues': [add or remove]}
        self.repo.api_call(requests.post, url_head=first(self.repo.url.split('api')),
                           url_tail=f'agile/1.0/epic/{epic_name}/issue', json=issues, success_code=204)

    def get_epic_children(self) -> list:
        """If this issue is an epic, get all its children"""

        children = [i['key'] for i in self.repo.api_call(requests.get, f"search?jql=cf[10008]='{self.jira_key}'")['issues']]
        return children

    def add_to_sprint(self, sprint_id: str):
        """
        Post this issue to a sprint
        :param sprint_id: Jira ID of the sprint to add this issue to
        """
        logger.debug(f'Adding Jira issue {self.jira_key} to sprint {sprint_id}')
        self.repo.api_call(requests.post, f'sprint/{sprint_id}/issue', url_head=self.repo.alt_url,
                           json={'issues': [self.jira_key]}, success_code=204)

    def remove_from_sprint(self):
        """Remove this issue from any sprint it may be in"""

        logger.debug(f'Removing Jira issue {self.jira_key} from sprint {self.sprint_name}')
        self.sprint_name = None
        self.sprint_id = None
        self.repo.api_call(requests.put, f'issue/{self.jira_key}',
                           json={'fields': {CustomFieldNames.sprint: None}}, success_code=204)

    def get_sprint_id(self, sprint_title: str) -> int or None:
        """
        Search for a sprint ID by its name
        :param sprint_title: Jira sprint name to look up ID for
        """
        url = f'search?jql=sprint="{sprint_title}"'
        content = self.repo.api_call(requests.get, url)
        try:
            data = content['issues'][0]['fields']['customfield_10010']
            # The following attempts to extract the sprint ID from a string wrapped in a list, which contains one "["
            # character. It is very cryptic. Please see test in for Sync class for an example of "data".
            sprint_info = data[0].split('[')[1].split(',')
            jira_sprint_id = int(re.search(r'\d+', sprint_info[0]).group(0))
            logger.info(f'Sync sprint: Found sprint ID for sprint {sprint_title}')
        except KeyError:
            logger.warning(first(content['errorMessages']))
            jira_sprint_id = None

        return jira_sprint_id
