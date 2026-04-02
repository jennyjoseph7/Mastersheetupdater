

def yield_result(*args, **kwargs):
    pass

def yield_error(error_type, error_description, *args, **kwargs):
    yield {"status" : "error","error_type":error_type, "error_description":error_description,"session_id":kwargs.get("request_data",{}).get("session_id") or kwargs.get("session_id",""),"message_id" : kwargs.get("reply_to","")}


def yield_status(status_id, status_description, *args, **kwargs):
    yield {"status" : status_id,"message":status_description,"session_id":kwargs.get("request_data").get("session_id"),"message_id" : kwargs.get("reply_to")}

