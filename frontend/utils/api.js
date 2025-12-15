// utils/api.js
import {
  APP_BASE_URL,
  HEADERS,
  FILE_UPLOAD_URL,
  FILE_UPLOAD_HEADERS,
} from "./headers";

// --- 1. Generic Fetch Wrapper ---
async function fetchAPIData(modelName, queryParams = {}) {
  try {
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

// --- 2. Campaign Pivot Logic ---
async function fetchPivotCountForCampaign(type) {
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
    return 0;
  }
}

// --- 3. File Upload Service ---
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

// --- 4. Extract CSV Headers Task ---
async function extractCsvHeadersAPI(fileUrl) {
  const response = await fetch(
    `${APP_BASE_URL}/gryd/task/autocrm-core/extract_csv_headers`,
    {
      method: "POST",
      headers: HEADERS,
      body: JSON.stringify({
        args: [fileUrl],
        kwargs: {},
      }),
    }
  );

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`Header extraction failed: ${errorBody}`);
  }
  return response.json();
}

// --- 5. Start Import Task ---
async function startImportTask(
  category,
  audienceName,
  fileUrl,
  tags = [],
  sourceName = "",
  fieldMapping = {}
) {
  const response = await fetch(
    `${APP_BASE_URL}/gryd/task/autocrm-core/import_leads_from_csv`,
    {
      method: "POST",
      headers: HEADERS,
      body: JSON.stringify({
        args: [category || "post-sales", "ambal-auto-south-india", fileUrl],
        kwargs: {
          campaign_id: "626952a0-1ac7-3a7c-85aa-c46d30897ea4",
          campaign_objective_id: "626952a0-1ac7-3a7c-85aa-c46d30897ea4",
          workshop_id: "ambal-auto - ambal-auto---service-center - coimbatore",
          source: "csv",
          tags: tags,
          source_name: sourceName || "Uploaded via csv",
          mapping: fieldMapping,
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

// --- 6. Create Audience Task Record (DB) ---
async function createAudienceTask(taskData) {
  const response = await fetch(
    `${APP_BASE_URL}/gryd/db/objects/audience_task`,
    {
      method: "PUT",
      headers: HEADERS,
      body: JSON.stringify(taskData),
    }
  );

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`Failed to create audience task record: ${errorBody}`);
  }

  return response.json();
}

// --- 7. UPDATE Audience Task Record (DB) ---
async function updateAudienceTask(taskId, updateData) {
  // FIX: Using query param ?task_id=... as requested
  const url = new URL(`${APP_BASE_URL}/gryd/db/objects/audience_task`);
  url.searchParams.append("task_id", taskId);

  const response = await fetch(url.toString(), {
    method: "POST", // Using PUT as per screenshot
    headers: HEADERS,
    body: JSON.stringify(updateData),
  });

  if (!response.ok) {
    const errorBody = await response.text();
    console.error(`Failed to update audience task ${taskId}:`, errorBody);
  }
  return response.json();
}

// --- 8. Poll Task Status ---
async function getTaskStatus(taskId) {
  const response = await fetch(`${APP_BASE_URL}/gryd/status/${taskId}`, {
    method: "GET",
    headers: HEADERS,
  });

  if (!response.ok) {
    throw new Error(`Status check failed: ${response.statusText}`);
  }

  return response.json();
}

// --- 9. Get Task Result ---
async function getTaskResult(taskId) {
  const response = await fetch(`${APP_BASE_URL}/gryd/result/${taskId}`, {
    method: "GET",
    headers: HEADERS,
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch result: ${response.statusText}`);
  }

  return response.json();
}

// --- 10. Fetch Audience List (For Table) ---
async function fetchAudienceTasks() {
  return fetchAPIData("audience_task");
}

// --- 11. Fetch Dealership Campaigns ---
async function fetchDealershipCampaigns(page = 1, pageSize = 50) {
  try {
    // Use admin role header as per the curl command
    const adminHeaders = {
      "Content-Type": "application/json",
      Accept: "application/json",
      "X-GRYD-ENTERPRISE-ID": "autocrm",
      "X-GRYD-TOKEN": "53014452-7df1-351c-9b79-af13d3d6b92f",
      "X-GRYD-SESSION-ID": "94b970d4-5c2b-3762-bf65-272901d0ad53",
      "X-GRYD-ROLE": "admin",
    };

    // Use 127.0.0.1:5008 directly to match the curl command exactly
    const baseUrl =
      typeof window !== "undefined" &&
      (window.location.hostname === "localhost" ||
        window.location.hostname === "127.0.0.1")
        ? "http://127.0.0.1:5008"
        : APP_BASE_URL;

    const url = `${baseUrl}/gryd/db/objects/dealership_campaign`;
    console.log("[fetchDealershipCampaigns] Fetching from:", url);
    console.log("[fetchDealershipCampaigns] Headers:", adminHeaders);

    // Try GET first (like other db/objects endpoints work)
    let response = await fetch(url, {
      method: "GET",
      headers: adminHeaders,
    });

    console.log(
      "[fetchDealershipCampaigns] GET Response status:",
      response.status
    );

    // If GET returns 405 (Method Not Allowed), use POST as per curl command
    if (!response.ok && response.status === 405) {
      console.log(
        "[fetchDealershipCampaigns] GET not allowed, using POST as per curl..."
      );
      response = await fetch(url, {
        method: "POST",
        headers: adminHeaders,
        body: "", // Empty string as per curl command --data ''
      });
      console.log(
        "[fetchDealershipCampaigns] POST Response status:",
        response.status
      );
    }

    if (!response.ok) {
      const errorText = await response.text();
      console.error("[fetchDealershipCampaigns] Error response:", errorText);
      throw new Error(`API Error: ${response.status} ${errorText}`);
    }

    const json = await response.json();
    console.log("[fetchDealershipCampaigns] Response data:", json);

    // Response format: { data: [], total_number: 2, page_number: 1, page_size: 50, ... }
    const items = json?.data ?? [];
    const total = json?.total_number ?? 0;

    console.log(
      `[fetchDealershipCampaigns] Returning ${items.length} items, total: ${total}`
    );

    return {
      items,
      total,
    };
  } catch (error) {
    console.error("[fetchDealershipCampaigns] Fetch error:", error);
    return { items: [], total: 0 };
  }
}

// --- Helpers ---
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
  if (!str) return "";
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
}

export {
  fetchAPIData,
  fetchPivotCountForCampaign,
  uploadFileToGryd,
  extractCsvHeadersAPI,
  startImportTask,
  createAudienceTask,
  updateAudienceTask,
  getTaskStatus,
  getTaskResult,
  fetchAudienceTasks,
  fetchDealershipCampaigns,
  epochToIST,
  capitalize,
};
