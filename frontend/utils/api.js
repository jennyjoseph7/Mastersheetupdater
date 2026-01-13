import {
  APP_BASE_URL,
  HEADERS,
  FILE_UPLOAD_URL,
  FILE_UPLOAD_HEADERS,
} from "./headers";
import { triggerGlobalLogout } from "@/lib/auth-context";

// --- Helper: Client-side Cookie Reader ---
const getCookie = (name) => {
  if (typeof document === "undefined") return null;
  const match = document.cookie.split("; ").find((row) => row.startsWith(name + "="));
  return match ? match.split("=")[1] : null;
};

// --- Helper: Secure Fetch (Auto-Logout on 401) ---
async function secureFetch(url, options = {}) {
  const response = await fetch(url, options);

  if (response.status === 401) {
    console.warn("[API] 401 Unauthorized detected. Triggering logout...");
    triggerGlobalLogout();
    // We throw/return here to stop further processing that might depend on data
    throw new Error("Session expired"); 
  }

  return response;
}

async function fetchAPIData(modelName, queryParams = {}) {
  try {
    let url = new URL(`${APP_BASE_URL}/gryd/db/objects/${modelName}`);
    Object.entries(queryParams).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.append(key, value);
      }
    });

    // Use secureFetch instead of fetch
    const response = await secureFetch(url.toString(), {
      method: "GET",
      headers: HEADERS,
    });

    if (!response.ok) throw new Error("API request failed");

    const json = await response.json();

    return {
      items: json?.data ?? [],
      total: json?.total ?? json?.total_number ?? 0,
    };
  } catch (error) {
    console.error("API fetch error:", error);
    return { items: [], total: 0 };
  }
}

