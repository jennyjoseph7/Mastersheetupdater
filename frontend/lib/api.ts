import { triggerGlobalLogout } from "@/lib/auth-context";

const getApiBaseUrl = () => {
  const url = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();

  if (!url) {
    throw new Error(
      "❌ NEXT_PUBLIC_API_BASE_URL is not defined. Please set it in your environment variables."
    );
  }

  console.log(`[APP_ENV] Using API URL -> ${url}`);
  return url;
  
};

export const API_BASE_URL = getApiBaseUrl();

// Helper function to get cookie (moved to top for initialization)
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

// Get credentials from cookies for default headers
const token = getCookieFromDocument("gryd_token");
const sessionId = getCookieFromDocument("gryd_session_id");
let applicationId = getCookieFromDocument("gryd_application_id");

// CRITICAL FIX: Always use "autocrm", never "gryd"
if (applicationId === "gryd" || !applicationId) {
  applicationId = "autocrm";
}

const DEFAULT_HEADERS = {
  "Content-Type": "application/json",
  Accept: "application/json",
  "X-GRYD-ENTERPRISE-ID": "autocrm",
  "X-GRYD-TOKEN": token || "", // Removed hardcoded fallback
  "X-GRYD-SESSION-ID": sessionId || "", // Removed hardcoded fallback
  "X-GRYD-APPLICATION-ID": applicationId,
  "X-GRYD-ROLE": "agent",
};

