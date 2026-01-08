import { NextRequest, NextResponse } from "next/server";

// Helper function to get cookie from request headers
function getCookieFromRequest(
  request: NextRequest,
  name: string,
): string | null {
  const cookieHeader = request.headers.get("cookie");
  if (!cookieHeader) return null;

  const cookies = cookieHeader.split(";").reduce(
    (acc, cookie) => {
      const [key, value] = cookie.trim().split("=");
      acc[key] = decodeURIComponent(value);
      return acc;
    },
    {} as Record<string, string>,
  );

  return cookies[name] || null;
}

// Skip static generation - API routes are not used with static export

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Get credentials from cookies (set during login)
    const token = getCookieFromRequest(request, "gryd_token");
    const sessionId = getCookieFromRequest(request, "gryd_session_id");

    // Require authentication
    if (!token || !sessionId) {
      console.error(
        "[Create Buyback Center API] Missing authentication credentials",
      );
      return NextResponse.json(
        { error: "Authentication required. Please login again." },
        { status: 401 },
      );
    }

    console.log(
      "[Create Buyback Center API] Using user credentials from cookies",
    );

    // Proxy the request to the backend
    const backendUrl = `https://autobot-webapp-dev.gryd.in/gryd/db/object/buyback_center`;

    // Headers must include X-GRYD-APPLICATION-ID to prevent backend defaulting to "gryd"
    // Postman curl doesn't show it, but backend requires it to avoid "Unauthorized user for application_id gryd!" error
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      Accept: "application/json",
      "X-GRYD-ENTERPRISE-ID": "autocrm",
      "X-GRYD-TOKEN": token,
      "X-GRYD-SESSION-ID": sessionId,
      "X-GRYD-ROLE": "agent",
      "X-GRYD-APPLICATION-ID": "autocrm",
    };

    console.log("=".repeat(80));
    console.log("[Create Buyback Center API] ===== REQUEST START =====");
    console.log("[Create Buyback Center API] Backend URL:", backendUrl);
    console.log("[Create Buyback Center API] Method: POST");
    console.log(
      "[Create Buyback Center API] Headers:",
      JSON.stringify(headers, null, 2),
    );
    console.log(
      "[Create Buyback Center API] Request body:",
      JSON.stringify(body, null, 2),
    );
    console.log("[Create Buyback Center API] ===== REQUEST END =====");
    console.log("=".repeat(80));

    const res = await fetch(backendUrl, {
      method: "POST",
      headers: headers,
      body: JSON.stringify(body),
      cache: "no-store",
      redirect: "follow",
    });

    console.log("=".repeat(80));
    console.log("[Create Buyback Center API] ===== RESPONSE START =====");
    console.log(
      `[Create Buyback Center API] Response status: ${res.status} ${res.statusText}`,
    );

    if (!res.ok) {
      const errorText = await res.text();
      console.error(
        `[Create Buyback Center API] Error response text:`,
        errorText,
      );
      console.log("[Create Buyback Center API] ===== RESPONSE END =====");
      console.log("=".repeat(80));

      let errorMessage = `Failed to create buyback center (${res.status})`;
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
    console.log("[Create Buyback Center API] Response:", data);
    console.log("[Create Buyback Center API] ===== RESPONSE END =====");
    console.log("=".repeat(80));
    return NextResponse.json(data);
  } catch (error) {
    console.error("[Create Buyback Center API] Error:", error);
    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? error.message
            : "Failed to create buyback center",
      },
      { status: 500 },
    );
  }
}

export async function GET(request: NextRequest) {
  try {
    // Get credentials from cookies
    const token = getCookieFromRequest(request, "gryd_token");
    const sessionId = getCookieFromRequest(request, "gryd_session_id");

    if (!token || !sessionId) {
      return NextResponse.json(
        { error: "Authentication required. Please login again." },
        { status: 401 },
      );
    }

    // Get query parameters
    const { searchParams } = new URL(request.url);
    const dealershipId = searchParams.get("dealership_id");

    if (!dealershipId) {
      return NextResponse.json(
        { error: "dealership_id query parameter is required" },
        { status: 400 },
      );
    }

    // Proxy the request to the backend
    const backendUrl = `https://autobot-webapp-dev.gryd.in/gryd/db/objects/buyback_center?dealership_id=${encodeURIComponent(
      dealershipId,
    )}`;

    console.log("[Get Buyback Centers API] Calling backend:", backendUrl);

    const res = await fetch(backendUrl, {
      method: "GET",
      headers: {
        Accept: "application/json",
        "X-GRYD-ENTERPRISE-ID": "autocrm",
        "X-GRYD-TOKEN": token,
        "X-GRYD-SESSION-ID": sessionId,
        "X-GRYD-ROLE": "agent",
        "X-GRYD-APPLICATION-ID": "autocrm",
      },
      cache: "no-store",
    });

    console.log(`[Get Buyback Centers API] Response status: ${res.status}`);

    if (!res.ok) {
      if (res.status === 404) {
        return NextResponse.json([]);
      }
      const errorText = await res.text();
      console.error(`[Get Buyback Centers API] Error response:`, errorText);
      let errorMessage = `Failed to fetch buyback centers (${res.status})`;
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
    console.log("[Get Buyback Centers API] Response:", data);

    // Handle both array and object responses
    if (Array.isArray(data)) {
      return NextResponse.json(data);
    } else if (data && Array.isArray(data.data)) {
      return NextResponse.json(data.data);
    } else if (data && Array.isArray(data.buyback_centers)) {
      return NextResponse.json(data.buyback_centers);
    }

    return NextResponse.json([]);
  } catch (error) {
    console.error("[Get Buyback Centers API] Error:", error);
    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? error.message
            : "Failed to fetch buyback centers",
      },
      { status: 500 },
    );
  }
}
