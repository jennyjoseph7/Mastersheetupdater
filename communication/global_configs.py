import os

def load_environment_config():
    return {
        "GRYD_COMMUNICATION_SERVICE": os.environ.get("GRYD_COMMUNICATION_SERVICE", "autocrm-communication"),
        "GRYD_COMMUNICATION_BROKER": os.environ.get("GRYD_COMMUNICATION_BROKER", "sqs"),
        "GRYD_COMMUNICATION_TIMEOUT": int(os.environ.get("GRYD_COMMUNICATION_TIMEOUT", "10")),
        "GRYD_COMMUNICATION_SHUTDOW_TIMEOUT": int(os.environ.get("GRYD_COMMUNICATION_SHUTDOW_TIMEOUT", "43200")),
        "CONVERS_SERVICE_NAME": os.environ.get("CONVERS_SERVICE_NAME", "conversation_dev"),
        "CONVERS_TASK_NAME": os.environ.get("CONVERS_TASK_NAME", "converse"),
        "GLOBAL_ENTERPRISES": os.environ.get("GLOBAL_ENTERPRISES", "test1,no_code_low_code"),        
    }