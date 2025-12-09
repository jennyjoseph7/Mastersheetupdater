import { NextResponse } from "next/server";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:5008";

export async function GET() {
  try {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      Accept: "application/json",
      "X-GRYD-ENTERPRISE-ID": "autocrm",
      "X-GRYD-TOKEN": "53014452-7df1-351c-9b79-af13d3d6b92f",
      "X-GRYD-SESSION-ID": "94b970d4-5c2b-3762-bf65-272901d0ad53",
      "X-GRYD-ROLE": "admin",
    };

    const res = await fetch(`${API_BASE_URL}/gryd/db/objects/audience_task`, {
      method: "GET",
      headers,
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
