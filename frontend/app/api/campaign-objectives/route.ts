import { NextResponse } from "next/server";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "https://autobot-webapp-dev.gryd.in";

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

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      Accept: "application/json",
      "X-GRYD-ENTERPRISE-ID": "autocrm",
      "X-GRYD-TOKEN": "53014452-7df1-351c-9b79-af13d3d6b92f",
      "X-GRYD-SESSION-ID": "94b970d4-5c2b-3762-bf65-272901d0ad53",
      "X-GRYD-ROLE": "admin",
    };

    const url = `${API_BASE_URL}/gryd/db/objects/campaign_objective?campaign_type=${campaignType}`;
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
