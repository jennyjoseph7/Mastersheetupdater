// Use environment variable or fallback to production API
const APP_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "https://autobot-webapp-dev.gryd.in";
const HEADERS = {
  "Content-Type": "application/json",
  "X-GRYD-ENTERPRISE-ID": "autocrm",
  "X-GRYD-TOKEN": "53014452-7df1-351c-9b79-af13d3d6b92f",
  "X-GRYD-SESSION-ID": "94b970d4-5c2b-3762-bf65-272901d0ad53",
  "X-GRYD-ROLE": "agent",
};

export { APP_BASE_URL, HEADERS };
