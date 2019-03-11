
class Issue:

    def __init__(self):
        self.url = None  # str
        self.token = None  # str
        self.headers = None  # dict[str, str]

        self.assignee = None  # str
        self.created = None  # datetime object
        self.description = None  # str
        self.github_key = None  # str, this identifier is used by zenhub and github
        self.github_repo_name = None  # str
        self.issue_type = None  # str
        self.jira_key = None  # str, this identifier is only used by jira
        self.parent = None  # str, the epic that this issue is a sub-task of
        self.status = None  # str
        self.story_points = None  # int
        self.summary = None  # str
        self.updated = None  # datetime object

    def update_from(self, source: 'Issue'):
        """
        Set all fields in the sink issue (self) to match those in the source Issue object.
        Fields that are defined in self but are None in source will be left alone.
        """

        for attribute in source.__dict__.keys():
            if attribute not in ['headers', 'url', 'token', 'description']:  # ignore attributes specific to the source
                if source.__dict__[attribute] is not None:
                    self.__dict__[attribute] = source.__dict__[attribute]

    def fill_in_blanks_from(self, source: 'Issue'):
        """If a field in the sink issue (self) is blank, fill it with info from the source issue."""

        for attribute in source.__dict__.keys():
            if attribute not in ['headers', 'url', 'token', 'description']:  # ignore attributes specific to the source
                if self.__dict__[attribute] is None:
                    self.__dict__[attribute] = source.__dict__[attribute]  # fill in missing info

