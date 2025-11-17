"""Provider base interfaces."""

from typing import Optional, Callable, Dict, Any, List
import sys, os, json, requests

class ProviderBase:

    def __init__(self, *args, **kwargs):
        pass
    
    @classmethod
    def create_call(self, *args, **kwargs):
        raise NotImplementedError
    
    @classmethod
    def status_callback(self, callback:Optional[Callable] ):
        pass
