export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "https://autobot-webapp-dev.gryd.in";

interface ApiOptions {
  method?: string;
  headers?: Record<string, string>;
  body?: any;
}

export async function api(
  endpoint: string,
  method: string = "GET",
  body?: any,
  customHeaders: Record<string, string> = {}
) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
    "X-GRYD-ENTERPRISE-ID": "autocrm",
    "X-GRYD-TOKEN": "53014452-7df1-351c-9b79-af13d3d6b92f",
    "X-GRYD-SESSION-ID": "94b970d4-5c2b-3762-bf65-272901d0ad53",
    "X-GRYD-ROLE": "agent",
    ...customHeaders,
  };
  const res = await fetch(`${API_BASE_URL}${endpoint}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`API Error: ${res.status} ${errorText}`);
  }
  return res.json();
}

// Fetch person objects from the API
// or the the added audience for
export async function fetchPersonObjects() {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
    "X-GRYD-ENTERPRISE-ID": "autocrm",
    "X-GRYD-TOKEN": "53014452-7df1-351c-9b79-af13d3d6b92f",
    "X-GRYD-SESSION-ID": "94b970d4-5c2b-3762-bf65-272901d0ad53",
    "X-GRYD-ROLE": "admin",
  };

  const res = await fetch(`${API_BASE_URL}/gryd/db/objects/person`, {
    method: "GET",
    headers,
    cache: "no-store",
  });

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`API Error: ${res.status} ${errorText}`);
  }

  return res.json();
}

// Dealership signup API
export interface DealershipSignupRequest {
  args: [
    string, // dealership_name
    string, // region
    string, // vehicle_type
    string, // dealership_type
    string[], // languages
    string[], // brands
    string, // admin_name
    string, // email
    string // phone
  ];
  kwargs: {
    aliases?: string[];
    pan_number?: string;
    gstin?: string;
    website?: string;
  };
  _timeout?: number;
}

export class ApiError extends Error {
  status: number;
  error: any;

  constructor(status: number, message: string, error?: any) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.error = error;
  }
}

export async function dealershipSignup(data: DealershipSignupRequest) {
  // Use Next.js API route proxy to avoid CORS issues
  const res = await fetch("/api/dealership-signup", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(data),
    cache: "no-store",
  });

  if (!res.ok) {
    let errorMessage = `Request failed (${res.status})`;
    let errorData: any = null;

    try {
      const errorText = await res.text();
      try {
        errorData = JSON.parse(errorText);
        errorMessage =
          errorData.error || errorData.message || errorText || errorMessage;
      } catch {
        errorMessage = errorText || errorMessage;
      }
    } catch {
      errorMessage = `Failed to process request (${res.status})`;
    }

    // Clean up error message - remove any "API Error:" prefixes
    errorMessage = errorMessage.replace(/^API Error:\s*\d*\s*/i, "").trim();
    if (!errorMessage) {
      errorMessage = `Request failed (${res.status})`;
    }

    throw new ApiError(res.status, errorMessage, errorData);
  }

  return res.json();
}
