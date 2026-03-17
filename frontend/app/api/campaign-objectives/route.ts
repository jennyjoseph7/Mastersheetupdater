import { cookies } from "next/headers";
import { NextResponse } from "next/server";
// Import shared logic
import { APP_BASE_URL, createApiHeaders } from "@/utils/headers"; // Adjust path to where header.ts is located

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
 export async function GET() {
  const cookieStore = cookies();
  
 // 1. Get credentials from Server Cookies
  let token = cookieStore.get("gryd_token")?.value;
  let sessionId = cookieStore.get("gryd_session_id")?.value;
  let applicationId = cookieStore.get("gryd_application_id")?.value;

  // CRITICAL FIX: Always use "autocrm", never "gryd"
  if (applicationId === "gryd" || !applicationId) {
    applicationId = "autocrm";
  }

   
  if (!token || !sessionId) {
    console.warn("[Audience Task API] Missing credentials. Returning 401.");
    return NextResponse.json(
      { error: "Authentication required" },
      { status: 401 }
    );
  }

  try {
    // 3. Generate Headers using the shared helper
    // Note: We override role to 'admin' as per your original requirement
    const headers = createApiHeaders({
      token,
      sessionId,
      applicationId,
      role: "admin", 
    });

    console.log("[Audience Task API] Application ID used:", headers["X-GRYD-APPLICATION-ID"]);

    // Define campaignType (replace 'defaultType' with the actual value you want)
    const campaignType = "";

    const url = `${API_BASE_URL}/campaign_objective?campaign_type=${campaignType}`;
    console.log("[API Route] Fetching from:", url);

    const res = await fetch(url, {
      method: "GET",
      headers,
      cache: "no-store",
    });

    console.log("[API Route] Response status:", res.status);

    if (!res.ok) {
      const errorText = await res.text();
      console.error("[API Route] Error response:", errorText);
      return NextResponse.json(
        { error: `API Error: ${res.status} ${errorText}` },
        { status: res.status }
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error fetching campaign objectives:", error);
    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? error.message
            : "Failed to fetch campaign objectives",
      },
      { status: 500 }
    );
  }
}
