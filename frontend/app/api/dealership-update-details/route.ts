import { NextResponse } from "next/server";

// Determine API base URL based on environment
const getApiBaseUrl = () => {
  // Check for explicit environment variable override
  if (process.env.NEXT_PUBLIC_API_BASE_URL) {
    return process.env.NEXT_PUBLIC_API_BASE_URL;
  }
  
  // Check if we're in development (localhost)
  if (process.env.NODE_ENV === "development") {
    return "http://127.0.0.1:5008";
  }
  
  // Production URL
  return "https://autobot-webapp-dev.gryd.in";
};

const API_BASE_URL = getApiBaseUrl();

export async function POST(request: Request) {
  try {
    const body = await request.json();

    // Log the request body for debugging
    console.log(
      `[Dealership Update Details] Request body:`,
      JSON.stringify(body, null, 2)
    );
    console.log(`[Dealership Update Details] API Base URL:`, API_BASE_URL);
    console.log(
      `[Dealership Update Details] Full URL:`,
      `${API_BASE_URL}/gryd/api/autocrm-core/dealership_update_details`
    );

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      Accept: "application/json",
      "X-GRYD-ENTERPRISE-ID": "autocrm",
      "X-GRYD-TOKEN": "53014452-7df1-351c-9b79-af13d3d6b92f",
      "X-GRYD-SESSION-ID": "94b970d4-5c2b-3762-bf65-272901d0ad53",
      "X-GRYD-ROLE": "agent",
    };

    const res = await fetch(
      `${API_BASE_URL}/gryd/api/autocrm-core/dealership_update_details`,
      {
        method: "POST",
        headers,
        body: JSON.stringify(body),
        cache: "no-store",
      }
    );

    // Log response status for debugging
    console.log(
      `[Dealership Update Details] Backend response status: ${res.status}`
    );

    if (!res.ok) {
      let errorMessage = `Request failed (${res.status})`;
      let errorData: any = null;
      try {
        const errorText = await res.text();
        console.log(`[Dealership Update Details] Error response:`, errorText);
        try {
          errorData = JSON.parse(errorText);
          errorMessage =
            errorData?.error || errorData?.message || errorText || errorMessage;
        } catch {
          // Not JSON, use as is
          errorMessage = errorText || errorMessage;
        }
      } catch (readError) {
        console.error("[Dealership Update Details] Failed to read error:", readError);
      }

      console.error(`[Dealership Update Details] Returning error:`, errorMessage);
      return NextResponse.json({ error: errorMessage }, { status: res.status });
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error in dealership update details proxy:", error);
    const errorMessage =
      error instanceof Error
        ? error.message
        : "Failed to update dealership details";
    return NextResponse.json({ error: errorMessage }, { status: 500 });
  }
}

