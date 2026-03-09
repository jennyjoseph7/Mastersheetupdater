import requests
import json
from bp_utils import get_logger
import os
from dotenv import load_dotenv

load_dotenv()

base_url = os.getenv("GRYD_BASE_URL")
enterprise_id = os.getenv("GRYD_ENTERPRISE_ID")
token = os.getenv("GRYD_TOKEN")
session_id = os.getenv("GRYD_SESSION_ID")
role = os.getenv("GRYD_ROLE")

logger = get_logger(__name__)

def fetch_chunk_data_by_id(chunk_id):
    """
    Fetches the ACTUAL data from the Gryd DB API using the specific headers and params.
    """
    url = f"{base_url}/gryd/db/objects/chunk_saver"
    
    
    headers = {
        'Content-Type': 'application/json',
        'X-GRYD-ENTERPRISE-ID': enterprise_id,
        'X-GRYD-TOKEN': token,
        'X-GRYD-SESSION-ID': session_id,
        'Accept': 'application/json',
        'X-GRYD-ROLE': role
    }

   
    params = {
        "chunk_id": chunk_id 
    }
    
    

    try:
        logger.info(f"🌐 Fetching data for Chunk ID: {chunk_id} from API...")
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
         
            
            return data
        else:
            logger.error(f"❌ API Error: {response.status_code} - {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Network Error connecting to DB API: {e}")
        return None