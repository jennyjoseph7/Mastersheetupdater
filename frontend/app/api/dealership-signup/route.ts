import { NextResponse } from "next/server";

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

export async function POST(request: Request) {
  try {
    const body = await request.json();

    // Log the request body for debugging
    console.log(
      `[Dealership Signup] Request body:`,
      JSON.stringify(body, null, 2)
    );
    console.log(`[Dealership Signup] API Base URL:`, API_BASE_URL);
    const backendUrl = `${API_BASE_URL}/dealership_signup`;
    console.log(`[Dealership Signup] Full URL:`, backendUrl);

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "X-GRYD-ENTERPRISE-ID": "autocrm",
      "X-GRYD-SIGNUP-TOKEN": "YXV0b2NybTE3NjI2MTAzOTUgMjY0NTI0",
    };

    const res = await fetch(backendUrl, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      cache: "no-store",
    });

    // Log response status for debugging
    console.log(`[Dealership Signup] Backend response status: ${res.status}`);

    if (!res.ok) {
      let errorMessage = `Request failed (${res.status})`;
      let errorData: any = null;

      try {
        const contentType = res.headers.get("content-type");
        const errorText = await res.text();

        console.log(
          `[Dealership Signup] Error response content-type: ${contentType}`
        );
        console.log(
          `[Dealership Signup] Error response body: ${errorText.substring(
            0,
            500
          )}`
        );

        // Try to parse JSON error response
        if (errorText && errorText.trim()) {
          try {
            errorData = JSON.parse(errorText);

            // Extract error message from various possible formats
            if (errorData && typeof errorData === "object") {
              if (errorData.error) {
                errorMessage = String(errorData.error);
              } else if (errorData.message) {
                errorMessage = String(errorData.message);
              } else if (errorData.detail) {
                errorMessage = String(errorData.detail);
              } else {
                // If it's an object but no standard error field, try to extract useful info
                const errorStr = JSON.stringify(errorData);
                // Check if it contains the Python error message
                if (
                  errorStr.includes("'NoneType' object has no attribute 'get'")
                ) {
                  // This is a backend bug - try to extract the original error if available
                  errorMessage =
                    "An error occurred while processing your request. Please check if the dealership already exists or try again.";
                } else {
                  errorMessage = errorStr;
                }
              }
            } else if (typeof errorData === "string") {
              errorMessage = errorData;
            }
          } catch (parseError) {
            // Not JSON, use errorText as is
            console.log(
              `[Dealership Signup] Error response is not JSON, using raw text`
            );
            errorMessage = errorText || errorMessage;
          }
        } else {
          console.log(`[Dealership Signup] Empty error response body`);
        }
      } catch (readError) {
        // Failed to read response, use default message
        console.error(
          "[Dealership Signup] Failed to read error response:",
          readError
        );
        errorMessage = `Request failed (${res.status})`;
      }

      // Clean up any "API Error:" prefixes
      errorMessage = errorMessage.replace(/^API Error:\s*\d*\s*/gi, "").trim();

      // Handle Python traceback errors - replace with user-friendly message
      if (errorMessage.includes("'NoneType' object has no attribute 'get'")) {
        errorMessage =
          "An error occurred while processing your request. The dealership may already exist or there was a server error. Please try again.";
      }

      // If message is empty after cleanup, use a default
      if (!errorMessage || errorMessage === "") {
        errorMessage = `Request failed (${res.status})`;
      }

      console.log(`[Dealership Signup] Returning error: ${errorMessage}`);

      return NextResponse.json({ error: errorMessage }, { status: res.status });
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error in dealership signup proxy:", error);

    // Handle different error types
    let errorMessage = "Failed to process dealership signup";

    if (error instanceof Error) {
      errorMessage = error.message;
      // Clean up any technical error messages
      if (errorMessage.includes("'NoneType' object has no attribute 'get'")) {
        errorMessage =
          "An error occurred while processing your request. Please try again.";
      }
    }

    return NextResponse.json({ error: errorMessage }, { status: 500 });
  }
}
