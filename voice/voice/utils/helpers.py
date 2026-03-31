import uuid
from datetime import datetime
import json, sys, os
import base64
import audioop
import logging
from pydub import AudioSegment
from io import BytesIO
from datetime import datetime
import pytz
from urllib.parse import quote, unquote
import zlib
from fastapi import Request
from redis import Redis
import csv
import requests

redis_url = os.getenv("REDIS_URL", os.environ.get("REDIS_URL", "localhost"))
redis_port = int(os.getenv("REDIS_PORT", os.environ.get("REDIS_PORT", 6379)))


# ---- Logging ----
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)


TWILIO_DAVE_STATUS_MAP = {
    "failed": "error",
    "no-answer": "failed",
    "canceled": "failed",
    "busy": "failed",
    "queued": "queued",
    "initiated": "attempted",
    "ringing": "reached",
    "answered":"contacted",
    "in-progress": "contacted",
    "completed": "contacted"
}

TWILIO_DAVE_DISPOSITION_DETAILS = {
    "no-answer": "Not reachable",
    "canceled": "Rejected",
    "busy": "Didnt pickup",
    "failed": {
        "dnd":"DND", 
        "invalid":"Invalid / Doesn't exist",
        "other":"DND"
    }
}

TWILIO_ERROR_CODES = {
    "invalid":{
        21211: "Invalid 'To' Phone Number",
        21217: "Phone number does not appear to be valid",
        21401: "Invalid Phone Number",
        21421: "Phone Number is invalid",
        22102: "Invalid Phone Number (format or non-existent code)",
        18054: "Invalid phone number (format is incorrect or contains errors)",
        60006: "Invalid Phone Number (downstream provider says invalid)",
        80406: "Phone Number Did Invalid",
        13223: "Dial: Invalid phone number format (not E.164)",
        13224: "Dial: Twilio does not support calling this number or the number is invalid",
        60703: "Invalid phone numbers format (not E.164)"
    },

    "dnd": {
        30007: "Carrier Filtering (often used for DND, spam, or opt-out in many countries)",
        21610: "Message has been blocked by the user (STOP/opt-out)",
        21614: "'To' number is not a mobile number (e.g., landline, which may be DND in some regions)",
        21612: "'To' number is not SMS-capable (sometimes returned for DND)",
        801: "The end user is blocked (SMPP error, can be DND)",
        218: "Screening error. Terminating IMSI blocked (SMPP, can be DND)",
        928: "Blocked due to spam (SMPP, can be DND)"
    },
    "others": {
    }   
        
}

MIME_TYPES = {
    # 🧾 Document Formats
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "doc": "application/msword",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xls": "application/vnd.ms-excel",
    "csv": "text/csv",
    "pdf": "application/pdf",

    # 🧠 Data / API Formats
    "json": "application/json",
    "xml": "application/xml",
    "yaml": "application/x-yaml",

    # 🎧 Audio Formats
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "ogg": "audio/ogg",
    "aac": "audio/aac",
    "m4a": "audio/mp4",

    # 🎥 Video Formats
    "mp4": "video/mp4",
    "webm": "video/webm",
    "avi": "video/x-msvideo",
    "mov": "video/quicktime",
    "mkv": "video/x-matroska",
    "3gp": "video/3gpp",

    # 🖼️ Image Formats
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "bmp": "image/bmp",
    "svg": "image/svg+xml",
    "webp": "image/webp",
    "tiff": "image/tiff",

    # 🗂️ Other / Generic Types
    "txt": "text/plain",
    "html": "text/html",
    "bin": "application/octet-stream",
    "form": "multipart/form-data",
    "urlencoded": "application/x-www-form-urlencoded"
}


def generate_uuid() -> str:
    """Generate a unique message_id combining timestamp and UUID4."""
    uid = str(uuid.uuid4())
    return uid


def strip_data_uri(b64_str: str) -> str:
    """Remove possible data:...;base64, prefix."""
    if not b64_str:
        return b64_str
    if isinstance(b64_str, bytes):
        b64_str = b64_str.decode("utf-8")
    if b64_str.startswith("data:") and "," in b64_str:
        return b64_str.split(",", 1)[1]
    return b64_str


def mulaw_b64_to_pcm16k_b64(twilio_b64: str) -> str:
    return twilio_b64
    mulaw_bytes = base64.b64decode(twilio_b64)
    pcm_8k = audioop.ulaw2lin(mulaw_bytes, 2)  # 2 bytes/sample for 16-bit
    seg = AudioSegment.from_raw(BytesIO(pcm_8k), sample_width=2, frame_rate=8000, channels=1)
    seg = seg.set_frame_rate(16000)
    pcm_16k = seg.raw_data
    return base64.b64encode(pcm_16k).decode("utf-8")

def pcm16k_b64_to_mulaw_b64(pcm16k_b64: str) -> str:
    """
    Convert PCM16 (16kHz) base64 -> Twilio mu-law (8kHz) base64.
    """
    return pcm16k_b64
    pcm16k_b64 = _strip_data_uri(pcm16k_b64)
    pcm16k = base64.b64decode(pcm16k_b64)

    try:
        seg = AudioSegment.from_raw(BytesIO(pcm16k), sample_width=2, frame_rate=16000, channels=1)
        seg = seg.set_frame_rate(8000)
        pcm_8k = seg.raw_data
    except Exception as e:
        logger.exception("Downsampling failed: %s", e)
        raise

    try:
        mulaw = audioop.lin2ulaw(pcm_8k, 2)
    except Exception as e:
        logger.exception("PCM to μ-law conversion failed: %s", e)
        raise

    return base64.b64encode(mulaw).decode("utf-8")


