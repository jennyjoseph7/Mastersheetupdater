from gryd_helper import gryd_db_helper as db


class AutoCRMPGConnector(db.GrydPGConnector):
    def __init__(self, enterprise_id, *args, **kwargs):
        super().__init__(enterprise_id, *args, **kwargs)
    
    