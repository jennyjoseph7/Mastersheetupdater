import os 
import sys 
_parent = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
if _parent not in sys.path:
    sys.path.insert(0, _parent)
import json
import re
from ai_service import ai_service_app
from cohorts_new.utils.utility import *
from cohorts_new.utils.common_utils import *
from collections import defaultdict

logger = get_logger(__name__)


class SessionStitcher(UtilityMixin):
    def __init__(self, source : list[dict]):
        self.sessions_by_user = defaultdict(list)
        final_source = []
        if isinstance(source, list):
            if all(isinstance(item, dict) for item in source):
                final_source = source
            elif all(isinstance(item, str) for item in source):
                for item in source:
                    loaded = self._load_json(item)
                    if isinstance(loaded, list):
                        final_source.extend(loaded)
                    elif isinstance(loaded, dict):
                        final_source.append(loaded)
                    else:
                        raise ValueError(f"Invalid JSON structure in: {item}")
            else:
                raise ValueError("source must be either list of dicts OR list of urls/paths")
        else:
            raise ValueError("source must be list of dict")
        self.source = final_source
        self.stitch_sessions()

    def stitch_sessions(self):
        for session in self.source:
            uid = session.get('uid')
            if uid:
                self.sessions_by_user[uid].append(session)
        sort_by_timestamp = lambda x : x.get('load_timestamp','')
        for uid in self.sessions_by_user:
            self.sessions_by_user[uid].sort(key=sort_by_timestamp, reverse=False)
        return dict(self.sessions_by_user)

    def get_user_stats(self, uid: str):
        sessions = self.sessions_by_user.get(uid)
        active_page_time_ms = [s.get('active_page_time_ms', 0) for s in sessions]
        total_page_time_ms = [s.get('total_page_time_ms', 0) for s in sessions]
        total_active_time = sum(active_page_time_ms)
        total_page_time = sum(total_page_time_ms)
        page_visited = list(set([s.get('path') for s in sessions]))
        return {
            "uid": uid,
            "total_sessions": len(sessions),
            "active_page_time_ms": total_active_time,
            "total_page_time_ms": total_page_time,
            "page_visited": page_visited
        }

    def get_user_summary(self, uid:str=None):
        if not uid:
            return self.get_all_user_summary()
        sessions = self.sessions_by_user.get(uid)
        if not sessions:
            return {}
        active_page_time_ms = [s.get('active_page_time_ms', 0) for s in sessions]
        total_page_time_ms = [s.get('total_page_time_ms', 0) for s in sessions]
        total_active_time = sum(active_page_time_ms)
        total_page_time = sum(total_page_time_ms)
        page_visited = list(set([s.get('path') for s in sessions]))
        return {
            "active_page_time_ms": total_active_time,
            "total_page_time_ms": total_page_time,
            "page_visited": page_visited,
            "sessions": sessions
        }
    
    def get_all_user_summary(self):
        return [self.get_user_summary(uid) for uid in self.sessions_by_user.keys()]


        

            

if __name__ == "__main__":
    u = SessionStitcher(
        source="/home/shreyasvaishnav/autobot_agents_branch_master/autobot_agents/cohorts_new/test_files/all_session_for_a_user.json"
    )

    uid = "c95d6a53-f72e-4530-9d77-1f66a075935c"
    print(json.dumps(u.get_user_summary(uid=uid), indent=4, default=str))