import { NextResponse } from "next/server";

// Use local backend for generate OTP endpoint
const API_BASE_URL = "http://127.0.0.1:5008";

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
      Accept: "application/json",
      "X-GRYD-ENTERPRISE-ID": "autocrm",
      "X-GRYD-TOKEN": "53014452-7df1-351c-9b79-af13d3d6b92f",
      "X-GRYD-SESSION-ID": "94b970d4-5c2b-3762-bf65-272901d0ad53",
      "X-GRYD-ROLE": "agent",
    };

    const requestBody = {
      args: [contact, type],
    };

    const res = await fetch(
      `${API_BASE_URL}/gryd/api/autocrm-core/generate_otp`,
      {
        method: "POST",
        headers,
        body: JSON.stringify(requestBody),
        cache: "no-store",
      }
    );

    if (!res.ok) {
      let errorMessage = `Request failed (${res.status})`;
      try {
        const errorText = await res.text();
        const errorData = JSON.parse(errorText);
        errorMessage =
          errorData?.error || errorData?.message || errorText || errorMessage;
      } catch {
        // Use default error message
      }

      return NextResponse.json({ error: errorMessage }, { status: res.status });
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error in generate OTP proxy:", error);
    const errorMessage =
      error instanceof Error ? error.message : "Failed to generate OTP";
    return NextResponse.json({ error: errorMessage }, { status: 500 });
  }
}