export async function api(
  endpoint: string,
  method: string = "GET",
  body?: any,
  customHeaders: Record<string, string> = {}
) {
  const fullUrl = `${API_BASE_URL}${endpoint}`;

  // Re-fetch cookies to ensure headers are fresh on every request (fixes SPA navigation issues)
  const freshToken = getCookieFromDocument("gryd_token");
  const freshSessionId = getCookieFromDocument("gryd_session_id");
  let freshAppId = getCookieFromDocument("gryd_application_id");
  if (freshAppId === "gryd" || !freshAppId) freshAppId = "autocrm";

  // --- MISSING COOKIE CHECK ---
  if (!freshToken || !freshSessionId) {
    console.warn(
      `[API] Missing credentials for ${fullUrl}. Triggering logout...`
    );
    triggerGlobalLogout();
    throw new Error("Authentication required");
  }
  // ----------------------------

  // Merge headers - customHeaders override DEFAULT_HEADERS
  const headers: Record<string, string> = {
    ...DEFAULT_HEADERS,
    "X-GRYD-TOKEN": freshToken,
    "X-GRYD-SESSION-ID": freshSessionId,
    "X-GRYD-APPLICATION-ID": freshAppId,
    ...customHeaders,
  };

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

  // --- AUTO-LOGOUT CHECK ---
  if (res.status === 401) {
    console.warn(`[API] 401 detected at ${fullUrl}. Triggering logout...`);
    triggerGlobalLogout();
  }
  // -------------------------

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
  // Get credentials from cookies
  const token = getCookieFromDocument("gryd_token");
  const sessionId = getCookieFromDocument("gryd_session_id");
  let applicationId = getCookieFromDocument("gryd_application_id");

  // CRITICAL FIX: Always use "autocrm", never "gryd"
  if (applicationId === "gryd" || !applicationId) {
    applicationId = "autocrm";
  }

  // --- MISSING COOKIE CHECK ---
  if (!token || !sessionId) {
    console.warn(
      "[Fetch Person Objects] Missing credentials. Triggering logout..."
    );
    triggerGlobalLogout();
    throw new ApiError(401, "Authentication required");
  }
  // ----------------------------

  const finalToken = token;
  const finalSessionId = sessionId;

  // Call backend directly
  const backendUrl = `${API_BASE_URL}/gryd/db/objects/person`;

  console.log("[Fetch Person Objects] Calling backend directly:", backendUrl);
  console.log("[Fetch Person Objects] Application ID (fixed):", applicationId);

  const res = await fetch(backendUrl, {
    method: "GET",
    headers: {
      // Don't include Content-Type for GET requests to avoid CORS preflight
      Accept: "application/json",
      "X-GRYD-ENTERPRISE-ID": "autocrm",
      "X-GRYD-TOKEN": finalToken,
      "X-GRYD-SESSION-ID": finalSessionId,
      "X-GRYD-APPLICATION-ID": applicationId,
      "X-GRYD-ROLE": "admin",
    },
    cache: "no-store",
    // Don't use credentials: "include" - we manually extract cookies and send them as headers
    // This avoids CORS issues when backend returns Access-Control-Allow-Origin: *
    mode: "cors", // Explicitly set CORS mode
  });

  console.log(`[Fetch Person Objects] Response status: ${res.status}`);

  // --- AUTO-LOGOUT CHECK ---
  if (res.status === 401) {
    triggerGlobalLogout();
  }
  // -------------------------

  if (!res.ok) {
    let errorMessage = `Failed to fetch person objects (${res.status})`;
    try {
      const errorData = await res.json();
      errorMessage = errorData?.error || errorData?.message || errorMessage;
    } catch {
      const errorText = await res.text();
      errorMessage = errorText || errorMessage;
    }
    throw new ApiError(res.status, errorMessage);
  }

  const data = await res.json();
  console.log("[Fetch Person Objects] Response:", data);
  return data;
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
    credits_balance?: number;
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

  // Call backend directly - matches Postman curl pattern
  const backendUrl = `${API_BASE_URL}/generate_otp`;

  const requestBody = {
    args: [contact, type],
    kwargs: {},
  };

  console.log("[Generate OTP] Calling backend directly:", backendUrl);
  console.log("[Generate OTP] Contact:", contact);
  console.log("[Generate OTP] Type:", type);

  const res = await fetch(backendUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-GRYD-ENTERPRISE-ID": "autocrm",
      "X-GRYD-SIGNUP-TOKEN": process.env.NEXT_PUBLIC_SIGNUP_API_KEY || "",
    },
    body: JSON.stringify(requestBody),
    cache: "no-store",
    // Don't use credentials: "include" - we manually extract cookies and send them as headers
    // This avoids CORS issues when backend returns Access-Control-Allow-Origin: *
    mode: "cors",
  });

  console.log(`[Generate OTP] Response status: ${res.status}`);

  if (!res.ok) {
    let errorMessage = `Request failed (${res.status})`;
    try {
      const errorData = await res.json();
      errorMessage = errorData?.error || errorData?.message || errorMessage;
    } catch {
      const errorText = await res.text();
      errorMessage = errorText || errorMessage;
    }

    errorMessage =
      errorMessage.replace(/^API Error:\s*\d*\s*/i, "").trim() || errorMessage;
    throw new ApiError(res.status, errorMessage);
  }

  const data = await res.json();
  console.log("[Generate OTP] Response:", data);
  return data;
}

export async function dealershipSignup(data: DealershipSignupRequest) {
  // Call backend directly - matches Postman curl pattern
  const backendUrl = `${API_BASE_URL}/dealership_signup`;

  console.log("[Dealership Signup] Calling backend directly:", backendUrl);
  console.log(
    "[Dealership Signup] Request body:",
    JSON.stringify(data, null, 2)
  );

  const res = await fetch(backendUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-GRYD-ENTERPRISE-ID": "autocrm",
      "X-GRYD-SIGNUP-TOKEN": process.env.NEXT_PUBLIC_SIGNUP_API_KEY || "",
    },
    body: JSON.stringify(data),
    cache: "no-store",
    // Don't use credentials: "include" - we manually extract cookies and send them as headers
    // This avoids CORS issues when backend returns Access-Control-Allow-Origin: *
    mode: "cors",
  });

  console.log(`[Dealership Signup] Response status: ${res.status}`);

  if (!res.ok) {
    let errorMessage = `Request failed (${res.status})`;
    try {
      const errorData = await res.json();
      errorMessage = errorData?.error || errorData?.message || errorMessage;
    } catch {
      const errorText = await res.text();
      errorMessage = errorText || errorMessage;
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
    credit_balance?: number;
    website?: string;
  };
  _timeout?: number;
}

