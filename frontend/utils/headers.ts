"use client";

import { triggerGlobalLogout } from "@/lib/auth-context";

/* ---------------------------------------------------
   1. Cookie Helper (CLIENT SAFE)
--------------------------------------------------- */
const getCookie = (name: string): string | null => {
  if (typeof document === "undefined") return null;

  const match = document.cookie
    .split("; ")
    .find((row) => row.startsWith(name + "="));

  return match ? decodeURIComponent(match.split("=")[1]) : null;
};

/* ---------------------------------------------------
   2. Base URL (Environment Aware)
--------------------------------------------------- */
// const getAppBaseUrl = () => {
//   if (process.env.NEXT_PUBLIC_API_BASE_URL) {
//     return process.env.NEXT_PUBLIC_API_BASE_URL;
//   }

//   const url = "https://autobot-webapp-dev.gryd.in";
//   console.log(`[APP_ENV] Using production URL -> ${url}`);
//   return url;
// };
const getAppBaseUrl = () => {
  const url = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();

  if (!url) {
    throw new Error(
      "❌ NEXT_PUBLIC_API_BASE_URL is not defined. Please set it in your environment variables."
    );
  }

  console.log(`[APP_ENV] Using API URL -> ${url}`);
  return url;
};
export const APP_BASE_URL = getAppBaseUrl();

/* ---------------------------------------------------
   3. Header Types
--------------------------------------------------- */
interface HeaderParams {
  token: string | null;
  sessionId: string | null;
  applicationId: string | null;
  role?: string;
}

/* ---------------------------------------------------
   4. Centralized Header Generator
--------------------------------------------------- */
export const createApiHeaders = ({
  token,
  sessionId,
  applicationId,
  role = "agent",
}: HeaderParams) => {
  const finalAppId =
    !applicationId || applicationId === "gryd"
      ? "autocrm"
      : applicationId;

  return {
    "Content-Type": "application/json",
    Accept: "application/json",
    "X-GRYD-ENTERPRISE-ID": "autocrm",
    "X-GRYD-TOKEN": token ?? "",
    "X-GRYD-SESSION-ID": sessionId ?? "",
    "X-GRYD-APPLICATION-ID": finalAppId,
    "X-GRYD-ROLE": role,
  };
};

/* ---------------------------------------------------
   5. Client Header Getter (🔥 FIX)
   NEVER export static headers
--------------------------------------------------- */
export const getClientHeaders = () => {
  return createApiHeaders({
    token: getCookie("gryd_token"),
    sessionId: getCookie("gryd_session_id"),
    applicationId: getCookie("gryd_application_id"),
    role: "agent",
  });
};

/* ---------------------------------------------------
   6. File Upload Config (unchanged)
--------------------------------------------------- */
export const FILE_UPLOAD_URL =
  "https://file-prod.gryd.in/media/document";

export const FILE_UPLOAD_HEADERS = {
  "X-I2CE-ENTERPRISE-ID": "gryd_file_system",
  "X-I2CE-USER-ID": "abhishek+file-gryd@iamdave.ai",
  "X-I2CE-API-KEY": "4bd3fe53-02bf-3918-8e27-53095dd0e32b",
};

/* ---------------------------------------------------
   7. Authenticated Fetch (🔥 SAFE)
--------------------------------------------------- */
export const authenticatedFetch = async (
  endpoint: string,
  options: RequestInit = {}
) => {
  const token = getCookie("gryd_token");
  const sessionId = getCookie("gryd_session_id");
  const applicationId = getCookie("gryd_application_id");

  // 🚨 Session check ONLY here (not at import time)
  if (!token || !sessionId) {
    console.warn("[API] Missing credentials. Logging out...");
    triggerGlobalLogout();
    throw new Error("Session expired");
  }

  const headers = {
    ...createApiHeaders({
      token,
      sessionId,
      applicationId,
      role: "agent",
    }),
    ...(options.headers || {}),
  };

  const url = endpoint.startsWith("http")
    ? endpoint
    : `${APP_BASE_URL}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers: headers as HeadersInit,
  });

  if (response.status === 401) {
    console.warn("[API] 401 Unauthorized. Logging out...");
    triggerGlobalLogout();
  }

  return response;
};
