import { cookies } from "next/headers";
import { NextResponse } from "next/server";
// Import shared logic
import { APP_BASE_URL, createApiHeaders } from "@/utils/headers"; // Adjust path to where header.ts is located

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

    const res = await fetch(`${APP_BASE_URL}/gryd/db/objects/audience_task`, {
      method: "GET",
      // We cast to Record<string, string> to satisfy TypeScript fetch definitions if needed
      headers: headers as Record<string, string>, 
      cache: "no-store",
    });

    if (!res.ok) {
      const errorText = await res.text();
      return NextResponse.json(
        { error: `API Error: ${res.status} ${errorText}` },
        { status: res.status }
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error fetching audience task:", error);
    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? error.message
            : "Failed to fetch audience task",
      },
      { status: 500 }
    );
  }
}