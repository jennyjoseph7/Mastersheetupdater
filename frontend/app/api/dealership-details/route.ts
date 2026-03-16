import { APP_BASE_URL } from "@/utils/headers";
import { NextRequest, NextResponse } from "next/server";

// Helper function to get cookie from request headers
function getCookieFromRequest(
  request: NextRequest,
  name: string
): string | null {
  const cookieHeader = request.headers.get("cookie");
  if (!cookieHeader) return null;

  const cookies = cookieHeader.split(";").reduce((acc, cookie) => {
    const [key, value] = cookie.trim().split("=");
    acc[key] = decodeURIComponent(value);
    return acc;
  }, {} as Record<string, string>);

  return cookies[name] || null;
}

export async function GET(request: NextRequest) {
  try {
    // Get cookies from the request headers
    const token = getCookieFromRequest(request, "gryd_token");
    const sessionId = getCookieFromRequest(request, "gryd_session_id");
    let applicationId = getCookieFromRequest(request, "gryd_application_id");

    // Get user_id from query params or cookies
    const { searchParams } = new URL(request.url);
    let userId = searchParams.get("user_id") || getCookieFromRequest(request, "gryd_user_id");

    // CRITICAL FIX: Always use "autocrm", never "gryd"
    // Backend returns "gryd" sometimes, but we need "autocrm"
    if (applicationId === "gryd" || !applicationId) {
      applicationId = "autocrm";
    }

    if (!token || !sessionId || !userId) {
      return NextResponse.json(
        { error: "Authentication required. Please login again." },
        { status: 401 }
      );
    }

    // Proxy the request to the backend
    // Use production URL instead of localhost to avoid backend cursor errors
   const baseurl= APP_BASE_URL;
       const backendUrl = `${baseurl}/get-dealership-details/${userId}`;

    console.log("[Dealership Details API] Calling backend:", backendUrl);
    console.log("[Dealership Details API] Using user_id:", userId);
    console.log("[Dealership Details API] Application ID (fixed):", applicationId);

    const res = await fetch(backendUrl, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        "X-GRYD-ENTERPRISE-ID": "autocrm",
        "X-GRYD-TOKEN": token,
        "X-GRYD-SESSION-ID": sessionId,
        "X-GRYD-APPLICATION-ID": applicationId,
      },
      cache: "no-store",
    });

    console.log(`[Dealership Details API] Response status: ${res.status}`);

    if (!res.ok) {
      const errorText = await res.text();
      console.error(`[Dealership Details API] Error:`, errorText);
      return NextResponse.json(
        {
          error:
            errorText || `Failed to fetch dealership details (${res.status})`,
        },
        { status: res.status }
      );
    }

    const data = await res.json();
    console.log("[Dealership Details API] Response:", data);
    return NextResponse.json(data);
  } catch (error) {
    console.error("[Dealership Details API] Error:", error);
    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? error.message
            : "Failed to fetch dealership details",
      },
      { status: 500 }
    );
  }
}
