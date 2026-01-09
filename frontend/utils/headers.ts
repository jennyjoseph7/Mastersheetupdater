// lib/api.ts

// Always use production URL
const getAppBaseUrl = () => {
  const url = "https://autobot-webapp-dev.gryd.in";
  console.log(`[APP_ENV] Using production URL -> ${url}`);
  return url;
};

const APP_BASE_URL = getAppBaseUrl();

// Helper: read cookie safely in browser
const getCookie = (name: string) => {
  if (typeof document === "undefined") return null;

  const match = document.cookie
    .split("; ")
    .find((row) => row.startsWith(name + "="));

  return match ? match.split("=")[1] : null;
};

// Read cookies (browser-safe)
let token = getCookie("gryd_token");
let sessionId = getCookie("gryd_session_id");
let applicationId = getCookie("gryd_application_id");

// Fallback (curl-tested credentials)
if (!token || !sessionId) {
  console.log("[Create Workshop API] Using fallback hardcoded credentials");
  token = "53014452-7df1-351c-9b79-af13d3d6b92f";
  sessionId = "94b970d4-5c2b-3762-bf65-272901d0ad53";
} else {
  console.log("[Create Workshop API] Using user credentials from cookies");
}

const HEADERS = {
  "Content-Type": "application/json",
  "X-GRYD-ENTERPRISE-ID": "autocrm",
  "X-GRYD-TOKEN": token,
  "X-GRYD-SESSION-ID": sessionId,
  "X-GRYD-APPLICATION-ID": applicationId || "autocrm",
  "X-GRYD-ROLE": "agent",
};

const FILE_UPLOAD_URL = "https://file-prod.gryd.in/media/document";

const FILE_UPLOAD_HEADERS = {
  "X-I2CE-ENTERPRISE-ID": "gryd_file_system",
  "X-I2CE-USER-ID": "abhishek+file-gryd@iamdave.ai",
  "X-I2CE-API-KEY": "4bd3fe53-02bf-3918-8e27-53095dd0e32b",
};

export {
  APP_BASE_URL,
  HEADERS,
  FILE_UPLOAD_URL,
  FILE_UPLOAD_HEADERS,
};
