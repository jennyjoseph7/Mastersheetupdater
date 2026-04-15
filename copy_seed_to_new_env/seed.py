import json
import sys,os
import time
from datetime import datetime, timedelta
from gryd_worker import gryd,gryd_db_helper as db_helper,gryd_helpers as hp
_root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)
from autocrm_db_helper import get_pg_connector

logger = gryd.hp.get_logger(__name__)

def read_sequence_json(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

def merge_models(default_models, user_models=None):
    if not user_models:
        return list(default_models) 

    final = list(default_models)

    for model in user_models:
        if model not in final:
            final.append(model)

    return final
   
def create_output_dir(model, created_at):
    logger.info(f"Creating output directory for {model}")
    dir_path = f"seed_data/{created_at}"
    hp.mkdir_p(dir_path)
    logger.info(f"Created output directory: {dir_path}")
    return dir_path

# def copy_to_seed(model, created_at, output_dir):

#     logger.info(f"Copying {model} to {output_dir}")
#     epoch_time = convert_date_to_epoch(created_at)

#     os.makedirs(output_dir, exist_ok=True)
#     file_path = os.path.join(output_dir, f"{model}.json")

#     query = f"""
#         COPY (
#             SELECT row_to_json(t)
#             FROM (
#                 SELECT *
#                 FROM {model}
#                 WHERE created >= to_timestamp({epoch_time})
#             ) t
#         ) TO STDOUT
#     """

#     rows = []

#     with get_pg_connector() as pg:
#         with pg.connection.cursor() as cur:
#             with cur.copy(query) as copy:
#                 for chunk in copy:
#                     line = bytes(chunk).decode().strip()
#                     if line:
#                         logger.info("line",line)
#                         obj = json.loads(line)      # 👈 convert string → dict
#                         rows.append(obj.get("dict")) 
#     if not rows:
#         logger.info(f"No data found for this model: {model} from the date: {created_at}:{epoch_time}")
#     with open(file_path, "w") as f:
#         json.dump(rows, f, indent=2)

#     logger.info(f"Exported to {file_path}")

def copy_to_seed(model, created_at, output_dir):
    logger.info(f"Copying {model} model to {output_dir} directory.")
    # logger.info(f"Created_at: {created_at}")
    epoch_time = convert_date_to_epoch(created_at)

    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, f"{model}.json")

    query = f"""
        SELECT dict
        FROM {model}
        WHERE created >= to_timestamp(%s)
    """

    rows = []
    count = 0

    with get_pg_connector() as pg:
        with pg.connection.cursor() as cur:
            cur.execute(query, (epoch_time,))
            for row in cur:
                # fetching each row
                # logger.info(f"row -->{row}")
                record = row[0]

                if record is None:
                    continue

                if isinstance(record, dict):
                    obj = record
                else:
                    try:
                        obj = json.loads(record)
                    except Exception:
                        logger.info("Skipping bad row")
                        continue

                rows.append(obj)
                count += 1

    with open(file_path, "w") as f:
        json.dump(rows, f, indent=4)

    logger.info(f"Exported {count} records to {file_path}")
    logger.info("--------------------------------------------------")

def convert_date_to_epoch(date_str):
    date_obj = time.strptime(date_str, '%Y-%m-%d')
    epoch_time = time.mktime(date_obj)
    
    return epoch_time

def get_models_and_copy_data_to_seed(user_models=[], created_at=None):
    """
    Fetches model data and copies it to the seed based on provided parameters.

    Parameters:
    ----------
    user_models : list, optional
        A list of additional model names to include.
        - If not provided, only the default model sequence list is used.
        - If provided, these models are appended to the default model list.

    created_at : str, optional
        The start date (in "YYYY-MM-DD" format) to filter data.
        - If not provided, defaults to a date 2 months prior to the current date.
        - If provided, overrides the default date.

    Behavior:
    --------
    1. If both `user_models` and `created_at` are not provided:
       - Uses default model sequence list.
       - Uses date = current date - 2 months.

    2. If only `user_models` is provided:
       - Uses default model sequence list + user-provided models.
       - Uses date = current date - 2 months.

    3. If only `created_at` is provided:
       - Uses default model sequence list.
       - Uses the provided `created_at` date.

    4. If both `user_models` and `created_at` are provided:
       - Uses default model sequence list + user-provided models.
       - Uses the provided `created_at` date.

    Returns:
    -------
    None
        Copies the filtered model data into the seed.
    """
    logger.info(f"User models: {user_models}")
    sequence_data = read_sequence_json('copy_seed_to_new_env/sequence.json')
    final_models = merge_models(sequence_data, user_models)
    if not created_at:
        today = datetime.today().date()
        created_at= str(today - timedelta(days=60))
        logger.info(f"By default created_at is 2 month ago date if user does not provide --{created_at}")
    
    epoch_time = convert_date_to_epoch(created_at)
    logger.info(f"Epoch time for {created_at}: {epoch_time}")
    for model in final_models:
        output_dir = create_output_dir(model, created_at)
        # logger.info(f"Copying {model} model to {output_dir} directory.")
        copy_to_seed(model,created_at,output_dir)


# NOTE: This function can be called in multiple ways this takes 2 parameters user_models (list) and created_at

# get_models_and_copy_data_to_seed() #if user_models and created_at are not provided then it will take default sequence list and 2 month ago date

# get_models_and_copy_data_to_seed(user_models=["session_test"]) #if user_models is provided and created_at are not provided then it will take default sequence list + user_models list and 2 month ago date

get_models_and_copy_data_to_seed(created_at="2026-03-01")