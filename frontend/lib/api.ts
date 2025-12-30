// Determine API base URL - always use production unless explicitly overridden
const getApiBaseUrl = () => {
  // Check for explicit environment variable override
  if (process.env.NEXT_PUBLIC_API_BASE_URL) {
    return process.env.NEXT_PUBLIC_API_BASE_URL;
  }

  // Always use production URL
  return "https://autobot-webapp-dev.gryd.in";
};

export const API_BASE_URL = getApiBaseUrl();

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

export interface DealershipSignupRequest {
  args: [
    string, // dealership_name
    string // region
  ];
  kwargs: {
    aliases?: string[];
    pan_number?: string;
    gstin?: string;
    website?: string;
    vehicle_type?: string;
    dealership_type?: string;
    languages?: string[];
    brands?: string[];
    primary_contact_name?: string;
    primary_contact_email?: string;
    primary_contact_phone?: string;
    password?: string;
    confirm_password?: string;
    email_otp?: string;
    phone_number_otp?: string;
    email_otp_token?: string;
    phone_number_otp_token?: string;
  };
  _timeout?: number;
}

export async function generateOTP(contact: string, type: "whatsapp" | "email") {
  if (!contact) {
    throw new ApiError(400, "Contact (phone or email) is required");
  }

  if (!type || (type !== "whatsapp" && type !== "email")) {
    throw new ApiError(400, "Type must be 'whatsapp' or 'email'");
  }

  const backendUrl = `${API_BASE_URL}/gryd/api/autocrm-core/generate_otp`;
  const requestBody = {
    args: [contact, type],
  };

  console.log("[Generate OTP] Calling backend directly:", backendUrl);
  console.log(
    "[Generate OTP] Request body:",
    JSON.stringify(requestBody, null, 2)
  );

  const res = await fetch(backendUrl, {
    method: "POST",
    headers: DEFAULT_HEADERS,
    body: JSON.stringify(requestBody),
    cache: "no-store",
  });

  console.log(`[Generate OTP] Response status: ${res.status}`);
  console.log(
    `[Generate OTP] Response headers:`,
    Object.fromEntries(res.headers.entries())
  );

  // Check content-type to detect HTML responses
  const contentType = res.headers.get("content-type") || "";
  const isHTML = contentType.includes("text/html");

  if (!res.ok) {
    let errorMessage = `Request failed (${res.status})`;
    try {
      const errorText = await res.text();

      // If response is HTML, it's likely a CORS error or redirect
      if (
        isHTML ||
        errorText.trim().startsWith("<!DOCTYPE") ||
        errorText.trim().startsWith("<html")
      ) {
        console.error(
          "[Generate OTP] Received HTML response instead of JSON. This usually indicates:"
        );
        console.error("  1. CORS is not properly configured on the backend");
        console.error("  2. The endpoint is redirecting to an HTML page");
        console.error("  3. The endpoint doesn't exist (404 HTML page)");
        console.error("Response preview:", errorText.substring(0, 500));
        errorMessage = `Server returned HTML instead of JSON (Status: ${res.status}). This usually indicates a CORS issue or the endpoint doesn't exist. Check browser console for details.`;
      } else {
        // Try to parse as JSON
        try {
          const errorData = JSON.parse(errorText);
          errorMessage =
            errorData?.error || errorData?.message || errorText || errorMessage;
        } catch {
          // Not JSON, use text as is
          errorMessage = errorText || errorMessage;
        }
      }
    } catch (readError) {
      console.error("[Generate OTP] Failed to read error response:", readError);
    }

    errorMessage =
      errorMessage.replace(/^API Error:\s*\d*\s*/i, "").trim() || errorMessage;
    throw new ApiError(res.status, errorMessage);
  }

  // Check if successful response is also HTML (shouldn't happen, but handle it)
  // Clone the response to read it without consuming it
  const responseClone = res.clone();
  const responseText = await responseClone.text();

  if (
    isHTML ||
    responseText.trim().startsWith("<!DOCTYPE") ||
    responseText.trim().startsWith("<html")
  ) {
    console.error(
      "[Generate OTP] Received HTML response for successful request!"
    );
    console.error("Response status:", res.status);
    console.error("Response URL:", res.url);
    console.error(
      "Response headers:",
      Object.fromEntries(res.headers.entries())
    );
    console.error("Response preview:", responseText.substring(0, 1000));
    throw new ApiError(
      500,
      `Server returned HTML instead of JSON (Status: ${res.status}). This usually indicates:
1. CORS is not properly configured on the backend
2. The endpoint URL is incorrect: ${backendUrl}
3. The backend is redirecting to an HTML page
Check browser console and Network tab for more details.`
    );
  }

  // Try to parse as JSON
  let data;
  try {
    data = JSON.parse(responseText);
  } catch (parseError) {
    console.error("[Generate OTP] Failed to parse response as JSON");
    console.error("Response text:", responseText.substring(0, 500));
    throw new ApiError(
      500,
      `Server returned invalid JSON. Response preview: ${responseText.substring(
        0,
        200
      )}...`
    );
  }

  console.log("[Generate OTP] Response:", data);
  return data;
}

