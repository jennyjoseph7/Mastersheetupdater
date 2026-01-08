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

// Helper function to get authentication headers from cookies
function getAuthHeaders(): Record<string, string> {
  if (typeof document === "undefined") {
    return {};
  }

  const getCookie = (name: string): string | null => {
    const nameEQ = name + "=";
    const ca = document.cookie.split(";");
    for (let i = 0; i < ca.length; i++) {
      let c = ca[i];
      while (c.charAt(0) === " ") c = c.substring(1, c.length);
      if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
    }
    return null;
  };

  const token = getCookie("gryd_token");
  const sessionId = getCookie("gryd_session_id");
  const applicationId = getCookie("gryd_application_id");

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
    "X-GRYD-ENTERPRISE-ID": "autocrm",
    "X-GRYD-APPLICATION-ID": applicationId || "autocrm",
  };

  if (token) {
    headers["X-GRYD-TOKEN"] = token;
  }
  if (sessionId) {
    headers["X-GRYD-SESSION-ID"] = sessionId;
  }
  headers["X-GRYD-ROLE"] = "agent";

  return headers;
}

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

  // Call backend directly to see full URL in network tab
  const backendUrl = `${API_BASE_URL}/generate_otp`;
  const requestBody = {
    args: [contact, type],
    kwargs: {},
  };

  console.log("[Generate OTP] Calling backend directly:", backendUrl);
  console.log("[Generate OTP] Contact:", contact);
  console.log("[Generate OTP] Type:", type);
  console.log(
    "[Generate OTP] Request body:",
    JSON.stringify(requestBody, null, 2)
  );

  const res = await fetch(backendUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-GRYD-ENTERPRISE-ID": "autocrm",
      "X-GRYD-SIGNUP-TOKEN": "YXV0b2NybTE3NjI2MTAzOTUgMjY0NTI0",
    },
    body: JSON.stringify(requestBody),
    cache: "no-store",
    mode: "cors",
    credentials: "omit",
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
2. The endpoint URL is incorrect
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
  // Call backend directly to avoid CloudFront blocking POST requests to API routes
  const backendUrl = `${API_BASE_URL}/dealership_signup`;

  console.log("[Dealership Signup] Calling backend directly:", backendUrl);
  console.log(
    "[Dealership Signup] Request body:",
    JSON.stringify(data, null, 2)
  );

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
    "X-GRYD-ENTERPRISE-ID": "autocrm",
    "X-GRYD-SIGNUP-TOKEN": "YXV0b2NybTE3NjI2MTAzOTUgMjY0NTI0",
  };

  const res = await fetch(backendUrl, {
    method: "POST",
    headers,
    body: JSON.stringify(data),
    cache: "no-store",
    mode: "cors",
    credentials: "omit",
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
    dealership_legal_name?: string;
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
  // Call backend directly to avoid CloudFront blocking POST requests to API routes
  const backendUrl = `${API_BASE_URL}/gryd/api/autocrm-core/dealership_update_details`;

  console.log(
    "[Dealership Update Details] Calling backend directly:",
    backendUrl
  );
  console.log(
    "[Dealership Update Details] Request body:",
    JSON.stringify(data, null, 2)
  );

  const headers = getAuthHeaders();
  if (!headers["X-GRYD-TOKEN"] || !headers["X-GRYD-SESSION-ID"]) {
    throw new ApiError(401, "Authentication required. Please login again.");
  }

  const res = await fetch(backendUrl, {
    method: "POST",
    headers,
    body: JSON.stringify(data),
    cache: "no-store",
    mode: "cors",
    credentials: "omit",
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

export interface DealerLoginRequest {
  email: string;
  password: string;
}

export interface DealerLoginResponse {
  role: string;
  token: string;
  expiry: number;
  user_id: string;
  enterprise_id: string;
  application_id: string;
  session_id: string;
}

export async function dealerLogin(
  data: DealerLoginRequest
): Promise<DealerLoginResponse> {
  // Use production API for dealer login
  const loginApiUrl = "https://autobot-webapp-dev.gryd.in/gryd/login";

  // Transform the request to match API requirements
  const requestBody = {
    user_id: data.email,
    password: data.password,
    role: "human_agent",
    attribute: "email",
    application_id: "autocrm",
  };

  console.log("[Dealer Login] Calling login API:", loginApiUrl);
  console.log(
    "[Dealer Login] Request body:",
    JSON.stringify(requestBody, null, 2)
  );

  const res = await fetch(loginApiUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      "X-GRYD-ENTERPRISE-ID": "autocrm",
      "X-GRYD-SIGNUP-TOKEN": "YXV0b2NybTE3NjI2MTAzOTUgMjY0NTI0",
    },
    body: JSON.stringify(requestBody),
    cache: "no-store",
  });

  console.log(`[Dealer Login] Response status: ${res.status}`);

  if (!res.ok) {
    let errorMessage = `Login failed (${res.status})`;
    try {
      const errorText = await res.text();
      console.log(`[Dealer Login] Error response text:`, errorText);
      try {
        const errorData = JSON.parse(errorText);
        errorMessage =
          errorData?.error || errorData?.message || errorText || errorMessage;
      } catch {
        // Not JSON, use as is
        errorMessage = errorText || errorMessage;
      }
    } catch (readError) {
      console.error("[Dealer Login] Failed to read error:", readError);
    }

    errorMessage =
      errorMessage.replace(/^API Error:\s*\d*\s*/i, "").trim() || errorMessage;
    throw new ApiError(res.status, errorMessage);
  }

  const responseData = await res.json();
  console.log("[Dealer Login] Response:", responseData);
  return responseData;
}

export interface DealershipDetailsResponse {
  [key: string]: any; // Dealership data structure may vary
}

// Helper function to get cookie (for use in non-client contexts)
function getCookieFromDocument(name: string): string | null {
  if (typeof document === "undefined") return null;
  const nameEQ = name + "=";
  const ca = document.cookie.split(";");
  for (let i = 0; i < ca.length; i++) {
    let c = ca[i];
    while (c.charAt(0) === " ") c = c.substring(1, c.length);
    if (c.indexOf(nameEQ) === 0) {
      const value = c.substring(nameEQ.length, c.length);
      // Decode URI component in case cookie was encoded
      try {
        return decodeURIComponent(value);
      } catch {
        return value;
      }
    }
  }
  return null;
}

export async function getDealershipDetails(): Promise<DealershipDetailsResponse> {
  // Get token, session_id, and user_id from cookies
  const token = getCookieFromDocument("gryd_token");
  const sessionId = getCookieFromDocument("gryd_session_id");
  const userId = getCookieFromDocument("gryd_user_id");

  if (!token || !sessionId || !userId) {
    throw new ApiError(401, "Authentication required. Please login again.");
  }

  // Call backend directly to avoid CloudFront blocking GET requests to API routes
  const backendUrl = `${API_BASE_URL}/get-dealership-details/${userId}`;

  console.log("[Get Dealership Details] Calling backend directly:", backendUrl);
  console.log("[Get Dealership Details] Using user_id:", userId);

  const headers = getAuthHeaders();
  if (!headers["X-GRYD-TOKEN"] || !headers["X-GRYD-SESSION-ID"]) {
    throw new ApiError(401, "Authentication required. Please login again.");
  }

  const res = await fetch(backendUrl, {
    method: "GET",
    headers: {
      Accept: "application/json",
      "X-GRYD-ENTERPRISE-ID": "autocrm",
      "X-GRYD-TOKEN": headers["X-GRYD-TOKEN"],
      "X-GRYD-SESSION-ID": headers["X-GRYD-SESSION-ID"],
      "X-GRYD-APPLICATION-ID": headers["X-GRYD-APPLICATION-ID"],
    },
    cache: "no-store",
    mode: "cors",
    credentials: "omit",
  });

  console.log(`[Get Dealership Details] Response status: ${res.status}`);

  if (!res.ok) {
    let errorMessage = `Failed to fetch dealership details (${res.status})`;
    try {
      const errorText = await res.text();
      console.error(`[Get Dealership Details] Error response text:`, errorText);
      try {
        const errorData = JSON.parse(errorText);
        errorMessage =
          errorData?.error || errorData?.message || errorText || errorMessage;
      } catch {
        // Not JSON, use as is
        errorMessage = errorText || errorMessage;
      }
    } catch (readError) {
      console.error(
        "[Get Dealership Details] Failed to read error:",
        readError
      );
    }

    errorMessage =
      errorMessage.replace(/^API Error:\s*\d*\s*/i, "").trim() || errorMessage;
    throw new ApiError(res.status, errorMessage);
  }

  const responseData = await res.json();
  console.log("[Get Dealership Details] Response:", responseData);
  return responseData;
}

export interface CreateWorkshopRequest {
  dealer_name: string;
  dealership_id: string;
  workshop_name: string;
  workshop_type: string;
  workshop_status?: string;
  email: string;
  contact_number: string;
  manager_name: string;
  address: string;
  city: string;
  state: string;
  pincode: string;
  region_id?: string;
  region_name?: string;
  geolocation: [number, number]; // [latitude, longitude]
  operating_hours: {
    opening_time: string;
    closing_time: string;
    days_open: string[];
  };
  supported_brands: string[];
  services_offered: string[];
  total_technicians: number;
  total_service_bays: number;
  daily_service_capacity: number;
}

export async function createWorkshop(
  data: CreateWorkshopRequest
): Promise<any> {
  // Call backend directly to avoid CloudFront blocking POST requests to API routes
  const backendUrl = `${API_BASE_URL}/gryd/db/object/workshop`;

  console.log("[Create Workshop] Calling backend directly:", backendUrl);
  console.log("[Create Workshop] Request body:", JSON.stringify(data, null, 2));

  const headers = getAuthHeaders();
  if (!headers["X-GRYD-TOKEN"] || !headers["X-GRYD-SESSION-ID"]) {
    throw new ApiError(401, "Authentication required. Please login again.");
  }

  const res = await fetch(backendUrl, {
    method: "POST",
    headers,
    body: JSON.stringify(data),
    cache: "no-store",
    mode: "cors",
    credentials: "omit",
  });

  console.log(`[Create Workshop] Response status: ${res.status}`);

  if (!res.ok) {
    let errorMessage = `Failed to create workshop (${res.status})`;
    try {
      const errorText = await res.text();
      console.error(`[Create Workshop] Error response text:`, errorText);
      try {
        const errorData = JSON.parse(errorText);
        errorMessage =
          errorData?.error || errorData?.message || errorText || errorMessage;
      } catch {
        // Not JSON, use as is
        errorMessage = errorText || errorMessage;
      }
    } catch (readError) {
      console.error("[Create Workshop] Failed to read error:", readError);
    }

    errorMessage =
      errorMessage.replace(/^API Error:\s*\d*\s*/i, "").trim() || errorMessage;
    throw new ApiError(res.status, errorMessage);
  }

  const responseData = await res.json();
  console.log("[Create Workshop] Response:", responseData);
  return responseData;
}

export async function getWorkshopsForDealership(
  dealershipId: string
): Promise<any[]> {
  // Call backend directly to avoid CloudFront blocking GET requests to API routes
  const backendUrl = `${API_BASE_URL}/gryd/db/objects/workshop?dealership_id=${encodeURIComponent(
    dealershipId
  )}`;

  console.log("[Get Workshops] Calling backend directly:", backendUrl);

  const headers = getAuthHeaders();
  if (!headers["X-GRYD-TOKEN"] || !headers["X-GRYD-SESSION-ID"]) {
    throw new ApiError(401, "Authentication required. Please login again.");
  }

  const res = await fetch(backendUrl, {
    method: "GET",
    headers: {
      Accept: "application/json",
      "X-GRYD-ENTERPRISE-ID": "autocrm",
      "X-GRYD-TOKEN": headers["X-GRYD-TOKEN"],
      "X-GRYD-SESSION-ID": headers["X-GRYD-SESSION-ID"],
      "X-GRYD-ROLE": "agent",
      "X-GRYD-APPLICATION-ID": headers["X-GRYD-APPLICATION-ID"],
    },
    cache: "no-store",
    mode: "cors",
    credentials: "omit",
  });

  console.log(`[Get Workshops] Response status: ${res.status}`);

  if (!res.ok) {
    // If 404, return empty array (no workshops found)
    if (res.status === 404) {
      return [];
    }
    let errorMessage = `Failed to fetch workshops (${res.status})`;
    try {
      const errorText = await res.text();
      console.error(`[Get Workshops] Error response text:`, errorText);
      try {
        const errorData = JSON.parse(errorText);
        errorMessage =
          errorData?.error || errorData?.message || errorText || errorMessage;
      } catch {
        errorMessage = errorText || errorMessage;
      }
    } catch (readError) {
      console.error("[Get Workshops] Failed to read error:", readError);
    }

    errorMessage =
      errorMessage.replace(/^API Error:\s*\d*\s*/i, "").trim() || errorMessage;
    throw new ApiError(res.status, errorMessage);
  }

  const responseData = await res.json();
  console.log("[Get Workshops] Response:", responseData);

  // Handle both array and object responses
  if (Array.isArray(responseData)) {
    return responseData;
  } else if (responseData && Array.isArray(responseData.data)) {
    return responseData.data;
  } else if (responseData && Array.isArray(responseData.workshops)) {
    return responseData.workshops;
  }

  return [];
}

// Showroom interfaces and functions
export interface CreateShowroomRequest {
  showroom_id: string;
  showroom_name: string;
  showroom_full_name: string;
  showroom_type: string;
  showroom_status: string;
  dealership_id: string;
  dealership_name: string;
  manager_name: string;
  email: string;
  contact_number: string;
  address: string;
  city: string;
  state: string;
  pincode: string;
  region_name?: string;
  geolocation: [number, number];
  operating_hours: {
    opening_time: string;
    closing_time: string;
  };
  days_open: string[];
  supported_brands: string[];
  parking_capacity: number;
  daily_walkin_capacity: number;
  display_vehicle_count: number;
  total_sales_executives: number;
}

export async function createShowroom(
  data: CreateShowroomRequest
): Promise<any> {
  // Call backend directly to avoid CloudFront blocking POST requests to API routes
  const backendUrl = `${API_BASE_URL}/gryd/db/object/showroom`;

  console.log("[Create Showroom] Calling backend directly:", backendUrl);
  console.log("[Create Showroom] Request body:", JSON.stringify(data, null, 2));

  const headers = getAuthHeaders();
  if (!headers["X-GRYD-TOKEN"] || !headers["X-GRYD-SESSION-ID"]) {
    throw new ApiError(401, "Authentication required. Please login again.");
  }

  const res = await fetch(backendUrl, {
    method: "POST",
    headers,
    body: JSON.stringify(data),
    cache: "no-store",
    mode: "cors",
    credentials: "omit",
  });

  console.log(`[Create Showroom] Response status: ${res.status}`);

  if (!res.ok) {
    let errorMessage = `Failed to create showroom (${res.status})`;
    try {
      const errorText = await res.text();
      console.error(`[Create Showroom] Error response text:`, errorText);
      try {
        const errorData = JSON.parse(errorText);
        errorMessage =
          errorData?.error || errorData?.message || errorText || errorMessage;
      } catch {
        errorMessage = errorText || errorMessage;
      }
    } catch (readError) {
      console.error("[Create Showroom] Failed to read error:", readError);
    }

    errorMessage =
      errorMessage.replace(/^API Error:\s*\d*\s*/i, "").trim() || errorMessage;
    throw new ApiError(res.status, errorMessage);
  }

  const responseData = await res.json();
  console.log("[Create Showroom] Response:", responseData);
  return responseData;
}

export async function getShowroomsForDealership(
  dealershipId: string
): Promise<any[]> {
  // Call backend directly to avoid CloudFront blocking GET requests to API routes
  const backendUrl = `${API_BASE_URL}/gryd/db/objects/showroom?dealership_id=${encodeURIComponent(
    dealershipId
  )}`;

  console.log("[Get Showrooms] Calling backend directly:", backendUrl);

  const headers = getAuthHeaders();
  if (!headers["X-GRYD-TOKEN"] || !headers["X-GRYD-SESSION-ID"]) {
    throw new ApiError(401, "Authentication required. Please login again.");
  }

  const res = await fetch(backendUrl, {
    method: "GET",
    headers: {
      Accept: "application/json",
      "X-GRYD-ENTERPRISE-ID": "autocrm",
      "X-GRYD-TOKEN": headers["X-GRYD-TOKEN"],
      "X-GRYD-SESSION-ID": headers["X-GRYD-SESSION-ID"],
      "X-GRYD-ROLE": "agent",
      "X-GRYD-APPLICATION-ID": headers["X-GRYD-APPLICATION-ID"],
    },
    cache: "no-store",
    mode: "cors",
    credentials: "omit",
  });

  console.log(`[Get Showrooms] Response status: ${res.status}`);

  if (!res.ok) {
    if (res.status === 404) {
      return [];
    }
    let errorMessage = `Failed to fetch showrooms (${res.status})`;
    try {
      const errorText = await res.text();
      console.error(`[Get Showrooms] Error response text:`, errorText);
      try {
        const errorData = JSON.parse(errorText);
        errorMessage =
          errorData?.error || errorData?.message || errorText || errorMessage;
      } catch {
        errorMessage = errorText || errorMessage;
      }
    } catch (readError) {
      console.error("[Get Showrooms] Failed to read error:", readError);
    }

    errorMessage =
      errorMessage.replace(/^API Error:\s*\d*\s*/i, "").trim() || errorMessage;
    throw new ApiError(res.status, errorMessage);
  }

  const responseData = await res.json();
  console.log("[Get Showrooms] Response:", responseData);

  if (Array.isArray(responseData)) {
    return responseData;
  } else if (responseData && Array.isArray(responseData.data)) {
    return responseData.data;
  } else if (responseData && Array.isArray(responseData.showrooms)) {
    return responseData.showrooms;
  }

  return [];
}

// Buyback Center interfaces and functions
export interface CreateBuybackCenterRequest {
  buyback_center_id: string;
  dealership_id: string;
  dealership_name: string;
  manager_name: string;
  email: string;
  contact_number: string;
  address: string;
  city: string;
  state: string;
  pincode: string;
  geolocation: [number, number];
  operating_hours: {
    opening_time: string;
    closing_time: string;
  };
  days_open: Record<string, any> | string[];
  parking_capacity: number;
  daily_walkin_capacity: number;
  display_vehicle_count: number;
  total_sales_executives: number;
}

export async function createBuybackCenter(
  data: CreateBuybackCenterRequest
): Promise<any> {
  // Call backend directly to avoid CloudFront blocking POST requests to API routes
  const backendUrl = `${API_BASE_URL}/gryd/db/object/buyback_center`;

  console.log("[Create Buyback Center] Calling backend directly:", backendUrl);
  console.log(
    "[Create Buyback Center] Request body:",
    JSON.stringify(data, null, 2)
  );

  const headers = getAuthHeaders();
  if (!headers["X-GRYD-TOKEN"] || !headers["X-GRYD-SESSION-ID"]) {
    throw new ApiError(401, "Authentication required. Please login again.");
  }

  const res = await fetch(backendUrl, {
    method: "POST",
    headers,
    body: JSON.stringify(data),
    cache: "no-store",
    mode: "cors",
    credentials: "omit",
  });

  console.log(`[Create Buyback Center] Response status: ${res.status}`);

  if (!res.ok) {
    let errorMessage = `Failed to create buyback center (${res.status})`;
    try {
      const errorText = await res.text();
      console.error(`[Create Buyback Center] Error response text:`, errorText);
      try {
        const errorData = JSON.parse(errorText);
        errorMessage =
          errorData?.error || errorData?.message || errorText || errorMessage;
      } catch {
        errorMessage = errorText || errorMessage;
      }
    } catch (readError) {
      console.error("[Create Buyback Center] Failed to read error:", readError);
    }

    errorMessage =
      errorMessage.replace(/^API Error:\s*\d*\s*/i, "").trim() || errorMessage;
    throw new ApiError(res.status, errorMessage);
  }

  const responseData = await res.json();
  console.log("[Create Buyback Center] Response:", responseData);
  return responseData;
}

export async function getBuybackCentersForDealership(
  dealershipId: string
): Promise<any[]> {
  // Call backend directly to avoid CloudFront blocking GET requests to API routes
  const backendUrl = `${API_BASE_URL}/gryd/db/objects/buyback_center?dealership_id=${encodeURIComponent(
    dealershipId
  )}`;

  console.log("[Get Buyback Centers] Calling backend directly:", backendUrl);

  const headers = getAuthHeaders();
  if (!headers["X-GRYD-TOKEN"] || !headers["X-GRYD-SESSION-ID"]) {
    throw new ApiError(401, "Authentication required. Please login again.");
  }

  const res = await fetch(backendUrl, {
    method: "GET",
    headers: {
      Accept: "application/json",
      "X-GRYD-ENTERPRISE-ID": "autocrm",
      "X-GRYD-TOKEN": headers["X-GRYD-TOKEN"],
      "X-GRYD-SESSION-ID": headers["X-GRYD-SESSION-ID"],
      "X-GRYD-ROLE": "agent",
      "X-GRYD-APPLICATION-ID": headers["X-GRYD-APPLICATION-ID"],
    },
    cache: "no-store",
    mode: "cors",
    credentials: "omit",
  });

  console.log(`[Get Buyback Centers] Response status: ${res.status}`);

  if (!res.ok) {
    if (res.status === 404) {
      return [];
    }
    let errorMessage = `Failed to fetch buyback centers (${res.status})`;
    try {
      const errorText = await res.text();
      console.error(`[Get Buyback Centers] Error response text:`, errorText);
      try {
        const errorData = JSON.parse(errorText);
        errorMessage =
          errorData?.error || errorData?.message || errorText || errorMessage;
      } catch {
        errorMessage = errorText || errorMessage;
      }
    } catch (readError) {
      console.error("[Get Buyback Centers] Failed to read error:", readError);
    }

    errorMessage =
      errorMessage.replace(/^API Error:\s*\d*\s*/i, "").trim() || errorMessage;
    throw new ApiError(res.status, errorMessage);
  }

  const responseData = await res.json();
  console.log("[Get Buyback Centers] Response:", responseData);

  if (Array.isArray(responseData)) {
    return responseData;
  } else if (responseData && Array.isArray(responseData.data)) {
    return responseData.data;
  } else if (responseData && Array.isArray(responseData.buyback_centers)) {
    return responseData.buyback_centers;
  }

  return [];
}
