import { NextResponse } from "next/server";

// Determine API base URL
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

const API_BASE_URL = getApiBaseUrl();

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { contact, type } = body;

    if (!contact) {
      return NextResponse.json(
        { error: "Contact (phone or email) is required" },
        { status: 400 }
      );
    }

    if (!type || (type !== "whatsapp" && type !== "email")) {
      return NextResponse.json(
        { error: "Type must be 'whatsapp' or 'email'" },
        { status: 400 }
      );
    }

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "X-GRYD-ENTERPRISE-ID": "autocrm",
      "X-GRYD-SIGNUP-TOKEN": "YXV0b2NybTE3NjI2MTAzOTUgMjY0NTI0",
    };

    const requestBody = {
      args: [contact, type],
      kwargs: {},
    };

    const backendUrl = `${API_BASE_URL}/generate_otp`;

    // Enhanced logging for debugging
    console.log("=".repeat(80));
    console.log("[Generate OTP] ===== REQUEST START =====");
    console.log(`[Generate OTP] API Base URL:`, API_BASE_URL);
    console.log(`[Generate OTP] Full Backend URL:`, backendUrl);
    console.log(`[Generate OTP] Method: POST`);
    console.log(`[Generate OTP] Headers:`, JSON.stringify(headers, null, 2));
    console.log(
      `[Generate OTP] Request Body:`,
      JSON.stringify(requestBody, null, 2)
    );
    console.log("[Generate OTP] ===== REQUEST END =====");
    console.log("=".repeat(80));

    const res = await fetch(backendUrl, {
      method: "POST",
      headers,
      body: JSON.stringify(requestBody),
      cache: "no-store",
    });

    // Enhanced response logging
    console.log("=".repeat(80));
    console.log("[Generate OTP] ===== RESPONSE START =====");
    console.log(`[Generate OTP] Backend URL Called:`, backendUrl);
    console.log(
      `[Generate OTP] Response Status: ${res.status} ${res.statusText}`
    );
    console.log(
      `[Generate OTP] Response Headers:`,
      JSON.stringify(Object.fromEntries(res.headers.entries()), null, 2)
    );

    // Clone response to read body without consuming it
    const responseClone = res.clone();
    const responseText = await responseClone.text();
    console.log(
      `[Generate OTP] Response Body:`,
      responseText.substring(0, 500)
    );
    console.log("[Generate OTP] ===== RESPONSE END =====");
    console.log("=".repeat(80));

    if (!res.ok) {
      let errorMessage = `Request failed (${res.status})`;
      try {
        const errorText = responseText;
        const errorData = JSON.parse(errorText);
        errorMessage =
          errorData?.error || errorData?.message || errorText || errorMessage;
      } catch {
        // Use default error message
      }

      const errorResponse = NextResponse.json(
        { error: errorMessage },
        { status: res.status }
      );
      // Add custom header to show backend URL in network tab
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
    console.error("Error in generate OTP proxy:", error);
    const errorMessage =
      error instanceof Error ? error.message : "Failed to generate OTP";
    return NextResponse.json({ error: errorMessage }, { status: 500 });
  }
}
