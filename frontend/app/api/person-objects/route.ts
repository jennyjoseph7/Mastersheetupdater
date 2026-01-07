import { NextResponse } from "next/server";

const getApiBaseUrl = () => {
  // Check for explicit environment variable override
  if (process.env.NEXT_PUBLIC_API_BASE_URL) {
    return process.env.NEXT_PUBLIC_API_BASE_URL;
  }

  // Always use production URL
  return "https://autobot-webapp-dev.gryd.in";
};

export const API_BASE_URL = getApiBaseUrl();
export async function GET() {
  try {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      Accept: "application/json",
      "X-GRYD-ENTERPRISE-ID": "autocrm",
      "X-GRYD-TOKEN": "53014452-7df1-351c-9b79-af13d3d6b92f",
      "X-GRYD-SESSION-ID": "94b970d4-5c2b-3762-bf65-272901d0ad53",
      "X-GRYD-ROLE": "admin",
      Origin: API_BASE_URL, // Set origin to match the API base URL
    };

    const res = await fetch(`${API_BASE_URL}/gryd/db/objects/person`, {
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
    console.error("Error fetching person objects:", error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to fetch person objects" },
      { status: 500 }
    );
  }
}

