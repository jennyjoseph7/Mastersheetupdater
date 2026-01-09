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

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Get credentials from cookies (set during login)
    const token = getCookieFromRequest(request, "gryd_token");
    const sessionId = getCookieFromRequest(request, "gryd_session_id");
    let applicationId = getCookieFromRequest(request, "gryd_application_id");

    // CRITICAL FIX: Always use "autocrm", never "gryd"
    // Backend returns "gryd" sometimes, but we need "autocrm"
    if (applicationId === "gryd" || !applicationId) {
      applicationId = "autocrm";
    }

    // Require authentication - no fallback to hardcoded credentials
    if (!token || !sessionId) {
      console.error("[Create Workshop API] Missing authentication credentials");
      return NextResponse.json(
        { error: "Authentication required. Please login again." },
        { status: 401 }
      );
    }

    console.log("[Create Workshop API] Using user credentials from cookies");
    console.log("[Create Workshop API] Application ID (fixed):", applicationId);

    // Proxy the request to the backend
    // URL matches the curl command exactly
    const backendUrl = `https://autobot-webapp-dev.gryd.in/gryd/db/object/workshop`;

    // Headers must match the curl exactly, including X-GRYD-APPLICATION-ID
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      Accept: "application/json",
      "X-GRYD-ENTERPRISE-ID": "autocrm",
      "X-GRYD-TOKEN": token,
      "X-GRYD-SESSION-ID": sessionId,
      "X-GRYD-APPLICATION-ID": applicationId,
    };

    console.log("=".repeat(80));
    console.log("[Create Workshop API] ===== REQUEST START =====");
    console.log("[Create Workshop API] Backend URL:", backendUrl);
    console.log("[Create Workshop API] Method: POST");
    console.log(
      "[Create Workshop API] Headers:",
      JSON.stringify(headers, null, 2)
    );
    console.log("[Create Workshop API] Token:", token);
    console.log("[Create Workshop API] Session ID:", sessionId);
    console.log(
      "[Create Workshop API] Request body:",
      JSON.stringify(body, null, 2)
    );
    console.log("[Create Workshop API] ===== REQUEST END =====");
    console.log("=".repeat(80));

    // Create fetch options matching curl exactly
    const fetchOptions: RequestInit = {
      method: "POST",
      headers: headers,
      body: JSON.stringify(body),
      cache: "no-store",
      // Ensure no extra headers or options are added
      redirect: "follow",
    };

    const res = await fetch(backendUrl, fetchOptions);

    console.log("=".repeat(80));
    console.log("[Create Workshop API] ===== RESPONSE START =====");
    console.log(
      `[Create Workshop API] Response status: ${res.status} ${res.statusText}`
    );
    console.log(
      `[Create Workshop API] Response headers:`,
      JSON.stringify(Object.fromEntries(res.headers.entries()), null, 2)
    );

    if (!res.ok) {
      const errorText = await res.text();
      console.error(`[Create Workshop API] Error response text:`, errorText);
      console.log("[Create Workshop API] ===== RESPONSE END =====");
      console.log("=".repeat(80));

      let errorMessage = `Failed to create workshop (${res.status})`;
      try {
        const errorData = JSON.parse(errorText);
        errorMessage =
          errorData?.error || errorData?.message || errorText || errorMessage;
      } catch {
        errorMessage = errorText || errorMessage;
      }
      return NextResponse.json({ error: errorMessage }, { status: res.status });
    }

    const data = await res.json();
    console.log("[Create Workshop API] Response:", data);
    return NextResponse.json(data);
  } catch (error) {
    console.error("[Create Workshop API] Error:", error);
    return NextResponse.json(
      {
        error:
          error instanceof Error ? error.message : "Failed to create workshop",
      },
      { status: 500 }
    );
  }
}

export async function GET(request: NextRequest) {
  try {
    // Get credentials from cookies (set during login)
    const token = getCookieFromRequest(request, "gryd_token");
    const sessionId = getCookieFromRequest(request, "gryd_session_id");
    let applicationId = getCookieFromRequest(request, "gryd_application_id");

    // CRITICAL FIX: Always use "autocrm", never "gryd"
    // Backend returns "gryd" sometimes, but we need "autocrm"
    if (applicationId === "gryd" || !applicationId) {
      applicationId = "autocrm";
    }

    if (!token || !sessionId) {
      return NextResponse.json(
        { error: "Authentication required. Please login again." },
        { status: 401 }
      );
    }

    // Get query parameters
    const { searchParams } = new URL(request.url);
    const dealershipId = searchParams.get("dealership_id");

    if (!dealershipId) {
      return NextResponse.json(
        { error: "dealership_id query parameter is required" },
        { status: 400 }
      );
    }

    // Proxy the request to the backend
    const backendUrl = `https://autobot-webapp-dev.gryd.in/gryd/db/objects/workshop?dealership_id=${encodeURIComponent(
      dealershipId
    )}`;

    console.log("[Get Workshops API] Calling backend:", backendUrl);
    console.log("[Get Workshops API] Application ID (fixed):", applicationId);

    const res = await fetch(backendUrl, {
      method: "GET",
      headers: {
        Accept: "application/json",
        "X-GRYD-ENTERPRISE-ID": "autocrm",
        "X-GRYD-TOKEN": token,
        "X-GRYD-SESSION-ID": sessionId,
        "X-GRYD-ROLE": "agent",
        "X-GRYD-APPLICATION-ID": applicationId,
      },
      cache: "no-store",
    });

    console.log(`[Get Workshops API] Response status: ${res.status}`);

    if (!res.ok) {
      // If 404, return empty array (no workshops found)
      if (res.status === 404) {
        return NextResponse.json([]);
      }
      const errorText = await res.text();
      console.error(`[Get Workshops API] Error response:`, errorText);
      let errorMessage = `Failed to fetch workshops (${res.status})`;
      try {
        const errorData = JSON.parse(errorText);
        errorMessage =
          errorData?.error || errorData?.message || errorText || errorMessage;
      } catch {
        errorMessage = errorText || errorMessage;
      }
      return NextResponse.json({ error: errorMessage }, { status: res.status });
    }

    const data = await res.json();
    console.log("[Get Workshops API] Response:", data);

    // Handle both array and object responses
    if (Array.isArray(data)) {
      return NextResponse.json(data);
    } else if (data && Array.isArray(data.data)) {
      return NextResponse.json(data.data);
    } else if (data && Array.isArray(data.workshops)) {
      return NextResponse.json(data.workshops);
    }

    return NextResponse.json([]);
  } catch (error) {
    console.error("[Get Workshops API] Error:", error);
    return NextResponse.json(
      {
        error:
          error instanceof Error ? error.message : "Failed to fetch workshops",
      },
      { status: 500 }
    );
  }
}
