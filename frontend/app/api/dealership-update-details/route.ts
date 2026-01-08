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

// Determine API base URL
const getApiBaseUrl = () => {
  // Check for explicit environment variable override
  if (process.env.NEXT_PUBLIC_API_BASE_URL) {
    return process.env.NEXT_PUBLIC_API_BASE_URL;
  }

  // Use production URL
  return "https://autobot-webapp-dev.gryd.in";
};

const API_BASE_URL = getApiBaseUrl();

export async function POST(request: NextRequest) {
  try {
    // Get credentials from cookies (set during login)
    const token = getCookieFromRequest(request, "gryd_token");
    const sessionId = getCookieFromRequest(request, "gryd_session_id");
    const applicationId = getCookieFromRequest(request, "gryd_application_id");

    if (!token || !sessionId) {
      return NextResponse.json(
        { error: "Authentication required. Please login again." },
        { status: 401 }
      );
    }

    const body = await request.json();

    const backendUrl = `${API_BASE_URL}/gryd/api/autocrm-core/dealership_update_details`;

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      Accept: "application/json",
      "X-GRYD-ENTERPRISE-ID": "autocrm",
      "X-GRYD-TOKEN": token,
      "X-GRYD-SESSION-ID": sessionId,
      "X-GRYD-ROLE": "agent",
      "X-GRYD-APPLICATION-ID": applicationId || "autocrm",
    };

    // Enhanced logging for debugging
    console.log("=".repeat(80));
    console.log("[Dealership Update Details] ===== REQUEST START =====");
    console.log(`[Dealership Update Details] API Base URL:`, API_BASE_URL);
    console.log(`[Dealership Update Details] Full Backend URL:`, backendUrl);
    console.log(`[Dealership Update Details] Method: POST`);
    console.log(
      `[Dealership Update Details] Headers:`,
      JSON.stringify(headers, null, 2)
    );
    console.log(
      `[Dealership Update Details] Request Body:`,
      JSON.stringify(body, null, 2)
    );
    console.log("[Dealership Update Details] ===== REQUEST END =====");
    console.log("=".repeat(80));

    const res = await fetch(backendUrl, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      cache: "no-store",
    });

    // Enhanced response logging
    console.log("=".repeat(80));
    console.log("[Dealership Update Details] ===== RESPONSE START =====");
    console.log(`[Dealership Update Details] Backend URL Called:`, backendUrl);
    console.log(
      `[Dealership Update Details] Response Status: ${res.status} ${res.statusText}`
    );
    console.log(
      `[Dealership Update Details] Response Headers:`,
      JSON.stringify(Object.fromEntries(res.headers.entries()), null, 2)
    );

    // Clone response to read body without consuming it
    const responseClone = res.clone();
    const responseText = await responseClone.text();
    console.log(
      `[Dealership Update Details] Response Body:`,
      responseText.substring(0, 1000)
    );
    console.log("[Dealership Update Details] ===== RESPONSE END =====");
    console.log("=".repeat(80));

    if (!res.ok) {
      let errorMessage = `Request failed (${res.status})`;
      let errorData: any = null;
      try {
        const errorText = responseText;
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

      const errorResponse = NextResponse.json(
        { error: errorMessage },
        { status: res.status }
      );
      // Add custom headers to show backend URL in network tab
      errorResponse.headers.set("X-Backend-URL", backendUrl);
      errorResponse.headers.set("X-API-Base-URL", API_BASE_URL);
      return errorResponse;
    }

    const data = JSON.parse(responseText);
    const successResponse = NextResponse.json(data);
    // Add custom headers to show backend URL in network tab
    successResponse.headers.set("X-Backend-URL", backendUrl);
    successResponse.headers.set("X-API-Base-URL", API_BASE_URL);
    return successResponse;
  } catch (error) {
    console.error("=".repeat(80));
    console.error("[Dealership Update Details] ===== ERROR START =====");
    console.error("Error in dealership update details proxy:", error);
    if (error instanceof Error) {
      console.error("Error name:", error.name);
      console.error("Error message:", error.message);
      console.error("Error stack:", error.stack);
    }
    console.error("[Dealership Update Details] ===== ERROR END =====");
    console.error("=".repeat(80));

    const errorMessage =
      error instanceof Error
        ? error.message
        : "Failed to update dealership details";
    return NextResponse.json({ error: errorMessage }, { status: 500 });
  }
}
