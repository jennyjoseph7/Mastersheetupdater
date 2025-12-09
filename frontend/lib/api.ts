export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:5008";

interface ApiOptions {
  method?: string;
  headers?: Record<string, string>;
  body?: any;
}

export async function api(
  endpoint: string,
  method: string = "GET",
  body?: any,
  customHeaders: Record<string, string> = {},
) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
    "X-GRYD-ENTERPRISE-ID": "autocrm",
    "X-GRYD-TOKEN": "53014452-7df1-351c-9b79-af13d3d6b92f",
    "X-GRYD-SESSION-ID": "94b970d4-5c2b-3762-bf65-272901d0ad53",
    "X-GRYD-ROLE": "agent",
    ...customHeaders,
  };
  const res = await fetch(`${API_BASE_URL}${endpoint}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`API Error: ${res.status} ${errorText}`);
  }
  return res.json();
}

// Fetch person objects from the API
// or the the added audience for
export async function fetchPersonObjects() {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
    "X-GRYD-ENTERPRISE-ID": "autocrm",
    "X-GRYD-TOKEN": "53014452-7df1-351c-9b79-af13d3d6b92f",
    "X-GRYD-SESSION-ID": "94b970d4-5c2b-3762-bf65-272901d0ad53",
    "X-GRYD-ROLE": "admin",
  };

  const res = await fetch(`${API_BASE_URL}/gryd/db/objects/person`, {
    method: "GET",
    headers,
    cache: "no-store",
  });

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`API Error: ${res.status} ${errorText}`);
  }

  return res.json();
}
