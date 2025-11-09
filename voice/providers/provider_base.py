"""Provider base classes and interfaces."""


class ProviderBase:
    def create_call(self, *args, **kwargs):
        raise NotImplementedError
