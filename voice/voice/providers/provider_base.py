"""Provider base interfaces."""

class ProviderBase:
    def create_call(self, *args, **kwargs):
        raise NotImplementedError

    def teardown(self):
        pass