export async function dealershipUpdateDetails(
  data: DealershipUpdateDetailsRequest
) {
  // Get credentials from cookies
  const token = getCookieFromDocument("gryd_token");
  const sessionId = getCookieFromDocument("gryd_session_id");
  let applicationId = getCookieFromDocument("gryd_application_id");

  // CRITICAL FIX: Always use "autocrm", never "gryd"
  if (applicationId === "gryd" || !applicationId) {
    applicationId = "autocrm";
  }

  if (!token || !sessionId) {
    triggerGlobalLogout(); // Added auto-logout
    throw new ApiError(401, "Authentication required. Please login again.");
  }

  // Call backend directly
  const backendUrl = `${API_BASE_URL}/gryd/api/autocrm-core/dealership_update_details`;

  console.log(
    "[Dealership Update Details] Calling backend directly:",
    backendUrl
  );
  console.log(
    "[Dealership Update Details] Request body:",
    JSON.stringify(data, null, 2)
  );
  console.log(
    "[Dealership Update Details] Application ID (fixed):",
    applicationId
  );

  const res = await fetch(backendUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      "X-GRYD-ENTERPRISE-ID": "autocrm",
      "X-GRYD-TOKEN": token,
      "X-GRYD-SESSION-ID": sessionId,
      "X-GRYD-APPLICATION-ID": applicationId,
      "X-GRYD-ROLE": "agent",
    },
    body: JSON.stringify(data),
    cache: "no-store",
    // Don't use credentials: "include" - we manually extract cookies and send them as headers
    // This avoids CORS issues when backend returns Access-Control-Allow-Origin: *
    mode: "cors",
  });

  console.log(`[Dealership Update Details] Response status: ${res.status}`);

  // --- AUTO-LOGOUT CHECK ---
  if (res.status === 401) {
    triggerGlobalLogout();
  }
  // -------------------------

  if (!res.ok) {
    let errorMessage = `Request failed (${res.status})`;
    try {
      const errorData = await res.json();
      errorMessage = errorData?.error || errorData?.message || errorMessage;
    } catch {
      const errorText = await res.text();
      errorMessage = errorText || errorMessage;
    }

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

  const baseurl = API_BASE_URL;  
  const loginApiUrl = `${baseurl}/gryd/login`;
  const signupToken = process.env.NEXT_PUBLIC_SIGNUP_API_KEY;
 
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
      "X-GRYD-SIGNUP-TOKEN": signupToken || "",
    },
    body: JSON.stringify(requestBody),
    cache: "no-store",
    // Don't use credentials: "include" - we manually extract cookies and send them as headers
    // This avoids CORS issues when backend returns Access-Control-Allow-Origin: *
    mode: "cors", // Explicitly set CORS mode
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