export async function dealershipSignup(data: DealershipSignupRequest) {
  const backendUrl = `${API_BASE_URL}/gryd/api/autocrm-core/dealership_signup`;

  console.log("[Dealership Signup] Calling backend directly:", backendUrl);
  console.log(
    "[Dealership Signup] Request body:",
    JSON.stringify(data, null, 2)
  );

  const res = await fetch(backendUrl, {
    method: "POST",
    headers: DEFAULT_HEADERS,
    body: JSON.stringify(data),
    cache: "no-store",
  });

  console.log(`[Dealership Signup] Response status: ${res.status}`);

  if (!res.ok) {
    let errorMessage = `Request failed (${res.status})`;
    let errorData: any = null;

    try {
      const contentType = res.headers.get("content-type");
      const errorText = await res.text();

      console.log(
        `[Dealership Signup] Error response content-type: ${contentType}`
      );
      console.log(
        `[Dealership Signup] Error response body: ${errorText.substring(
          0,
          500
        )}`
      );

      // Try to parse JSON error response
      if (errorText && errorText.trim()) {
        try {
          errorData = JSON.parse(errorText);

          // Extract error message from various possible formats
          if (errorData && typeof errorData === "object") {
            if (errorData.error) {
              errorMessage = String(errorData.error);
            } else if (errorData.message) {
              errorMessage = String(errorData.message);
            } else if (errorData.detail) {
              errorMessage = String(errorData.detail);
            } else {
              // If it's an object but no standard error field, try to extract useful info
              const errorStr = JSON.stringify(errorData);
              // Check if it contains the Python error message
              if (
                errorStr.includes("'NoneType' object has no attribute 'get'")
              ) {
                // This is a backend bug - try to extract the original error if available
                errorMessage =
                  "An error occurred while processing your request. Please check if the dealership already exists or try again.";
              } else {
                errorMessage = errorStr;
              }
            }
          } else if (typeof errorData === "string") {
            errorMessage = errorData;
          }
        } catch (parseError) {
          // Not JSON, use errorText as is
          console.log(
            `[Dealership Signup] Error response is not JSON, using raw text`
          );
          errorMessage = errorText || errorMessage;
        }
      }
    } catch (readError) {
      // Failed to read response, use default message
      console.error(
        "[Dealership Signup] Failed to read error response:",
        readError
      );
      errorMessage = `Request failed (${res.status})`;
    }

    // Clean up any "API Error:" prefixes
    errorMessage = errorMessage.replace(/^API Error:\s*\d*\s*/gi, "").trim();

    // Handle Python traceback errors - replace with user-friendly message
    if (errorMessage.includes("'NoneType' object has no attribute 'get'")) {
      errorMessage =
        "An error occurred while processing your request. The dealership may already exist or there was a server error. Please try again.";
    }

    // If message is empty after cleanup, use a default
    if (!errorMessage || errorMessage === "") {
      errorMessage = `Request failed (${res.status})`;
    }

    console.log(`[Dealership Signup] Returning error: ${errorMessage}`);
    throw new ApiError(res.status, errorMessage);
  }

  const responseData = await res.json();
  console.log("[Dealership Signup] Response:", responseData);
  return responseData;
}

export interface DealershipUpdateDetailsRequest {
  args: [string]; // dealership_id or dealership slug
  kwargs: {
    dealership_type?: string;
    languages?: string[];
    supported_brands?: string[];
    aliases?: string[];
    pan_number?: string;
    gstin?: string;
    website?: string;
  };
  _timeout?: number;
}

export async function dealershipUpdateDetails(
  data: DealershipUpdateDetailsRequest
) {
  const backendUrl = `${API_BASE_URL}/gryd/api/autocrm-core/dealership_update_details`;

  console.log(
    "[Dealership Update Details] Calling backend directly:",
    backendUrl
  );
  console.log(
    "[Dealership Update Details] Request body:",
    JSON.stringify(data, null, 2)
  );

  const res = await fetch(backendUrl, {
    method: "POST",
    headers: DEFAULT_HEADERS,
    body: JSON.stringify(data),
    cache: "no-store",
  });

  console.log(`[Dealership Update Details] Response status: ${res.status}`);

  if (!res.ok) {
    let errorMessage = `Request failed (${res.status})`;
    let errorData: any = null;
    try {
      const errorText = await res.text();
      console.log(
        `[Dealership Update Details] Error response text:`,
        errorText
      );
      try {
        errorData = JSON.parse(errorText);
        errorMessage =
          errorData?.error || errorData?.message || errorText || errorMessage;
        console.log(
          `[Dealership Update Details] Parsed error data:`,
          JSON.stringify(errorData, null, 2)
        );
      } catch {
        // Not JSON, use as is
        errorMessage = errorText || errorMessage;
      }
    } catch (readError) {
      console.error(
        "[Dealership Update Details] Failed to read error:",
        readError
      );
    }

    console.error(
      `[Dealership Update Details] Returning error response:`,
      errorMessage
    );
    errorMessage =
      errorMessage.replace(/^API Error:\s*\d*\s*/i, "").trim() || errorMessage;
    throw new ApiError(res.status, errorMessage);
  }

  const responseData = await res.json();
  console.log("[Dealership Update Details] Response:", responseData);
  return responseData;
}
