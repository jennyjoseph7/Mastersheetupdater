import os,sys
_root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)
import json

from gryd_worker import gryd_db_helper as db, gryd_helpers as hp
class AutoCRMPGConnector(db.GrydPGConnector):
    def __init__(self, enterprise_id, *args, **kwargs):
        super().__init__(enterprise_id, *args, **kwargs)
    
    def update(self, table_name, id_attr, id, data, additional = "", additional_values = None):
        return super().update(table_name, id, data, id_attr, additional, additional_values) 
    
    def get(self, table_name, id_attr, id):        
        return super().get(table_name, id, id_attr) 
    
    def list(self, table_name, where):
        return super().filter(table_name, where_clause)
    
    # TODO: add a limit .
    def list_order_by(self, table_name, where, order_by="created", order="DESC"):
        conditions = []
        where, values = db.dict_to_where_clause(where)
        order_clause = f"ORDER BY (dict->>'{order_by}') {order}"
        return super().list(table_name, f"{where} {order_clause}", values)
    
    def delete(self, table_name, id_attr, id):
        print("DELETE FROM {} WHERE {} = '{}'".format(table_name,id_attr,id))
        return super().execute_write("DELETE FROM {} WHERE {} = %s".format(table_name,id_attr), (id,), _fetch=False)
    
    def iadd(self, table_name, id_attr, id, attr, value):
        return super().iadd(table_name, id, attr, value, id_attr)
    
    def fetch_all(self, command, params=None, retries=2):
        if not self.is_connected:
            self.connect()

        with db.function_yielder(self, 'connection.cursor', retries) as cur:
            res = self._execute(cur, command, params, retries)

            if isinstance(res, int) and res:
                return self.fetch_all(command, params, res - 1)

            try:
                rows = cur.fetchall()
                return [hp.make_single(row) for row in rows]
            except Exception as e:
                print(f"Fetch all failed: {e}")
                return []
            finally:
                if db.AUTO_DISCONNECT:
                    self.close(do_sleep=False)
         
