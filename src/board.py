
class Issue:

    def __init__(self):
        self.jira_key = None  # this identifier is only used by jira
        self.github_key = None  # this identifier is used by zenhub and github
        self.github_repo_name = None
        self.summary = None
        self.description = None
        self.created = None
        self.updated = None
        self.status = None
        self.issue_type = None
        self.story_points = None
        self.assignee = None

    def update_from(self, source):
        """
        Set all fields in this issue to match those in the source issue.
        Fields that are defined in this issue but None in the source will be left alone.

        :param source: an Issue object to source data from
        """

        for attribute in source.__dict__.keys():
            if attribute not in ['jira', 'github', 'zenhub', 'headers']:  # ignore the self attribute
                if source.__dict__[attribute] is not None:
                    self.__dict__[attribute] = self.__dict__[attribute]

    def fill_in_blanks_from(self, source):
        """
        If a field in this issue is blank, fill it with info from the source issue.
        :param source: an Issue object to source data from
        """
        for attribute in source.__dict__.keys():
            if attribute not in ['jira', 'github', 'zenhub', 'headers']:  # ignore the self attribute
                if self.__dict__[attribute] is None:
                    self.__dict__[attribute] = source.__dict__[attribute]  # fill in missing info
