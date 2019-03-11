
class Issue:

    def __init__(self):
        self.url = None
        self.token = None
        self.headers = None

        self.assignee = None
        self.created = None
        self.description = None
        self.github_key = None  # this identifier is used by zenhub and github
        self.github_repo_name = None
        self.issue_type = None
        self.jira_key = None  # this identifier is only used by jira
        self.parent = None  # the epic that this issue is a sub-task of
        self.status = None
        self.story_points = None
        self.summary = None
        self.updated = None

    def update_from(self, source):
        """
        Set all fields in this issue to match those in the source issue.
        Fields that are defined in this issue but None in the source will be left alone.

        :param source: an Issue object to source data from
        """

        for attribute in source.__dict__.keys():
            # ignore the self attribute and attributes specific to the source
            if attribute not in ['jira', 'github', 'zenhub', 'headers', 'url', 'token', 'description']:
                if source.__dict__[attribute] is not None:
                    self.__dict__[attribute] = source.__dict__[attribute]

    def fill_in_blanks_from(self, source):
        """
        If a field in this issue is blank, fill it with info from the source issue.
        :param source: an Issue object to source data from
        """
        for attribute in source.__dict__.keys():
            # ignore the self attribute and attributes specific to the source
            if attribute not in ['jira', 'github', 'zenhub', 'headers', 'url', 'token', 'description']:
                if self.__dict__[attribute] is None:
                    self.__dict__[attribute] = source.__dict__[attribute]  # fill in missing info


class Board:

    def __init__(self):
        pass
