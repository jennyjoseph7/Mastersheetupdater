import { APP_BASE_URL, HEADERS } from "./headers";

async function fetchAPIData(modelName, queryParams = {}) {
  try {
    // Skip API calls if using localhost in production (static export)
    if (
      typeof window !== "undefined" &&
      APP_BASE_URL.includes("127.0.0.1") &&
      window.location.hostname !== "localhost"
    ) {
      console.warn("Skipping API call to localhost in production");
      return { items: [], total: 0 };
    }

    let url = new URL(`${APP_BASE_URL}/gryd/db/objects/${modelName}`);

    Object.entries(queryParams).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.append(key, value);
      }
    });

    const response = await fetch(url.toString(), {
      method: "GET",
      headers: HEADERS,
    });

    if (!response.ok) throw new Error("API request failed");

    const json = await response.json();

    return {
      items: json?.data ?? [],
      total: json?.total ?? 0,
    };
  } catch (error) {
    console.error("API fetch error:", error);
    return { items: [], total: 0 };
  }
}

async function fetchPivotCountForCampaign(type) {
  // Skip API calls if using localhost in production (static export)
  if (
    typeof window !== "undefined" &&
    APP_BASE_URL.includes("127.0.0.1") &&
    window.location.hostname !== "localhost"
  ) {
    console.warn("Skipping API call to localhost in production");
    return { pre_sales: 0, post_sales: 0 };
  }

  const base = `${APP_BASE_URL}/gryd/db/pivot`;

  let preUrl = "";
  let postUrl = "";
  if (type === "total") {
    preUrl = `${base}/pre_sales_campaign/campaign_id`;
    postUrl = `${base}/post_sales_campaign/campaign_id`;
  } else if (type === "active") {
    preUrl = `${base}/pre_sales_campaign/campaign_id?campaign_status=active`;
    postUrl = `${base}/post_sales_campaign/campaign_id?campaign_status=active`;
  }

  try {
    const [preRes, postRes] = await Promise.all([
      fetch(preUrl, { headers: HEADERS }),
      fetch(postUrl, { headers: HEADERS }),
    ]);

    const preJson = await preRes.json();
    const postJson = await postRes.json();

    return {
      pre_sales: preJson?.data?.campaign_id ?? 0,
      post_sales: postJson?.data?.campaign_id ?? 0,
    };
  } catch (err) {
    console.error("Pivot fetch error:", err);
    return { pre_sales: 0, post_sales: 0 };
  }
}

function epochToIST(epochTime) {
  if (!epochTime) return "";
  const date = new Date(epochTime * 1000);
  const options = {
    timeZone: "Asia/Kolkata",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  };

  let a = new Intl.DateTimeFormat("en-IN", options).format(date);
  return a.replaceAll("/", "-").replace(",", " ");
}

function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
}

export { fetchAPIData, fetchPivotCountForCampaign, epochToIST, capitalize };
