import os,sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import json
from gryd_worker import gryd_db_helper as db


class AutoCRMPGConnector(db.GrydPGConnector):
    def __init__(self, enterprise_id, *args, **kwargs):
        super().__init__(enterprise_id, *args, **kwargs)
    
    def update(self, table_name, id_attr, id, data, additional = "", additional_values = None):
        return super().update(table_name, id, data, id_attr, additional, additional_values) 
    
    def get(self, table_name, id_attr, id):        
        return super().get(table_name, id, id_attr) 
    
    # def list(self, table_name, where):
    #     where  = "WHERE dict @> '{}'".format(json.dumps(where))
    #     return super().list(table_name, where)
    
    def list(self, table_name, where):
        if isinstance(where, dict):
            where_clause = "WHERE dict @> '{}'".format(json.dumps(where))
        else:
            where_clause = f"WHERE {where}"

        return super().list(table_name, where_clause)
    def list_order_by(self, table_name, where, order_by="created", order="DESC"):
        where_clause = "WHERE dict @> '{}'".format(json.dumps(where))
        order_clause = f"ORDER BY (dict->>'{order_by}') {order}"
        return super().list(table_name, f"{where_clause} {order_clause}")
    
    def delete(self, table_name, id_attr, id):
        print("DELETE FROM {} WHERE {} = '{}'".format(table_name,id_attr,id))
        return super().execute_write("DELETE FROM {} WHERE {} = '{}'".format(table_name,id_attr,id))
    
    def iadd(self, table_name, id_attr, id, attr, value):
        return super().iadd(table_name, id, attr, value, id_attr)