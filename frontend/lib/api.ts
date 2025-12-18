export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "https://autobot-webapp-dev.gryd.in";

const DEFAULT_HEADERS = {
  "Content-Type": "application/json",
  Accept: "application/json",
  "X-GRYD-ENTERPRISE-ID": "autocrm",
  "X-GRYD-TOKEN": "53014452-7df1-351c-9b79-af13d3d6b92f",
  "X-GRYD-SESSION-ID": "94b970d4-5c2b-3762-bf65-272901d0ad53",
  "X-GRYD-ROLE": "agent",
};

export async function api(
  endpoint: string,
  method: string = "GET",
  body?: any,
  customHeaders: Record<string, string> = {}
) {
  const fullUrl = `${API_BASE_URL}${endpoint}`;

  // Merge headers - customHeaders override DEFAULT_HEADERS
  const headers: Record<string, string> = {
    ...DEFAULT_HEADERS,
    ...customHeaders,
  };

  // For GET requests without body, don't include Content-Type
  // Some servers reject GET requests with Content-Type header
  if (method === "GET" && !body) {
    delete headers["Content-Type"];
  }

  console.log(`[API] Making ${method} request to:`, fullUrl);
  console.log(`[API] Headers:`, headers);

  const fetchOptions: RequestInit = {
    method,
    headers,
    cache: "no-store",
    credentials: "omit", // Don't send cookies
    mode: "cors", // Explicitly set CORS mode
  };

  // Only add body if it exists
  if (body) {
    fetchOptions.body = JSON.stringify(body);
  }

  const res = await fetch(fullUrl, fetchOptions);

  console.log(`[API] Response status:`, res.status, `for`, fullUrl);
  console.log(
    `[API] Response headers:`,
    Object.fromEntries(res.headers.entries())
  );

  if (!res.ok) {
    const errorText = await res.text();
    console.error(`[API] Error response (${res.status}):`, errorText);

    // Provide more detailed error for 412
    if (res.status === 412) {
      throw new Error(
        `Precondition Failed (412): The server rejected the request. This might be due to missing headers or CORS issues. Error: ${errorText}`
      );
    }

    throw new Error(`API Error: ${res.status} ${errorText}`);
  }

  return res.json();
}

export async function fetchPersonObjects() {
  return api("/gryd/db/objects/person", "GET", undefined, {
    "X-GRYD-ROLE": "admin",
  });
}

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
    try {
      const errorText = await res.text();
      const errorData = JSON.parse(errorText);
      errorMessage =
        errorData?.error || errorData?.message || errorText || errorMessage;
    } catch {
      // Use default error message
    }

    errorMessage =
      errorMessage.replace(/^API Error:\s*\d*\s*/i, "").trim() || errorMessage;
    throw new ApiError(res.status, errorMessage);
  }

  return res.json();
}
