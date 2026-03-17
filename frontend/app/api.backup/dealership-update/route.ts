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

// Skip static generation - API routes are not used with static export

export async function POST(request: NextRequest) {
  try {
    // Get cookies from the request headers
       const token = getCookieFromRequest(request, "gryd_token");
    const sessionId = getCookieFromRequest(request, "gryd_session_id");
    const application_id = getCookieFromRequest(request, "gryd_application_id");


    if (!token || !sessionId) {
      return NextResponse.json(
        { error: "Authentication required. Please login again." },
        { status: 401 }
      );
    }

    const body = await request.json();

    // Proxy the request to the backend
    const baseurl= APP_BASE_URL;
        const backendUrl = `${baseurl}/gryd/api/autocrm-core/dealership_update_details`;

    console.log("[Dealership Update API] Calling backend:", backendUrl);
    console.log(
      "[Dealership Update API] Request body:",
      JSON.stringify(body, null, 2)
    );
    console.log(
      "[Dealership Update API] Using token:",
      token.substring(0, 20) + "..."
    );
    console.log("[Dealership Update API] Using session_id:", sessionId);

    const res = await fetch(backendUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-GRYD-ENTERPRISE-ID": "autocrm",
        "X-GRYD-TOKEN": "53014452-7df1-351c-9b79-af13d3d6b92f",
        "X-GRYD-SESSION-ID": "94b970d4-5c2b-3762-bf65-272901d0ad53",
        Accept: "application/json",
        "X-GRYD-ROLE": "agent",
      },
      body: JSON.stringify(body),
      cache: "no-store",
    });

    console.log(`[Dealership Update API] Response status: ${res.status}`);

    if (!res.ok) {
      const errorText = await res.text();
      console.error(`[Dealership Update API] Error:`, errorText);
      try {
        const errorData = JSON.parse(errorText);
        return NextResponse.json(
          {
            error:
              errorData?.error ||
              errorData?.message ||
              errorText ||
              `Failed to update dealership details (${res.status})`,
          },
          { status: res.status }
        );
      } catch {
        return NextResponse.json(
          {
            error:
              errorText ||
              `Failed to update dealership details (${res.status})`,
          },
          { status: res.status }
        );
      }
    }

    const data = await res.json();
    console.log("[Dealership Update API] Response:", data);
    return NextResponse.json(data);
  } catch (error) {
    console.error("[Dealership Update API] Error:", error);
    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? error.message
            : "Failed to update dealership details",
      },
      { status: 500 }
    );
  }
}
