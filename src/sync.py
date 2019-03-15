
class Sync:

    @staticmethod
    def sync_from_specified_source(source, destination):
        destination.update_from(source)
        destination.update_remote()

    @staticmethod
    def sync_from_most_current(a, b):

        if a.updated > b.updated:  # a is the most current
            b.update_from(a)
            b.update_remote()
        else:
            a.update_from(b)
            a.update_remote()


