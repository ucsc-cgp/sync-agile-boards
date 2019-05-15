

class Issue:

    def __init__(self):

        self.assignees = None  # list[str]
        self.created = None  # datetime object

        self.description = None  # str
        self.github_key = None  # str, this identifier is used by ZenHub and github
        self.issue_type = None  # str, for Jira: Epic or Task or Story or Bug, for ZenHub: Epic or Issue
        self.jira_key = None  # str, this identifier is only used by jira
        self.jira_sprint = None  # str
        self.milestone = None  # int, github's equivalent of sprints?

        self.pipeline = None  # str, issue state in zenhub
        self.status = None  # str, issue state in jira
        self.story_points = None  # int
        self.summary = None  # str
        self.updated = None  # datetime object

        self.repo = None  # Repo object, the repo in which this issue lives

    def update_from(self, source: 'Issue'):
        """
        Set all fields in the sink issue (self) to match those in the source Issue object.
        Fields that are defined in self but are None in source will be left alone.
        """

        # Headers, url, and token are specific to the issue being in Jira or ZenHub.
        # Description and assignees are more complicated to sync.
        self.__dict__.update({k: v for k, v in source.__dict__.items() if v and k not in ['headers', 'url', 'token',
                                                                                          'description', 'assignees',
                                                                                          'repo']})

        # The ZenHub story point value cannot be set to None. If it's being updated from a Jira issue with no story
        # point value, set the story points to 0.
        if source.__class__.__name__ == 'JiraIssue' and source.story_points is None:
            self.story_points = 0

        if self.description and source.description:       # Both issues should have a description already
            self.description = Issue.merge_descriptions(source.description, self.description)
        elif source.__class__.__name__ == 'GitHubIssue':  # unless a ZenHubIssue is being updated from GitHub
            self.description = source.description
        else:                                             # Otherwise, something is wrong
            raise RuntimeError(f'Issue {self.jira_key} or {self.github_key} has no description')

    def fill_in_blanks_from(self, source: 'Issue'):
        # TODO is this used anywhere?
        """If a field in the sink issue (self) is blank, fill it with info from the source issue."""

        for attribute in source.__dict__.keys():
            if attribute not in ['headers', 'url', 'token', 'description']:  # ignore attributes specific to the source
                if self.__dict__[attribute] is None:
                    self.__dict__[attribute] = source.__dict__[attribute]  # fill in missing info

    @staticmethod
    def merge_descriptions(source: str, sink: str) -> str:
        """Merge issue descriptions by copying over description text without changing the sync info put in by Unito"""

        unito_link = [line for line in sink.split('\n') if line.startswith('┆')]  # lines added by unito start with ┆
        new_description = [line for line in source.split('\n') if not line.startswith('┆')]
        return '\n'.join(new_description) + '\n'.join(unito_link)

    def print(self):
        """Print out all fields for this issue. For testing purposes"""
        for attribute, value in self.__dict__.items():
            print(f'{attribute}: {value}')
        print('\n')


class Repo:

    def __init__(self):
        self.name = None
        self.org = None
        self.issues = None
        self.url = None
        self.headers = None
        self.id = None

    def api_call(self, action, url_tail: str, url_head: str = None, json: dict = None, page: int = '',
                 success_code: int = 200) -> dict:
        """Method to handle all API calls
        :param action: A requests method to call, e.g. requests.get or requests.post
        :param url_tail: The part of the url that is unique to this request. Appended to url_head.
        :param url_head: Defaults to self.repo.url, e.g. 'https://api.zenhub.io/p1/repositories/'. Can be set to
                         another value, like for using the old API version.
        :param json: The dictionary-formatted payload to send with the request.
        :param page: For paginated responses, the page/response number upon which to make the next call.
        :param success_code: The HTTP response code that should be returned on success. Defaults to 200; may need to be
                             set to 204 for some cases.
        """

        response = action(f'{url_head or self.url}{url_tail}{page}', headers=self.headers, json=json)
        print(self.headers)
        if response.status_code != success_code:
            raise RuntimeError(f'{response.status_code} Error: {response.text}')
        else:
            content = response.json()

        if page:  # Need to check if there is another page of results to get
            print(response.headers)
            if 'total' and 'maxResults' in content.keys():  # For Jira
                if content['total'] >= page + content['maxResults']:  # There could be another page of results
                    return content.update(self.api_call(action, url_tail, url_head=url_head, json=json,
                                                        page=page + content['maxResults'], success_code=success_code))
            elif 'rel="next"' in response.headers['Link']:  # For GitHub
                return content.update(self.api_call(action, url_tail, url_head=url_head, json=json, page=page + 1,
                                                    success_code=success_code))

        return content  # This is the last or only page
