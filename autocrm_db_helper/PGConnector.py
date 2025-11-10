import os,sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import json
from gryd_worker import gryd_db_helper as db


class AutoCRMPGConnector(db.GrydPGConnector):
    def __init__(self, enterprise_id, *args, **kwargs):
        super().__init__(enterprise_id, *args, **kwargs)
    
    def update(self, table_name, id_attr, id, data, additional = "", additional_values = None):
        super().update(table_name, id, data, id_attr, additional, additional_values) 
    def get(self, table_name, id_attr, id):
        super().get(table_name, id, id_attr) 
    def list(self, table_name, where):
        where  = "WHERE dict @> '{}'".format(json.dumps(where))
        super().list(table_name, where)