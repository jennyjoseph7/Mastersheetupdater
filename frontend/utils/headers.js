// utils/headers.js

// Backend Base URL
// NOTE: Ensure this port matches your Python backend (previous curls used 5000, this is 5008)
const APP_BASE_URL = 'http://127.0.0.1:5008'; 

const HEADERS = {
    'Content-Type': 'application/json',
    'X-GRYD-ENTERPRISE-ID': 'autocrm',
    'X-GRYD-TOKEN': '53014452-7df1-351c-9b79-af13d3d6b92f',
    'X-GRYD-SESSION-ID': '94b970d4-5c2b-3762-bf65-272901d0ad53',
    'X-GRYD-ROLE': 'agent'
};

// --- File Upload Service Config ---
const FILE_UPLOAD_URL = "https://file-prod.gryd.in/media/document";

// Note: Content-Type is NOT included here because FormData sets it automatically
const FILE_UPLOAD_HEADERS = {
    "X-I2CE-ENTERPRISE-ID": "gryd_file_system",
    "X-I2CE-USER-ID": "abhishek+file-gryd@iamdave.ai",
    "X-I2CE-API-KEY": "4bd3fe53-02bf-3918-8e27-53095dd0e32b",
};

export { APP_BASE_URL, HEADERS, FILE_UPLOAD_URL, FILE_UPLOAD_HEADERS };