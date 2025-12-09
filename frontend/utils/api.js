import { APP_BASE_URL, HEADERS, FILE_UPLOAD_URL, FILE_UPLOAD_HEADERS } from "./headers";

// ... [Existing fetchAPIData and fetchPivotCountForCampaign remain unchanged] ...

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

// --- File Upload & Import Flow ---

// 1. Upload File
async function uploadFileToGryd(file) {
    const uploadData = new FormData();
    uploadData.append("file", file);

    const response = await fetch(FILE_UPLOAD_URL, {
        method: "POST",
        headers: FILE_UPLOAD_HEADERS,
        body: uploadData,
    });

    if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
    }
    return response.json();
}

// 2. NEW: Extract CSV Headers
async function extractCsvHeadersAPI(fileUrl) {
    const response = await fetch(
        `${APP_BASE_URL}/gryd/task/autocrm-core/extract_csv_headers`,
        {
            method: "POST",
            headers: HEADERS,
            body: JSON.stringify({
                args: [fileUrl], // Assuming it takes the URL as the first arg
                kwargs: {},
                 cancellable: true,
            }),
        }
    );

    if (!response.ok) {
        const errorBody = await response.text();
        throw new Error(`Header extraction failed: ${errorBody}`);
    }
    return response.json();
}

// 3. Start Import Task (Updated to accept mapping)
async function startImportTask(category, audienceName, fileUrl, tags = [], sourceName = "", fieldMapping = {}) {
    const response = await fetch(
        `${APP_BASE_URL}/gryd/task/autocrm-core/import_leads_from_csv`,
        {
            method: "POST",
            headers: HEADERS,
            body: JSON.stringify({
                args: [
                    category || "post-sales", 
                    audienceName || "default-audience", 
                    fileUrl
                ],
                kwargs: {
                    campaign_id: "74f260b8-e8dc-3c52-ab8d-31bd0fc49943",
                     workshop_id: "ambal-auto - ambal-auto---service-center - coimbatore",
                    source: "csv",
                    tags: tags,
                    source_name: sourceName || "Uploaded via csv",
                    field_mapping: fieldMapping // Pass the mapping here
                },
                runtime_limit: 3600,
                cancellable: true,
            }),
        }
    );

    if (!response.ok) {
        const errorBody = await response.text();
        throw new Error(`Task start failed: ${errorBody}`);
    }

    return response.json();
}

// 4. Get Status
async function getTaskStatus(taskId) {
    const response = await fetch(`${APP_BASE_URL}/gryd/status/${taskId}`, {
        method: "GET",
        headers: HEADERS,
    });
    if (!response.ok) throw new Error(`Status check failed: ${response.statusText}`);
    return response.json();
}

// 5. Get Result
async function getTaskResult(taskId) {
    const response = await fetch(`${APP_BASE_URL}/gryd/result/${taskId}`, {
        method: "GET",
        headers: HEADERS,
    });
    if (!response.ok) throw new Error(`Failed to fetch result: ${response.statusText}`);
    return response.json();
}

// ... [Existing Helpers] ...
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

export { 
    fetchAPIData, 
    fetchPivotCountForCampaign, 
    uploadFileToGryd, 
    extractCsvHeadersAPI, // New
    startImportTask, 
    getTaskStatus, 
    getTaskResult,
    epochToIST, 
    capitalize 
};