export async function getDealershipDetails(): Promise<DealershipDetailsResponse> {
  // Get credentials from cookies
  const userId = getCookieFromDocument("gryd_user_id");
  const token = getCookieFromDocument("gryd_token");
  const sessionId = getCookieFromDocument("gryd_session_id");
  let applicationId = getCookieFromDocument("gryd_application_id");

  // CRITICAL FIX: Always use "autocrm", never "gryd"
  if (applicationId === "gryd" || !applicationId) {
    applicationId = "autocrm";
  }

  if (!userId || !token || !sessionId) {
    triggerGlobalLogout(); // Added auto-logout
    throw new ApiError(401, "Authentication required. Please login again.");
  }

  // Call backend directly
  const backendUrl = `${API_BASE_URL}/get-dealership-details/${userId}`;

  console.log("[Get Dealership Details] Calling backend directly:", backendUrl);
  console.log("[Get Dealership Details] Using user_id:", userId);
  console.log(
    "[Get Dealership Details] Application ID (fixed):",
    applicationId
  );

  const res = await fetch(backendUrl, {
    method: "GET",
    headers: {
      Accept: "application/json",
      "X-GRYD-ENTERPRISE-ID": "autocrm",
      "X-GRYD-TOKEN": token,
      "X-GRYD-SESSION-ID": sessionId,
      "X-GRYD-APPLICATION-ID": applicationId,
      "X-GRYD-ROLE": "agent",
    },
    cache: "no-store",
    // Don't use credentials: "include" - we manually extract cookies and send them as headers
    // This avoids CORS issues when backend returns Access-Control-Allow-Origin: *
    mode: "cors",
  });

  console.log(`[Get Dealership Details] Response status: ${res.status}`);

  // --- AUTO-LOGOUT CHECK ---
  if (res.status === 401) {
    triggerGlobalLogout();
  }
  // -------------------------

  if (!res.ok) {
    let errorMessage = `Failed to fetch dealership details (${res.status})`;
    try {
      const errorData = await res.json();
      errorMessage = errorData?.error || errorData?.message || errorMessage;
    } catch {
      const errorText = await res.text();
      errorMessage = errorText || errorMessage;
    }

    errorMessage =
      errorMessage.replace(/^API Error:\s*\d*\s*/i, "").trim() || errorMessage;
    throw new ApiError(res.status, errorMessage);
  }

  const responseData = await res.json();
  console.log("[Get Dealership Details22] Response:", responseData);
  localStorage.setItem("dealership_details", JSON.stringify(responseData));
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
  // Get credentials from cookies
  const token = getCookieFromDocument("gryd_token");
  const sessionId = getCookieFromDocument("gryd_session_id");
  let applicationId = getCookieFromDocument("gryd_application_id");

  // CRITICAL FIX: Always use "autocrm", never "gryd"
  if (applicationId === "gryd" || !applicationId) {
    applicationId = "autocrm";
  }

  if (!token || !sessionId) {
    triggerGlobalLogout(); // Added auto-logout
    throw new ApiError(401, "Authentication required. Please login again.");
  }

  // Call backend directly - matches Postman curl exactly
  const backendUrl = `${API_BASE_URL}/gryd/db/object/workshop`;

  console.log("[Create Workshop] Calling backend directly:", backendUrl);
  console.log("[Create Workshop] Request body:", JSON.stringify(data, null, 2));
  console.log("[Create Workshop] Application ID (fixed):", applicationId);

  const res = await fetch(backendUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      "X-GRYD-ENTERPRISE-ID": "autocrm",
      "X-GRYD-TOKEN": token,
      "X-GRYD-SESSION-ID": sessionId,
      "X-GRYD-APPLICATION-ID": applicationId,
    },
    body: JSON.stringify(data),
    cache: "no-store",
    // Don't use credentials: "include" - we manually extract cookies and send them as headers
    // This avoids CORS issues when backend returns Access-Control-Allow-Origin: *
    mode: "cors", // Explicitly set CORS mode
  });

  console.log(`[Create Workshop] Response status: ${res.status}`);

  // --- AUTO-LOGOUT CHECK ---
  if (res.status === 401) {
    triggerGlobalLogout();
  }
  // -------------------------

  if (!res.ok) {
    let errorMessage = `Failed to create workshop (${res.status})`;
    try {
      const errorData = await res.json();
      errorMessage = errorData?.error || errorData?.message || errorMessage;
    } catch {
      const errorText = await res.text();
      errorMessage = errorText || errorMessage;
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
  // Get credentials from cookies
  const token = getCookieFromDocument("gryd_token");
  const sessionId = getCookieFromDocument("gryd_session_id");
  let applicationId = getCookieFromDocument("gryd_application_id");

  // CRITICAL FIX: Always use "autocrm", never "gryd"
  if (applicationId === "gryd" || !applicationId) {
    applicationId = "autocrm";
  }

  if (!token || !sessionId) {
    triggerGlobalLogout(); // Added auto-logout
    throw new ApiError(401, "Authentication required. Please login again.");
  }

  // Call backend directly - matches Postman curl pattern
  const backendUrl = `${API_BASE_URL}/gryd/db/objects/workshop?dealership_id=${encodeURIComponent(
    dealershipId
  )}`;

  console.log("[Get Workshops] Calling backend directly:", backendUrl);
  console.log("[Get Workshops] Application ID (fixed):", applicationId);

  const res = await fetch(backendUrl, {
    method: "GET",
    headers: {
      Accept: "application/json",
      "X-GRYD-ENTERPRISE-ID": "autocrm",
      "X-GRYD-TOKEN": token,
      "X-GRYD-SESSION-ID": sessionId,
      "X-GRYD-APPLICATION-ID": applicationId,
      "X-GRYD-ROLE": "agent",
    },
    cache: "no-store",
    // Don't use credentials: "include" - we manually extract cookies and send them as headers
    // This avoids CORS issues when backend returns Access-Control-Allow-Origin: *
    mode: "cors", // Explicitly set CORS mode
  });

  console.log(`[Get Workshops] Response status: ${res.status}`);

  // --- AUTO-LOGOUT CHECK ---
  if (res.status === 401) {
    triggerGlobalLogout();
  }
  // -------------------------

  if (!res.ok) {
    // If 404, return empty array (no workshops found)
    if (res.status === 404) {
      return [];
    }
    let errorMessage = `Failed to fetch workshops (${res.status})`;
    try {
      const errorData = await res.json();
      errorMessage = errorData?.error || errorData?.message || errorMessage;
    } catch {
      const errorText = await res.text();
      errorMessage = errorText || errorMessage;
    }

    errorMessage =
      errorMessage.replace(/^API Error:\s*\d*\s*/i, "").trim() || errorMessage;
    throw new ApiError(res.status, errorMessage);
  }

  const responseData = await res.json();
  console.log("[Get Workshops] Response:", responseData);
  localStorage.setItem("workshops_data", JSON.stringify(responseData.data));

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
  // Get credentials from cookies
  const token = getCookieFromDocument("gryd_token");
  const sessionId = getCookieFromDocument("gryd_session_id");
  let applicationId = getCookieFromDocument("gryd_application_id");

  // CRITICAL FIX: Always use "autocrm", never "gryd"
  if (applicationId === "gryd" || !applicationId) {
    applicationId = "autocrm";
  }

  if (!token || !sessionId) {
    triggerGlobalLogout(); // Added auto-logout
    throw new ApiError(401, "Authentication required. Please login again.");
  }

  // Call backend directly - matches Postman curl exactly
  const backendUrl = `${API_BASE_URL}/gryd/db/object/showroom`;

  console.log("[Create Showroom] Calling backend directly:", backendUrl);
  console.log("[Create Showroom] Request body:", JSON.stringify(data, null, 2));
  console.log("[Create Showroom] Application ID (fixed):", applicationId);

  const res = await fetch(backendUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      "X-GRYD-ENTERPRISE-ID": "autocrm",
      "X-GRYD-TOKEN": token,
      "X-GRYD-SESSION-ID": sessionId,
      "X-GRYD-APPLICATION-ID": applicationId,
    },
    body: JSON.stringify(data),
    cache: "no-store",
    // Don't use credentials: "include" - we manually extract cookies and send them as headers
    // This avoids CORS issues when backend returns Access-Control-Allow-Origin: *
    mode: "cors", // Explicitly set CORS mode
  });

  console.log(`[Create Showroom] Response status: ${res.status}`);

  // --- AUTO-LOGOUT CHECK ---
  if (res.status === 401) {
    triggerGlobalLogout();
  }
  // -------------------------

  if (!res.ok) {
    let errorMessage = `Failed to create showroom (${res.status})`;
    try {
      const errorData = await res.json();
      errorMessage = errorData?.error || errorData?.message || errorMessage;
    } catch {
      const errorText = await res.text();
      errorMessage = errorText || errorMessage;
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
  // Get credentials from cookies
  const token = getCookieFromDocument("gryd_token");
  const sessionId = getCookieFromDocument("gryd_session_id");
  let applicationId = getCookieFromDocument("gryd_application_id");

  // CRITICAL FIX: Always use "autocrm", never "gryd"
  if (applicationId === "gryd" || !applicationId) {
    applicationId = "autocrm";
  }

  if (!token || !sessionId) {
    triggerGlobalLogout(); // Added auto-logout
    throw new ApiError(401, "Authentication required. Please login again.");
  }

  // Call backend directly - matches Postman curl pattern
  const backendUrl = `${API_BASE_URL}/gryd/db/objects/showroom?dealership_id=${encodeURIComponent(
    dealershipId
  )}`;

  console.log("[Get Showrooms] Calling backend directly:", backendUrl);
  console.log("[Get Showrooms] Application ID (fixed):", applicationId);

  const res = await fetch(backendUrl, {
    method: "GET",
    headers: {
      Accept: "application/json",
      "X-GRYD-ENTERPRISE-ID": "autocrm",
      "X-GRYD-TOKEN": token,
      "X-GRYD-SESSION-ID": sessionId,
      "X-GRYD-APPLICATION-ID": applicationId,
      "X-GRYD-ROLE": "agent",
    },
    cache: "no-store",
    // Don't use credentials: "include" - we manually extract cookies and send them as headers
    // This avoids CORS issues when backend returns Access-Control-Allow-Origin: *
    mode: "cors", // Explicitly set CORS mode
  });

  console.log(`[Get Showrooms] Response status: ${res.status}`);

  // --- AUTO-LOGOUT CHECK ---
  if (res.status === 401) {
    triggerGlobalLogout();
  }
  // -------------------------

  if (!res.ok) {
    if (res.status === 404) {
      return [];
    }
    let errorMessage = `Failed to fetch showrooms (${res.status})`;
    try {
      const errorData = await res.json();
      errorMessage = errorData?.error || errorData?.message || errorMessage;
    } catch {
      const errorText = await res.text();
      errorMessage = errorText || errorMessage;
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
  // Get credentials from cookies
  const token = getCookieFromDocument("gryd_token");
  const sessionId = getCookieFromDocument("gryd_session_id");
  let applicationId = getCookieFromDocument("gryd_application_id");

  // CRITICAL FIX: Always use "autocrm", never "gryd"
  if (applicationId === "gryd" || !applicationId) {
    applicationId = "autocrm";
  }

  if (!token || !sessionId) {
    triggerGlobalLogout(); // Added auto-logout
    throw new ApiError(401, "Authentication required. Please login again.");
  }

  // Call backend directly - matches Postman curl exactly
  const backendUrl = `${API_BASE_URL}/gryd/db/object/buyback_center`;

  console.log("[Create Buyback Center] Calling backend directly:", backendUrl);
  console.log(
    "[Create Buyback Center] Request body:",
    JSON.stringify(data, null, 2)
  );
  console.log("[Create Buyback Center] Application ID (fixed):", applicationId);

  const res = await fetch(backendUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      "X-GRYD-ENTERPRISE-ID": "autocrm",
      "X-GRYD-TOKEN": token,
      "X-GRYD-SESSION-ID": sessionId,
      "X-GRYD-APPLICATION-ID": applicationId,
    },
    body: JSON.stringify(data),
    cache: "no-store",
    // Don't use credentials: "include" - we manually extract cookies and send them as headers
    // This avoids CORS issues when backend returns Access-Control-Allow-Origin: *
    mode: "cors", // Explicitly set CORS mode
  });

  console.log(`[Create Buyback Center] Response status: ${res.status}`);

  // --- AUTO-LOGOUT CHECK ---
  if (res.status === 401) {
    triggerGlobalLogout();
  }
  // -------------------------

  if (!res.ok) {
    let errorMessage = `Failed to create buyback center (${res.status})`;
    try {
      const errorData = await res.json();
      errorMessage = errorData?.error || errorData?.message || errorMessage;
    } catch {
      const errorText = await res.text();
      errorMessage = errorText || errorMessage;
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
  // Get credentials from cookies
  const token = getCookieFromDocument("gryd_token");
  const sessionId = getCookieFromDocument("gryd_session_id");
  let applicationId = getCookieFromDocument("gryd_application_id");

  // CRITICAL FIX: Always use "autocrm", never "gryd"
  if (applicationId === "gryd" || !applicationId) {
    applicationId = "autocrm";
  }

  if (!token || !sessionId) {
    triggerGlobalLogout(); // Added auto-logout
    throw new ApiError(401, "Authentication required. Please login again.");
  }

  // Call backend directly - matches Postman curl pattern
  const backendUrl = `${API_BASE_URL}/gryd/db/objects/buyback_center?dealership_id=${encodeURIComponent(
    dealershipId
  )}`;

  console.log("[Get Buyback Centers] Calling backend directly:", backendUrl);
  console.log("[Get Buyback Centers] Application ID (fixed):", applicationId);

  const res = await fetch(backendUrl, {
    method: "GET",
    headers: {
      Accept: "application/json",
      "X-GRYD-ENTERPRISE-ID": "autocrm",
      "X-GRYD-TOKEN": token,
      "X-GRYD-SESSION-ID": sessionId,
      "X-GRYD-APPLICATION-ID": applicationId,
      "X-GRYD-ROLE": "agent",
    },
    cache: "no-store",
    // Don't use credentials: "include" - we manually extract cookies and send them as headers
    // This avoids CORS issues when backend returns Access-Control-Allow-Origin: *
    mode: "cors", // Explicitly set CORS mode
  });

  console.log(`[Get Buyback Centers] Response status: ${res.status}`);

  // --- AUTO-LOGOUT CHECK ---
  if (res.status === 401) {
    triggerGlobalLogout();
  }
  // -------------------------

  if (!res.ok) {
    if (res.status === 404) {
      return [];
    }
    let errorMessage = `Failed to fetch buyback centers (${res.status})`;
    try {
      const errorData = await res.json();
      errorMessage = errorData?.error || errorData?.message || errorMessage;
    } catch {
      const errorText = await res.text();
      errorMessage = errorText || errorMessage;
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

// Service Visit and Showroom Visit interfaces and functions for Conversions
export interface ServiceVisit {
  service_visit_id?: string;
  user_id?: string;
  person_name?: string;
  phone_number?: string;
  email?: string;
  appointment_date?: string;
  appointment_time?: string;
  purpose_of_visit?: string | string[];
  status?: string;
  dealership_id?: string;
  dealer_name?: string;
  workshop_name?: string;
  [key: string]: any;
}

export interface ShowroomVisit {
  showroom_visit_id?: string;
  user_id?: string;
  person_name?: string;
  phone_number?: string;
  email?: string;
  visit_date?: string;
  visit_timestamp?: number;
  purpose_of_visit?: string | string[];
  showroom_visit_status?: string;
  dealership_id?: string;
  dealer_name?: string;
  showroom_name?: string;
  [key: string]: any;
}

export async function getServiceVisitsForDealership(
  dealershipId: string
): Promise<ServiceVisit[]> {
  // Get credentials from cookies
  const token = getCookieFromDocument("gryd_token");
  const sessionId = getCookieFromDocument("gryd_session_id");
  let applicationId = getCookieFromDocument("gryd_application_id");

  // CRITICAL FIX: Always use "autocrm", never "gryd"
  if (applicationId === "gryd" || !applicationId) {
    applicationId = "autocrm";
  }

  if (!token || !sessionId) {
    triggerGlobalLogout();
    throw new ApiError(401, "Authentication required. Please login again.");
  }

  // Call backend directly
  const backendUrl = `${API_BASE_URL}/gryd/db/objects/service_visit?dealership_id=${encodeURIComponent(
    dealershipId
  )}`;

  console.log("[Get Service Visits] Calling backend directly:", backendUrl);
  console.log("[Get Service Visits] Application ID (fixed):", applicationId);

  const res = await fetch(backendUrl, {
    method: "GET",
    headers: {
      Accept: "application/json",
      "X-GRYD-ENTERPRISE-ID": "autocrm",
      "X-GRYD-TOKEN": token,
      "X-GRYD-SESSION-ID": sessionId,
      "X-GRYD-APPLICATION-ID": applicationId,
      "X-GRYD-ROLE": "agent",
    },
    cache: "no-store",
    mode: "cors",
  });

  console.log(`[Get Service Visits] Response status: ${res.status}`);

  // --- AUTO-LOGOUT CHECK ---
  if (res.status === 401) {
    triggerGlobalLogout();
  }
  // -------------------------

  if (!res.ok) {
    if (res.status === 404) {
      return [];
    }
    let errorMessage = `Failed to fetch service visits (${res.status})`;
    try {
      const errorData = await res.json();
      errorMessage = errorData?.error || errorData?.message || errorMessage;
    } catch {
      const errorText = await res.text();
      errorMessage = errorText || errorMessage;
    }

    errorMessage =
      errorMessage.replace(/^API Error:\s*\d*\s*/i, "").trim() || errorMessage;
    throw new ApiError(res.status, errorMessage);
  }

  const responseData = await res.json();
  console.log("[Get Service Visits] Response:", responseData);

  if (Array.isArray(responseData)) {
    return responseData;
  } else if (responseData && Array.isArray(responseData.data)) {
    return responseData.data;
  } else if (responseData && Array.isArray(responseData.service_visits)) {
    return responseData.service_visits;
  }

  return [];
}

export async function getShowroomVisitsForDealership(
  dealershipId: string
): Promise<ShowroomVisit[]> {
  // Get credentials from cookies
  const token = getCookieFromDocument("gryd_token");
  const sessionId = getCookieFromDocument("gryd_session_id");
  let applicationId = getCookieFromDocument("gryd_application_id");

  // CRITICAL FIX: Always use "autocrm", never "gryd"
  if (applicationId === "gryd" || !applicationId) {
    applicationId = "autocrm";
  }

  if (!token || !sessionId) {
    triggerGlobalLogout();
    throw new ApiError(401, "Authentication required. Please login again.");
  }

  // Call backend directly
  const backendUrl = `${API_BASE_URL}/gryd/db/objects/showroom_visit?dealership_id=${encodeURIComponent(
    dealershipId
  )}`;

  console.log("[Get Showroom Visits] Calling backend directly:", backendUrl);
  console.log("[Get Showroom Visits] Application ID (fixed):", applicationId);

  const res = await fetch(backendUrl, {
    method: "GET",
    headers: {
      Accept: "application/json",
      "X-GRYD-ENTERPRISE-ID": "autocrm",
      "X-GRYD-TOKEN": token,
      "X-GRYD-SESSION-ID": sessionId,
      "X-GRYD-APPLICATION-ID": applicationId,
      "X-GRYD-ROLE": "agent",
    },
    cache: "no-store",
    mode: "cors",
  });

  console.log(`[Get Showroom Visits] Response status: ${res.status}`);

  // --- AUTO-LOGOUT CHECK ---
  if (res.status === 401) {
    triggerGlobalLogout();
  }
  // -------------------------

  if (!res.ok) {
    if (res.status === 404) {
      return [];
    }
    let errorMessage = `Failed to fetch showroom visits (${res.status})`;
    try {
      const errorData = await res.json();
      errorMessage = errorData?.error || errorData?.message || errorMessage;
    } catch {
      const errorText = await res.text();
      errorMessage = errorText || errorMessage;
    }

    errorMessage =
      errorMessage.replace(/^API Error:\s*\d*\s*/i, "").trim() || errorMessage;
    throw new ApiError(res.status, errorMessage);
  }

  const responseData = await res.json();
  console.log("[Get Showroom Visits] Response:", responseData);

  if (Array.isArray(responseData)) {
    return responseData;
  } else if (responseData && Array.isArray(responseData.data)) {
    return responseData.data;
  } else if (responseData && Array.isArray(responseData.showroom_visits)) {
    return responseData.showroom_visits;
  }

  return [];
}
