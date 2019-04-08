
class Issue:

    def __init__(self):
        # TODO can we get rid of any of these attributes? it seems like a lot
        self.url = None  # str
        self.headers = None  # dict[str, str]

        self.assignees = None  # list[str]
        self.created = None  # datetime object

        self.description = None  # str
        self.github_key = None  # str, this identifier is used by ZenHub and github
        self.github_repo_name = None  # str
        self.issue_type = None  # str, for Jira: Epic or Task or Story or Bug, for ZenHub: Epic or Issue
        self.jira_key = None  # str, this identifier is only used by jira
        self.jira_sprint = None  # str
        self.milestone = None  # int, github's equivalent of sprints?

        self.pipeline = None  # str, issue state in zenhub
        self.status = None  # str, issue state in jira
        self.story_points = None  # int
        self.summary = None  # str
        self.updated = None  # datetime object

        # TODO issues in the Jira API know if they're an epic, and what their parent epic is, if any. Issues in the
        #  ZenHub API only know if they're an epic or not. If so, another API call can be made to find all their
        #  children issues. These need to be coordinated somehow.
        self.parent = None  # str, the epic that this issue is a sub-task of
        self.children = None  # list[str], if this is an epic, lists issues belonging to it

    def update_from(self, source: 'Issue'):
        """
        Set all fields in the sink issue (self) to match those in the source Issue object.
        Fields that are defined in self but are None in source will be left alone.
        """
        # TODO should be able to update description while leaving issue link intact
        self.__dict__.update({k: v for k, v in source.__dict__.items() if v and k not in ['headers', 'url', 'token', 'description', 'assignees']})

    def fill_in_blanks_from(self, source: 'Issue'):
        """If a field in the sink issue (self) is blank, fill it with info from the source issue."""

        for attribute in source.__dict__.keys():
            if attribute not in ['headers', 'url', 'token', 'description']:  # ignore attributes specific to the source
                if self.__dict__[attribute] is None:
                    self.__dict__[attribute] = source.__dict__[attribute]  # fill in missing info

    def print(self):
        """Print out all fields for this issue. For testing purposes"""
        for attribute, value in self.__dict__.items():
            print(f'{attribute}: {value}')
        print('\n')


