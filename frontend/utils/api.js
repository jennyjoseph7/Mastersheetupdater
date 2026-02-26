"use client";

import {
  APP_BASE_URL,
  authenticatedFetch,
  FILE_UPLOAD_URL,
  FILE_UPLOAD_HEADERS,
} from "./headers";

/* ---------------------------------------------------
   Utils (Next.js Safe)
--------------------------------------------------- */

function getDealershipId() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("dealership_id");
}

function epochToIST(epochTime) {
  if (!epochTime) return "";
  return new Date(epochTime * 1000).toLocaleString("en-IN", {
    timeZone: "Asia/Kolkata",
  });
}

function capitalize(str) {
  return str ? str.charAt(0).toUpperCase() + str.slice(1).toLowerCase() : "";
}

/* ---------------------------------------------------
   Generic Fetch Helpers
--------------------------------------------------- */

async function fetchAPIData(modelName, queryParams = {}) {
  try {
    const url = new URL(`${APP_BASE_URL}/gryd/db/objects/${modelName}`);

    Object.entries(queryParams).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.append(key, value);
      }
    });

    const response = await authenticatedFetch(url.toString(), {
      method: "GET",
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
  const url = `${APP_BASE_URL}/gryd/db/delete/${modelName}/${id}`;
  const response = await authenticatedFetch(url, { method: "DELETE" });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Delete failed: ${text}`);
  }
  return true;
}

/* ---------------------------------------------------
   Brand Fetcher
--------------------------------------------------- */

async function getBrands(regionId) {
  if (!regionId) return [];
  const { items } = await fetchAPIData("brand", { region_id: regionId });
  return items;
}

/* ---------------------------------------------------
   Pivot / Counts
--------------------------------------------------- */

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
      authenticatedFetch(preUrl),
      authenticatedFetch(postUrl),
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

/* ---------------------------------------------------
   File Upload
--------------------------------------------------- */

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

/* ---------------------------------------------------
   CSV / Import Tasks
--------------------------------------------------- */

async function extractCsvHeadersAPI(fileUrl) {
  const response = await authenticatedFetch(
    `${APP_BASE_URL}/gryd/task/autocrm-core/extract_csv_headers`,
    {
      method: "POST",
      body: JSON.stringify({
        args: [fileUrl],
        kwargs: {},
        runtime_limit: 3600,
        cancellable: true,
      }),
    }
  );

  if (!response.ok) {
    throw new Error(await response.text());
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
  campaignIdOrObjectiveId = "",
  dealershipId = getDealershipId()
) {
  const kwargs = {
    audience_name: audienceName,
    // workshop_id: dealershipId,
    source: "csv",
    tags,
    source_name: sourceName || "Uploaded via csv",
    mapping: fieldMapping,
  };

  if (campaignIdOrObjectiveId) {
    const isUuid =
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
        campaignIdOrObjectiveId
      );

    if (isUuid) kwargs.campaign_id = campaignIdOrObjectiveId;
    else kwargs.campaign_objective_id = campaignIdOrObjectiveId;
  }

  const response = await authenticatedFetch(
    `${APP_BASE_URL}/gryd/task/autocrm-core/import_leads_from_csv`,
    {
      method: "POST",
      body: JSON.stringify({
        args: [category || "post-sales", getDealershipId(), fileUrl],
        kwargs,
        runtime_limit: 3600,
        cancellable: true,
      }),
    }
  );

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return response.json();
}

/* ---------------------------------------------------
   Audience Tasks
--------------------------------------------------- */

async function createAudienceTask(taskData) {
  const response = await authenticatedFetch(
    `${APP_BASE_URL}/gryd/db/object/audience_task`,
    {
      method: "POST",
      body: JSON.stringify(taskData),
    }
  );

  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

async function updateAudienceTask(taskId, updateData) {
  const response = await authenticatedFetch(
    `${APP_BASE_URL}/gryd/db/object/audience_task/${taskId}`,
    {
      method: "PATCH",
      body: JSON.stringify(updateData),
    }
  );

  return response.json();
}

async function getTaskStatus(taskId) {
  const response = await authenticatedFetch(
    `${APP_BASE_URL}/gryd/status/${taskId}`
  );
  return response.json();
}

async function getTaskResult(taskId) {
  const response = await authenticatedFetch(
    `${APP_BASE_URL}/gryd/result/${taskId}`
  );

  updateAudienceTask(taskId, { fetched_result: true }).catch(console.error);
  return response.json();
}

/* ---------------------------------------------------
   Campaign Fetchers
--------------------------------------------------- */

// In utils/api.ts or api.js

export async function fetchPreSalesCampaigns(
  page = 1,
  pageSize = 50,
  dealershipId = getDealershipId()
) {
  // Ensure dealershipId is passed correctly if page/pageSize are provided
  const dId = dealershipId || getDealershipId();
  
  const response = await authenticatedFetch(
    `${APP_BASE_URL}/gryd/db/objects/pre_sales_campaign?page_number=${page}&page_size=${pageSize}&dealership_id=${encodeURIComponent(
      dId
    )}&sort_by=created&sort_reverse=true`,
    { headers: { "X-GRYD-ROLE": "admin" } }
  );

  const json = await response.json();
  return { items: json?.data ?? [], total: json?.total_number ?? 0 };
}

export async function fetchPostSalesCampaigns(
  page = 1,
  pageSize = 50,
  dealershipId = getDealershipId()
) {
  // Ensure dealershipId is passed correctly
  const dId = dealershipId || getDealershipId();
  if (!dId) return { items: [], total: 0 };

  const response = await authenticatedFetch(
    `${APP_BASE_URL}/gryd/db/objects/post_sales_campaign?page_number=${page}&page_size=${pageSize}&dealership_id=${encodeURIComponent(
      dId
    )}&sort_by=created&sort_reverse=true`
  );

  const json = await response.json();
  return { items: json?.data ?? [], total: json?.total_number ?? 0 };
}

async function fetchCampaignObjectives(campaignType) {
  return fetchAPIData("campaign_objective", {
    campaign_type: campaignType?.replace(/_/g, "-"),
    sort_by: "created",
    sort_reverse: true,
  });
}

async function fetchCampaignSummary(dealershipId = getDealershipId()) {
  console.log("Fetching campaign summary for dealership ID:", dealershipId);
  if (!dealershipId) return { items: [], total: 0 };

  const response = await authenticatedFetch(
    `${APP_BASE_URL}/gryd/db/objects/campaign_summary?dealership_id=${encodeURIComponent(
      dealershipId
    )}`
  );
  // const response = await authenticatedFetch(url);
  const json = await response.json();
  return json?.data ?? [];
}

async function fetchAudienceTasks(page = 1, pageSize = 50) {
  return fetchAPIData("audience_task", {
    dealership_id: getDealershipId(),
    page_number: page,
    page_size: pageSize,
    sort_by: "created",
    sort_reverse: true,
  });
}

async function fetchDealershipCampaigns(page = 1, pageSize = 50) {
  try {
    const response = await authenticatedFetch(
      `${APP_BASE_URL}/gryd/db/objects/dealership_campaign?page_number=${page}&page_size=${pageSize}`,
      { headers: { "X-GRYD-ROLE": "admin" } }
    );

    const json = await response.json();
    return { items: json?.data ?? [], total: json?.total_number ?? 0 };
  } catch (error) {
    console.error("[fetchDealershipCampaigns] Fetch error:", error);
    return { items: [], total: 0 };
  }
}

async function fetchCampaignPerformanceSummary(campaignId = "") {
  try {
    const url = `${APP_BASE_URL}/gryd/db/objects/campaign_performance_summary${
      campaignId ? `?campaign_id=${encodeURIComponent(campaignId)}` : ""
    }`;

    const response = await authenticatedFetch(url);
    if (!response.ok) throw new Error(await response.text());

    const json = await response.json();

    if (campaignId && Array.isArray(json?.data)) {
      return json.data.find((i) => i.campaign_id === campaignId) || null;
    }

    return json?.data ?? [];
  } catch (error) {
    console.error("[fetchCampaignPerformanceSummary]", error);
    return null;
  }
}

async function fetchCampaignLeads({
  campaignId = "",
  campaignType = "", // Expected: "pre-sales" or "post-sales"
  dealershipId = getDealershipId(),
  page_number = 1,
  page_size = 10,
  search = "",
  sort_by = "",
  sort_dir = "asc",
  disposition = "", // New filter parameter
} = {}) {
  // We now require campaignType to avoid making dual API calls
  if (!campaignId || !dealershipId || !campaignType) {
    console.warn("[fetchCampaignLeads] Missing required params:", { campaignId, campaignType });
    return { items: [], total_number: 0 };
  }

  try {
    // Dynamically set the endpoint based on the campaign type
    // Converts "pre-sales" to "pre_sales_lead" and "post-sales" to "post_sales_lead"
    const endpointType = campaignType.replace("-", "_");
    const endpoint = `${endpointType}_lead`;

    // Construct Query Parameters
    const params = new URLSearchParams({
      dealership_id: dealershipId,
      campaign_id: campaignId,
      page_number: String(page_number),
      page_size: String(page_size),
    });

    if (search) {
      params.append("search", search); 
    }

    if (sort_by) {
      params.append("sort_by", sort_by);
      // Assuming your backend uses 'sort_reverse' boolean like other endpoints in your file
      params.append("sort_reverse", sort_dir === "desc" ? "true" : "false"); 
    }
// Attach disposition filter if one is selected
    if (disposition) {
      params.append("disposition", disposition);
    }
    const url = `${APP_BASE_URL}/gryd/db/objects/${endpoint}?${params.toString()}`;

    const response = await authenticatedFetch(url);

    if (!response.ok) {
      throw new Error(`Error fetching leads: ${await response.text()}`);
    }

    const json = await response.json();

    return {
      items: json?.data ?? [],
      total_number: json?.total_number ?? json?.total ?? 0,
      page_number: json?.page_number ?? page_number,
      page_size: json?.page_size ?? page_size,
      is_first: json?.is_first ?? true,
      is_last: json?.is_last ?? true,
    };
  } catch (error) {
    console.error("[fetchCampaignLeads]", error);
    return { items: [], total_number: 0 };
  }
}

// ---- NEW: Added fetchCampaignSessions here ----
export async function fetchCampaignSessions({
  campaignId = "",
  dealershipId = getDealershipId(),
  page_number = 1,
  page_size = 10,
  search = "",
  sort_by = "created",
  sort_reverse = "true",
  disposition = "",
  start_date = "",
  end_date = "",
} = {}) {
  if (!campaignId || !dealershipId) {
    return { items: [], total_number: 0 };
  }

  try {
    const params = new URLSearchParams({
      dealership_id: dealershipId,
      campaign_id: campaignId,
      page_number: String(page_number),
      page_size: String(page_size),
      sort_by: sort_by,
      sort_reverse: sort_reverse,
    });

    if (search) params.append("search", search);
    if (disposition && disposition !== "all") params.append("disposition", disposition);
    
    // Apply Date Range - Sending as a comma-separated string: created=min,max
    if (start_date || end_date) {
      let startEpoch = 0; // Default minimum epoch if no start date is selected
      let endEpoch = Math.floor(Date.now() / 1000); // Default maximum epoch (current time)

      if (start_date) {
        const startObj = new Date(start_date);
        startObj.setHours(0, 0, 0, 0); // Start of the selected day
        startEpoch = startObj.getTime() / 1000;
      }
      
      if (end_date) {
        const endObj = new Date(end_date);
        endObj.setHours(23, 59, 59, 999); // End of the selected day
        endEpoch = endObj.getTime() / 1000;
      }

      // Append the single parameter with the comma-separated format
      params.append("created", `${startEpoch},${endEpoch}`);
    }

    const url = `${APP_BASE_URL}/gryd/db/objects/session?${params.toString()}`;
    const response = await authenticatedFetch(url);

    if (!response.ok) throw new Error(`Error fetching campaign sessions`);

    const json = await response.json();

    return {
      items: json?.data ?? [],
      total_number: json?.total_number ?? json?.total ?? 0,
      page_number: json?.page_number ?? page_number,
      page_size: json?.page_size ?? page_size,
    };
  } catch (error) {
    console.error("[fetchCampaignSessions]", error);
    return { items: [], total_number: 0 };
  }
}

async function fetchUserSessions(
  userId = "",
  campaignId = "",
  dealershipId = getDealershipId()
) {
  if (!userId || !campaignId || !dealershipId) {
    return { items: [], total: 0 };
  }

  try {
    // Build URL with query parameters matching the curl command
    const params = new URLSearchParams({
      status: "completed",
      dealership_id: dealershipId,
      campaign_id: campaignId,
      lead_id: userId,
      // page_size: "10",
      _reverse: "updated",
    });

    const url = `${APP_BASE_URL}/gryd/db/objects/session?${params.toString()}`;

    const response = await authenticatedFetch(url);
    if (!response.ok) throw new Error(await response.text());

    const json = await response.json();

    return {
      items: json?.data ?? [],
      total: json?.total_number ?? 0,
      page_number: json?.page_number ?? 1,
      page_size: json?.page_size ?? 10,
      is_first: json?.is_first ?? true,
      is_last: json?.is_last ?? true,
    };
  } catch (error) {
    console.error("[fetchUserSessions]", error);
    return { items: [], total: 0 };
  }
}

/**
 * Fetches active sessions for a dealership
 * Matches curl: GET /gryd/db/objects/session?session_live=True&dealership_id={id}
 * Headers: X-GRYD-ENTERPRISE-ID: autocrm, X-GRYD-TOKEN, X-GRYD-SESSION-ID, X-GRYD-ROLE: agent, X-GRYD-APPLICATION-ID: autocrm
 * Response: { data: SessionData[], total_number: number, page_number, page_size, is_first, is_last }
 */
// utils/api.ts
// (Assuming APP_BASE_URL is defined elsewhere in your file)

export async function fetchActiveSessions(dealershipId, params = {}) {
  if (!dealershipId) {
    console.warn("[fetchActiveSessions] No dealershipId provided");
    return { data: [], total_number: 0, page_number: 1 };
  }

  // Get credentials from cookies directly to match curl command exactly
  const getCookie = (name) => {
    if (typeof document === "undefined") return null;
    const match = document.cookie
      .split("; ")
      .find((row) => row.startsWith(name + "="));
    return match ? decodeURIComponent(match.split("=")[1]) : null;
  };

  const token = getCookie("gryd_token");
  const sessionId = getCookie("gryd_session_id");
  let applicationId = getCookie("gryd_application_id");

  // Default to autocrm if not set or if it's "gryd"
  if (!applicationId || applicationId === "gryd") {
    applicationId = "autocrm";
  }

  if (!token || !sessionId) {
    console.warn("[fetchActiveSessions] Missing credentials");
    return { data: [], total_number: 0, page_number: 1 };
  }

  try {
    // Dynamically build URL parameters
    const searchParams = new URLSearchParams();
    
    // Default required params
    searchParams.append("session_live", "True");
    searchParams.append("dealership_id", dealershipId);

    // Apply Pagination
    if (params.p) searchParams.append("page_number", params.p);
    if (params.page_size) searchParams.append("page_size", params.page_size);

    // Apply Sorting
    if (params.sort_by) searchParams.append("sort_by", params.sort_by);
    if (params.sort_order) {
      searchParams.append("sort_reverse", params.sort_order === "desc" ? "true" : "false");
    } else {
      searchParams.append("sort_reverse", "true"); 
    }

    // Apply Filters
    if (params.search) searchParams.append("search", params.search);
    if (params.channel) searchParams.append("channel", params.channel);
    if (params.status) searchParams.append("status", params.status);
    if (params.campaign_type) searchParams.append("campaign_type", params.campaign_type);
    
     
 // Apply Date Range - Sending as a comma-separated string: created=min,max
    if (params.start_date || params.end_date) {
      let startEpoch = 0; // Default minimum epoch if no start date is selected
      let endEpoch = Math.floor(Date.now() / 1000); // Default maximum epoch (current time)

      if (params.start_date) {
        const startObj = new Date(params.start_date);
        startObj.setHours(0, 0, 0, 0); // Start of the selected day
        startEpoch = startObj.getTime() / 1000;
      }
      
      if (params.end_date) {
        const endObj = new Date(params.end_date);
        endObj.setHours(23, 59, 59, 999); // End of the selected day
        endEpoch = endObj.getTime() / 1000;
      }

      // Append the single parameter with the comma-separated format
      searchParams.append("created", `${startEpoch},${endEpoch}`);
    }

    const url = `${APP_BASE_URL}/gryd/db/objects/session?${searchParams.toString()}`;
    console.log("[fetchActiveSessions] Fetching from URL:", url);

    // Make direct fetch call matching curl command exactly
    const response = await fetch(url, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        "X-GRYD-ENTERPRISE-ID": "autocrm",
        "X-GRYD-TOKEN": token,
        "X-GRYD-SESSION-ID": sessionId,
        Accept: "application/json",
        "X-GRYD-ROLE": "agent",
        "X-GRYD-APPLICATION-ID": applicationId,
      },
      cache: "no-store",
      credentials: "omit",
      mode: "cors",
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error("[fetchActiveSessions] API error:", response.status, errorText);
      throw new Error(`API Error ${response.status}: ${errorText}`);
    }

    const json = await response.json();
    return json;

  } catch (error) {
    console.error("[fetchActiveSessions] Error:", error);
    return { data: [], total_number: 0, page_number: 1 };
  }
}

/* ---------------------------------------------------
   Exports
--------------------------------------------------- */

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
  fetchAudienceTasks,
  getTaskResult,
  // fetchPreSalesCampaigns,
  // fetchPostSalesCampaigns,
  fetchCampaignObjectives,
  fetchCampaignSummary,
  fetchDealershipCampaigns,
  fetchCampaignPerformanceSummary,
  fetchCampaignLeads,
  // fetchCampaignSessions, // <-- Exported here
  fetchUserSessions,
  // fetchActiveSessions,
  epochToIST,
  capitalize,
  getDealershipId,
  getBrands,
};