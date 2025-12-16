import {
  APP_BASE_URL,
  HEADERS,
  FILE_UPLOAD_URL,
  FILE_UPLOAD_HEADERS,
} from "./headers";

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
      // Handle both 'total' and 'total_number' based on your API response example
      total: json?.total ?? json?.total_number ?? 0, 
    };
  } catch (error) {
    console.error("API fetch error:", error);
    return { items: [], total: 0 };
  }
}

async function deleteAPIData(modelName, id) {
  try {
    // Assuming DELETE endpoint uses singular object path
    const url = `${APP_BASE_URL}/gryd/db/object/${modelName}/${id}`;
    
    const response = await fetch(url, {
      method: "DELETE",
      headers: HEADERS,
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Delete failed: ${text}`);
    }
    
    return true;
  } catch (error) {
    console.error("Delete error:", error);
    throw error;
  }
}

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

//  File Upload Service ---
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

// Extract CSV Headers Task ---
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
    },
  );

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`Header extraction failed: ${errorBody}`);
  }
  return response.json();
}

// Start Import Task ---
async function startImportTask(
  category,
  audienceName,
  fileUrl,
  tags = [],
  sourceName = "",
  fieldMapping = {},
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
    },
  );

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`Task start failed: ${errorBody}`);
  }

  return response.json();
}

// 6. Create Audience Task Record (DB) ---
async function createAudienceTask(taskData) {
  const response = await fetch(
    `${APP_BASE_URL}/gryd/db/object/audience_task`,
    {
      method: "POST",
      headers: HEADERS,
      body: JSON.stringify(taskData),
    },
  );

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`Failed to create audience task record: ${errorBody}`);
  }

  return response.json();
}

// --- 7. UPDATE Audience Task Record (DB) ---
async function updateAudienceTask(taskId, updateData) {
  const url = new URL(`${APP_BASE_URL}/gryd/db/object/audience_task/${taskId}`);

  const response = await fetch(url.toString(), {
    method: "PATCH", 
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

//  Fetch Audience List (For Table) ---
async function fetchAudienceTasks() {
  return fetchAPIData("audience_task");
}

// Fetch Dealership Campaigns ---
async function fetchDealershipCampaigns(page = 1, pageSize = 50) {
  try {
    const adminHeaders = {
      "Content-Type": "application/json",
      Accept: "application/json",
      "X-GRYD-ENTERPRISE-ID": "autocrm",
      "X-GRYD-TOKEN": "53014452-7df1-351c-9b79-af13d3d6b92f",
      "X-GRYD-SESSION-ID": "94b970d4-5c2b-3762-bf65-272901d0ad53",
      "X-GRYD-ROLE": "admin",
    };

    const baseUrl =
      typeof window !== "undefined" &&
      (window.location.hostname === "localhost" ||
        window.location.hostname === "127.0.0.1")
        ? "http://127.0.0.1:5008"
        : APP_BASE_URL;

    const url = `${baseUrl}/gryd/db/objects/dealership_campaign`;
    
    let response = await fetch(url, {
      method: "GET",
      headers: adminHeaders,
    });

    if (!response.ok && response.status === 405) {
      response = await fetch(url, {
        method: "POST",
        headers: adminHeaders,
        body: "", 
      });
    }

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API Error: ${response.status} ${errorText}`);
    }

    const json = await response.json();
    const items = json?.data ?? [];
    const total = json?.total_number ?? 0;

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
  deleteAPIData,
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