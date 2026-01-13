import { triggerGlobalLogout } from "@/lib/auth-context";

// 1. Centralized Base URL Logic (Environment Aware)
const getAppBaseUrl = () => {
  // Allow environment override if needed, otherwise default to prod
  if (process.env.NEXT_PUBLIC_API_BASE_URL) {
    return process.env.NEXT_PUBLIC_API_BASE_URL;
  }
  
  const url = "https://autobot-webapp-dev.gryd.in";
  console.log(`[APP_ENV] Using production URL -> ${url}`);
  return url;
};

export const APP_BASE_URL = getAppBaseUrl();

// 2. Types for the Header Helper
interface HeaderParams {
  token: string | null | undefined;
  sessionId: string | null | undefined;
  applicationId: string | null | undefined;
  role?: string; // Optional, defaults to "agent"
}

// 3. Reusable Header Generator (Works on Server & Client)
export const createApiHeaders = ({
  token,
  sessionId,
  applicationId,
  role = "agent", // Default role
}: HeaderParams) => {
  // CRITICAL FIX: Always use "autocrm", never "gryd"
  // logic moved here to be shared across the app
  const finalAppId = (!applicationId || applicationId === "gryd") 
    ? "autocrm" 
    : applicationId;

  return {
    "Content-Type": "application/json",
    Accept: "application/json",
    "X-GRYD-ENTERPRISE-ID": "autocrm",
    "X-GRYD-TOKEN": token || "",
    "X-GRYD-SESSION-ID": sessionId || "",
    "X-GRYD-APPLICATION-ID": finalAppId,
    "X-GRYD-ROLE": role,
  };
};

// ------------------------------------------------------------------
// CLIENT-SIDE SPECIFIC LOGIC (Legacy support for existing imports)
// ------------------------------------------------------------------

// Helper: read cookie safely in browser
const getCookie = (name: string) => {
  if (typeof document === "undefined") return null;
  const match = document.cookie.split("; ").find((row) => row.startsWith(name + "="));
  return match ? match.split("=")[1] : null;
};

// Read cookies (browser-safe)
const clientToken = getCookie("gryd_token");
const clientSessionId = getCookie("gryd_session_id");
const clientAppId = getCookie("gryd_application_id");

// Auto-Logout Logic (Client Side Only)
if (typeof document !== "undefined" && (!clientToken || !clientSessionId)) {
  console.warn("[API] Missing credentials in cookies. Triggering auto-logout...");
  triggerGlobalLogout();
}

// Export static HEADERS for existing client-side code
export const HEADERS = createApiHeaders({
  token: clientToken,
  sessionId: clientSessionId,
  applicationId: clientAppId,
  role: "agent"
});

export const FILE_UPLOAD_URL = "https://file-prod.gryd.in/media/document";

export const FILE_UPLOAD_HEADERS = {
  "X-I2CE-ENTERPRISE-ID": "gryd_file_system",
  "X-I2CE-USER-ID": "abhishek+file-gryd@iamdave.ai",
  "X-I2CE-API-KEY": "4bd3fe53-02bf-3918-8e27-53095dd0e32b",
};

// Wrapper to handle 401s on individual requests
export const authenticatedFetch = async (
  endpoint: string,
  options: RequestInit = {}
) => {
  const freshToken = getCookie("gryd_token") || clientToken;
  const freshSessionId = getCookie("gryd_session_id") || clientSessionId;

  // Use the shared helper to generate headers with fresh cookies
  const dynamicHeaders = {
    ...createApiHeaders({
      token: freshToken,
      sessionId: freshSessionId,
      applicationId: getCookie("gryd_application_id"),
      role: "agent"
    }),
    ...(options.headers || {}),
  };

  const url = endpoint.startsWith("http") ? endpoint : `${APP_BASE_URL}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers: dynamicHeaders as HeadersInit,
  });

  if (response.status === 401) {
    console.warn("[API] 401 Unauthorized detected. Triggering logout...");
    triggerGlobalLogout();
  }

  return response;
};