import os,sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from gryd_worker import gryd_db_helper as db


class AutoCRMPGConnector(db.GrydPGConnector):
    def __init__(self, enterprise_id, *args, **kwargs):
        super().__init__(enterprise_id, *args, **kwargs)
    
    