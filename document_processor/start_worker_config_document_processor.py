from gryd_worker import gryd, gryd_routes, gryd_helpers as hp, beats as cron_worker
from ai_service import ai_service_app
import os, sys, csv, re

AUTOCRM_DOCUMENT_PROCESSOR_PIPELINE_SERVICE_NAME = os.environ.get('AUTOCRM_DOCUMENT_PROCESSOR_PIPELINE_SERVICE_NAME', 'document-processor')
GRYD_FILE_USER_ID = os.environ.get("GRYD_FILE_USER_ID")
GRYD_FILE_API_KEY = os.environ.get("GRYD_FILE_API_KEY")
GRYD_FILE_SERVER_URL = os.environ.get("GRYD_FILE_SERVER_URL", "https://file-prod.gryd.in")
VLM_MODEL_IDENTIFIER = os.environ.get("VLM_MODEL_IDENTIFIER","gcp-gemini-3.1-flash-lite-preview")       


