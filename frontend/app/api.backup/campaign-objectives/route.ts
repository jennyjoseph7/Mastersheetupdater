import { cookies } from "next/headers";
import { NextResponse } from "next/server";

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

// Skip static generation - API routes are not used with static export

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const campaignType = searchParams.get("campaign_type");

    if (!campaignType) {
      return NextResponse.json(
        { error: "campaign_type parameter is required" },
        { status: 400 }
      );
    }
  // Get credentials from cookies (set during login)
    let token = cookies().get("gryd_token")?.value;
    let sessionId = cookies().get("gryd_session_id")?.value;
    let application_id = cookies().get("gryd_application_id")?.value;

    // Fallback to hardcoded credentials if user credentials not available
    // These match the curl that works successfully
    if (!token || !sessionId) {
      console.log("[Create Workshop API] Using fallback hardcoded credentials");
      token = "53014452-7df1-351c-9b79-af13d3d6b92f";
      sessionId = "94b970d4-5c2b-3762-bf65-272901d0ad53";
    } else {
      console.log("[Create Workshop API] Using user credentials from cookies");
    }
const headers: Record<string, string> = {
      "Content-Type": "application/json",
      Accept: "application/json",
      "X-GRYD-ENTERPRISE-ID": "autocrm",
      "X-GRYD-TOKEN": token,
      "X-GRYD-SESSION-ID": sessionId,
      "X-GRYD-APPLICATION-ID": application_id || "autocrm",
      "X-GRYD-ROLE": "admin",
    };

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