def extract_audio_b64_from_dave(msg: dict) -> str:
    """
    Robustly extract base64 audio from various ElevenLabs message shapes.
    Possible locations:
      - msg['audio_event']['audio_base_64']
      - msg['audio']['chunk']
      - msg['audio']['audio_base_64']
    """
    if not isinstance(msg, dict):
        return None
    # audio_event
    ae = msg.get("audio_event")
    if isinstance(ae, dict) and ae.get("audio_base_64"):
        return ae.get("audio_base_64")

    audio = msg.get("audio")
    if isinstance(audio, dict):
        # prefer explicit names
        for k in ("audio_base_64", "audio_base64", "chunk", "data"):
            if audio.get(k):
                return audio.get(k)

    # fallback
    return None


def save_to_csv(data, base_path = "./stats/csv", filename=None, headers=None):
    """Save conversation messages to CSV."""
    os.makedirs(base_path, exist_ok=True)
    file_path = os.path.join(base_path, filename) if filename else None
    if filename is None:
        file_path = f"{base_path}/conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    headers = headers if headers else ["role", "content"] #"timestamp",

    with open(file_path, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)
    return file_path

def save_to_json(data, filename=None):
    """Save conversation messages to JSON."""
    base_path = "./stats/json"
    os.makedirs(base_path, exist_ok=True)
    file_path = os.path.join(base_path, filename) if filename else None
    if filename is None:
        file_path = f"{base_path}/conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(file_path, mode="w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)
    
    return file_path

def compress_string(text: str) -> str:
    compressed = zlib.compress(text.encode())
    b64 = base64.urlsafe_b64encode(compressed).decode()
    return quote(b64)

def decompress_string(compressed_text: str) -> str:
    decoded = unquote(compressed_text)
    decompressed = zlib.decompress(base64.urlsafe_b64decode(decoded))
    return decompressed.decode()

def datetime_now(tz = 'UTC'):
    return datetime.now(tz=pytz.timezone(tz)).strftime("%Y-%m-%d %I:%M:%S %p %z")

def save_audio_buffer_to_file(audio_data, file_path: str = None, ext: str = "mp3") -> str:
    """Save audio buffer (bytes or base64 str) to a local file. Returns the file path."""
    if file_path is None:
        file_path = f"/tmp/{uuid.uuid4()}.{ext}"
    
    if isinstance(audio_data, str):
        audio_data = base64.b64decode(audio_data)
    
    with open(file_path, "wb") as f:
        f.write(audio_data)
    
    logger.info(f"Audio saved to: {file_path}")
    return file_path

def func_gryd_file_system(local_path, **kwargs):
    url = f"https://file-prod.gryd.in/media/{kwargs.get('media_type','document')}"

    ext = os.path.splitext(local_path)[1].replace('.','').lower()
    content_type = MIME_TYPES[ext]

    logger.info(f'Local Path: {local_path}')
    logger.info(f'Content Type: {content_type}')

    files = [('file',(os.path.basename(local_path), open(local_path,'rb') ,content_type))]
    headers = {
    'X-I2CE-ENTERPRISE-ID': 'gryd_file_system',
    'X-I2CE-USER-ID': 'ananth+gryd_file_system@i2ce.in',
    'X-I2CE-API-KEY': '96aa6109-5128-32e6-94af-18fc74f77fba'
    }

    response = requests.request("POST", url, headers=headers, files=files)

    logger.info(f'Gryd File System Response: {response.text}')
    if response.status_code == 200:
        resp_json = response.json()
        return resp_json.get('cdn_url')
    return None

def upload_file(local_file_path, medium: str = 'func_gryd_file_system', **kwargs):
    if not hasattr(__import__(__name__), medium):
        return
    func = getattr(__import__(__name__), medium)
    if not callable(func):
        return
    
    return func(local_file_path, **kwargs)

class SessionStorage:
    def __init__(self, host = redis_url, port = redis_port, db = 0, expiry = 3600):
        self.session = Redis(host=host, port=port, db=db)
        self.expiry = expiry
        logger.info(f'Initialize Session Storage: {host}:{port}')
        return None
        
    def get(self, key, default = None):
        value = self.session.get(key).decode('utf-8')
        try:
            value = json.loads(value)
            if not isinstance(value, (dict, list, tuple)):
                value = str(value)
        except:
            pass

        #logger.info(f'Session Storage Get Key-Value:({key}, {value})')
        return value
    
    def set(self, key, value):
        self.session.set(key, value, self.expiry)
        #logger.info(f'Session Storage Set key-value: ({key}, {value})')
        return {key:value}
    
    def purge(self, key):
        logger.info(f'Purged Key {key}')

        self.session.delete(key)


if __name__ == "__main__":
    func_gryd_file_system("/home/nikit/dave_repo/voice-service/stats/csv/conversation_20251103_162521.csv")