async function deleteAPIData(modelName, id) {
  try {
    const url = `${APP_BASE_URL}/gryd/db/delete/${modelName}/${id}`;

    // Use secureFetch instead of fetch
    const response = await secureFetch(url, {
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
    // Use secureFetch instead of fetch
    const [preRes, postRes] = await Promise.all([
      secureFetch(preUrl, { headers: HEADERS }),
      secureFetch(postUrl, { headers: HEADERS }),
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

  // Note: File upload 401s should also trigger logout
  const response = await secureFetch(FILE_UPLOAD_URL, {
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
  const response = await secureFetch(
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

async function startImportTask(
  category,
  audienceName,
  fileUrl,
  tags = [],
  sourceName = "",
  fieldMapping = {},
  campaignIdOrObjectiveId = ""
) {
  // 1. Base kwargs
  const kwargs = {
    audience_name: audienceName,
    workshop_id: "ambal-auto - ambal-auto---service-center - coimbatore",
    source: "csv",
    tags: tags,
    source_name: sourceName || "Uploaded via csv",
    mapping: fieldMapping,
  };

  // 2. Determine which ID key to use
  if (campaignIdOrObjectiveId) {
    const isUuid =
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
        campaignIdOrObjectiveId
      );

    if (isUuid) {
      kwargs.campaign_id = campaignIdOrObjectiveId;
    } else {
      kwargs.campaign_objective_id = campaignIdOrObjectiveId;
    }
  }

  const response = await secureFetch(
    `${APP_BASE_URL}/gryd/task/autocrm-core/import_leads_from_csv`,
    {
      method: "POST",
      headers: HEADERS,
      body: JSON.stringify({
        args: [category || "post-sales", "ambal-auto-south-india", fileUrl],
        kwargs: kwargs,
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

// 6. Create Audience Task Record (DB) ---
async function createAudienceTask(taskData) {
  const response = await secureFetch(`${APP_BASE_URL}/gryd/db/object/audience_task`, {
    method: "POST",
    headers: HEADERS,
    body: JSON.stringify(taskData),
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`Failed to create audience task record: ${errorBody}`);
  }

  return response.json();
}

// --- 7. UPDATE Audience Task Record (DB) ---
async function updateAudienceTask(taskId, updateData) {
  const url = new URL(`${APP_BASE_URL}/gryd/db/object/audience_task/${taskId}`);

  const response = await secureFetch(url.toString(), {
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
  const response = await secureFetch(`${APP_BASE_URL}/gryd/status/${taskId}`, {
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
  const response = await secureFetch(`${APP_BASE_URL}/gryd/result/${taskId}`, {
    method: "GET",
    headers: HEADERS,
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch result: ${response.statusText}`);
  }
  updateAudienceTask(taskId, { fetched_result: true }).catch((err) =>
    console.error("Error updating fetched_result:", err)
  );
  return response.json();
}

//  Fetch Audience List (For Table) ---
async function fetchAudienceTasks(page = 1, pageSize = 50) {
  return fetchAPIData("audience_task", { 
    page_number: page, 
    page_size: pageSize 
  });
}
// --- NEW: Fetch Campaign Objectives ---
async function fetchCampaignObjectives(campaignType) {
  const type = campaignType ? campaignType.replace(/_/g, "-") : "";
  return fetchAPIData("campaign_objective", { campaign_type: type });
}

// Fetch Pre-Sales Campaigns ---
async function fetchPreSalesCampaigns(page = 1, pageSize = 50) {
  // Use client-side cookie helper instead of 'cookies().get' which is server-side
  let token = getCookie("gryd_token");
  let sessionId = getCookie("gryd_session_id");
  let applicationId = getCookie("gryd_application_id");

  // --- FALLBACK CHECK (Replaced hardcoded credentials with Logout) ---
  if (!token || !sessionId) {
    console.warn("[PreSales] Missing credentials. Triggering auto-logout...");
    triggerGlobalLogout();
    return { items: [], total: 0 }; // Exit gracefully while redirect happens
  }
  // ------------------------------------------------------------------

  try {
    const adminHeaders = {
      "Content-Type": "application/json",
      Accept: "application/json",
      "X-GRYD-ENTERPRISE-ID": "autocrm",
      "X-GRYD-TOKEN": token,
      "X-GRYD-SESSION-ID": sessionId,
      "X-GRYD-APPLICATION-ID": applicationId || "autocrm",
      "X-GRYD-ROLE": "admin",
    };

    const baseUrl = APP_BASE_URL;
    const url = `${baseUrl}/gryd/db/objects/pre_sales_campaign?page_number=${page}&page_size=${pageSize}`;

    let response = await secureFetch(url, {
      method: "GET",
      headers: adminHeaders,
    });

    if (!response.ok && response.status === 405) {
      response = await secureFetch(url, {
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
    return {
      items: json?.data ?? [],
      total: json?.total_number ?? 0,
    };
  } catch (error) {
    console.error("[fetchPreSalesCampaigns] Fetch error:", error);
    return { items: [], total: 0 };
  }
}

// Fetch Post-Sales Campaigns ---
async function fetchPostSalesCampaigns(dealershipId = null) {
  try {
    const finalDealershipId =
      dealershipId ||
      (typeof window !== "undefined"
        ? localStorage.getItem("dealership_id")
        : null);

    if (!finalDealershipId) {
      console.warn(
        "[fetchPostSalesCampaigns] No dealership_id provided or found in localStorage"
      );
      return { items: [], total: 0 };
    }

    const baseUrl = APP_BASE_URL;
    const url = `${baseUrl}/gryd/db/objects/post_sales_campaign?dealership_id=${encodeURIComponent(
      finalDealershipId
    )}`;

    let response = await secureFetch(url, {
      method: "GET",
      headers: HEADERS,
    });

    if (!response.ok && response.status === 405) {
      response = await secureFetch(url, {
        method: "POST",
        headers: HEADERS,
        body: "",
      });
    }

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API Error: ${response.status} ${errorText}`);
    }

    const json = await response.json();
    return {
      items: json?.data ?? [],
      total: json?.total_number ?? 0,
    };
  } catch (error) {
    console.error("[fetchPostSalesCampaigns] Fetch error:", error);
    return { items: [], total: 0 };
  }
}

// Fetch Dealership Campaigns ---
async function fetchDealershipCampaigns(page = 1, pageSize = 50) {
  // We should also ensure tokens exist here for consistency
  let token = getCookie("gryd_token");
  let sessionId = getCookie("gryd_session_id");
  let applicationId = getCookie("gryd_application_id");
  
  if (!token || !sessionId) {
    triggerGlobalLogout();
    return { items: [], total: 0 };
  }

  try {
    const adminHeaders = {
      "Content-Type": "application/json",
      Accept: "application/json",
      "X-GRYD-ENTERPRISE-ID": "autocrm",
      "X-GRYD-TOKEN": token,
      "X-GRYD-SESSION-ID": sessionId,
      "X-GRYD-APPLICATION-ID": applicationId || "autocrm",
      "X-GRYD-ROLE": "admin",
    };

    const baseUrl = APP_BASE_URL;
    const url = `${baseUrl}/gryd/db/objects/dealership_campaign`;

    let response = await secureFetch(url, {
      method: "GET",
      headers: adminHeaders,
    });

    if (!response.ok && response.status === 405) {
      response = await secureFetch(url, {
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
    return {
      items: json?.data ?? [],
      total: json?.total_number ?? 0,
    };
  } catch (error) {
    console.error("[fetchDealershipCampaigns] Fetch error:", error);
    return { items: [], total: 0 };
  }
}

// Fetch Overall Campaign Summary ---
async function fetchCampaignSummary(dealershipId = null) {
  try {
    let url = `${APP_BASE_URL}/gryd/db/objects/campaign_summary`;
    
    if (dealershipId) {
      url += `?dealership_id=${encodeURIComponent(dealershipId)}`;
    }

    const response = await secureFetch(url, {
      method: "GET",
      headers: HEADERS,
    });

    if (!response.ok && response.status === 405) {
      const retryResponse = await secureFetch(url, {
        method: "POST",
        headers: HEADERS,
        body: "",
      });
      if (!retryResponse.ok) {
        const errorText = await retryResponse.text();
        throw new Error(`API Error: ${retryResponse.status} ${errorText}`);
      }
      const json = await retryResponse.json();
      return json?.data ?? [];
    }

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API Error: ${response.status} ${errorText}`);
    }

    const json = await response.json();
    return json?.data ?? [];
  } catch (error) {
    console.error("[fetchCampaignSummary] Fetch error:", error);
    return [];
  }
}

// Fetch Campaign Performance Summary ---
async function fetchCampaignPerformanceSummary(campaignId) {
  try {
    const url = `${APP_BASE_URL}/gryd/db/objects/campaign_performance_summary${campaignId ? `?campaign_id=${campaignId}` : ''}`;

    const response = await secureFetch(url, {
      method: "GET",
      headers: HEADERS,
    });

    if (!response.ok && response.status === 405) {
      const retryResponse = await secureFetch(url, {
        method: "POST",
        headers: HEADERS,
        body: "",
      });
      if (!retryResponse.ok) {
        const errorText = await retryResponse.text();
        throw new Error(`API Error: ${retryResponse.status} ${errorText}`);
      }
      const json = await retryResponse.json();
      return json?.data ?? [];
    }

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API Error: ${response.status} ${errorText}`);
    }

    const json = await response.json();
    if (campaignId && json?.data) {
      return json.data.find((item) => item.campaign_id === campaignId) || null;
    }
    return json?.data ?? [];
  } catch (error) {
    console.error("[fetchCampaignPerformanceSummary] Fetch error:", error);
    return null;
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
  fetchPreSalesCampaigns,
  fetchPostSalesCampaigns,
  fetchDealershipCampaigns,
  fetchCampaignObjectives,
  fetchCampaignSummary,
  fetchCampaignPerformanceSummary,
  epochToIST,
  capitalize,
};