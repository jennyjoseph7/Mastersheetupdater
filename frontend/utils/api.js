import {
  APP_BASE_URL,
  HEADERS,
  cookies,
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
    const url = `${APP_BASE_URL}/gryd/db/delete/${modelName}/${id}`;

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
    }
  );

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`Header extraction failed: ${errorBody}`);
  }
  return response.json();
}

// Start Import Task ---
// async function startImportTask(
//   category,
//   audienceName,
//   fileUrl,
//   tags = [],
//   sourceName = "",
//   fieldMapping = {},
//   campaignObjectiveId = ""
// ) {
//   const response = await fetch(
//     `${APP_BASE_URL}/gryd/task/autocrm-core/import_leads_from_csv`,
//     {
//       method: "POST",
//       headers: HEADERS,
//       body: JSON.stringify({
//         args: [category || "post-sales", "ambal-auto-south-india", fileUrl],
//         kwargs: {
//           // campaign_id: campaignObjectiveId, // <--- Passing the selected objective ID to the task
//           campaign_objective_id: campaignObjectiveId, // <--- Also passing here for clarity if backend expects specific key
//           audience_name: audienceName,
//           // campaign_name: audienceName,
//           workshop_id: "ambal-auto - ambal-auto---service-center - coimbatore",
//           source: "csv",
//           tags: tags,
//           source_name: sourceName || "Uploaded via csv",
//           mapping: fieldMapping,
//         },
//         runtime_limit: 3600,
//         cancellable: true,
//       }),
//     },
//   );

//   if (!response.ok) {
//     const errorBody = await response.text();
//     throw new Error(`Task start failed: ${errorBody}`);
//   }

//   return response.json();
// }
async function startImportTask(
  category,
  audienceName,
  fileUrl,
  tags = [],
  sourceName = "",
  fieldMapping = {},
  campaignIdOrObjectiveId = "" // Accepts either ID
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
    // Check if UUID (Campaign ID)
    const isUuid =
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
        campaignIdOrObjectiveId
      );

    if (isUuid) {
      kwargs.campaign_id = campaignIdOrObjectiveId;
    } else {
      // Assume slug (Campaign Objective ID)
      kwargs.campaign_objective_id = campaignIdOrObjectiveId;
    }
  }

  const response = await fetch(
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
  const response = await fetch(`${APP_BASE_URL}/gryd/db/object/audience_task`, {
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
  updateAudienceTask(taskId, { fetched_result: true }).catch((err) =>
    console.error("Error updating fetched_result:", err)
  );
  return response.json();
}

//  Fetch Audience List (For Table) ---
async function fetchAudienceTasks() {
  return fetchAPIData("audience_task");
}

// --- NEW: Fetch Campaign Objectives ---
async function fetchCampaignObjectives(campaignType) {
  // Convert 'pre_sales' to 'pre-sales' to match API expectation
  const type = campaignType ? campaignType.replace(/_/g, "-") : "";
  return fetchAPIData("campaign_objective", { campaign_type: type });
}

// Fetch Pre-Sales Campaigns ---
async function fetchPreSalesCampaigns(page = 1, pageSize = 50) {
     // Get credentials from cookies (set during login)
      let token = cookies().get("gryd_token")?.value;
      let sessionId = cookies().get("gryd_session_id")?.value;
  
      // Fallback to hardcoded credentials if user credentials not available
      // These match the curl that works successfully
      if (!token || !sessionId) {
        console.log("[Create Workshop API] Using fallback hardcoded credentials");
        token = "53014452-7df1-351c-9b79-af13d3d6b92f";
        sessionId = "94b970d4-5c2b-3762-bf65-272901d0ad53";
      } else {
        console.log("[Create Workshop API] Using user credentials from cookies");
      }
  try {
    const adminHeaders = {
      "Content-Type": "application/json",
      Accept: "application/json",
      "X-GRYD-ENTERPRISE-ID": "autocrm",
      "X-GRYD-TOKEN": token,
      "X-GRYD-SESSION-ID": sessionId,
      "X-GRYD-APPLICATION-ID": application_id || "autocrm",
      "X-GRYD-ROLE": "admin",
    };

    const baseUrl = APP_BASE_URL;

    const url = `${baseUrl}/gryd/db/objects/pre_sales_campaign?page_number=${page}&page_size=${pageSize}`;

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
    console.error("[fetchPreSalesCampaigns] Fetch error:", error);
    return { items: [], total: 0 };
  }
}

// Fetch Post-Sales Campaigns ---
async function fetchPostSalesCampaigns(dealershipId = null) {
  try {
    // Get dealership_id from parameter or localStorage
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
    const url = `${baseUrl}/gryd/db/objects/post_sales_campaign?dealership_id=${encodeURIComponent(finalDealershipId)}`;

    let response = await fetch(url, {
      method: "GET",
      headers: HEADERS,
    });

    if (!response.ok && response.status === 405) {
      response = await fetch(url, {
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
    const items = json?.data ?? [];
    const total = json?.total_number ?? 0;

    return {
      items,
      total,
    };
  } catch (error) {
    console.error("[fetchPostSalesCampaigns] Fetch error:", error);
    return { items: [], total: 0 };
  }
}

// Fetch Dealership Campaigns ---
async function fetchDealershipCampaigns(page = 1, pageSize = 50) {
  try {
    const adminHeaders = {
      "Content-Type": "application/json",
      Accept: "application/json",
      "X-GRYD-ENTERPRISE-ID": "autocrm",
      "X-GRYD-TOKEN": token,
      "X-GRYD-SESSION-ID": sessionId,
      "X-GRYD-APPLICATION-ID": application_id || "autocrm",
      "X-GRYD-ROLE": "admin",
    };

    const baseUrl = APP_BASE_URL;

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

// Fetch Overall Campaign Summary ---
async function fetchCampaignSummary(dealershipId = null) {
  try {
    let url = `${APP_BASE_URL}/gryd/db/objects/campaign_summary`;
    
    // Add dealership_id query parameter if provided
    if (dealershipId) {
      url += `?dealership_id=${encodeURIComponent(dealershipId)}`;
    }

    const response = await fetch(url, {
      method: "GET",
      headers: HEADERS,
    });

    if (!response.ok && response.status === 405) {
      const retryResponse = await fetch(url, {
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

    const response = await fetch(url, {
      method: "GET",
      headers: HEADERS,
    });

    if (!response.ok && response.status === 405) {
      const retryResponse = await fetch(url, {
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
    // If campaignId is provided, return the matching campaign, otherwise return all
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
