"use client";

import {
  APP_BASE_URL,
  authenticatedFetch,
  FILE_UPLOAD_URL,
  FILE_UPLOAD_HEADERS,
} from "./headers";
import { api } from "@/lib/api";

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

// async function extractCsvHeadersAPI(fileUrl) {
//   const servicename =
//     process.env.NEXT_PUBLIC_AUTOCRM_CORE_SERVICE_NAME || "autocrm-core";
//   const response = await authenticatedFetch(
//     `${APP_BASE_URL}/gryd/task/${servicename}/extract_csv_headers`,
//     {
//       method: "POST",
//       body: JSON.stringify({
//         args: [fileUrl],
//         kwargs: {},
//         runtime_limit: 3600,
//         cancellable: true,
//       }),
//     },
//   );

//   if (!response.ok) {
//     throw new Error(await response.text());
//   }

//   return response.json();
// }

async function extractCsvHeadersAPI(fileUrl) {
  const servicename =
    process.env.NEXT_PUBLIC_AUTOCRM_CORE_SERVICE_NAME || "autocrm-core";

  return directExecuteTask(servicename, "extract_csv_headers", {
    args: [fileUrl],
    kwargs: {},
    runtime_limit: 3600,
    cancellable: true,
  });
}

async function startImportTask(
  category,
  audienceName,
  fileUrl,
  tags = [],
  sourceName = "",
  fieldMapping = {},
  campaignIdOrObjectiveId = "",
  dealershipId = getDealershipId(),
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
        campaignIdOrObjectiveId,
      );

    if (isUuid) kwargs.campaign_id = campaignIdOrObjectiveId;
    else kwargs.campaign_objective_id = campaignIdOrObjectiveId;
  }
  const servicename =
    process.env.NEXT_PUBLIC_AUTOCRM_CORE_SERVICE_NAME || "autocrm-core";

  const response = await authenticatedFetch(
    `${APP_BASE_URL}/gryd/task/${servicename}/import_leads_from_csv`,
    {
      method: "POST",
      body: JSON.stringify({
        args: [category || "post-sales", getDealershipId(), fileUrl],
        kwargs,
        runtime_limit: 3600,
        cancellable: true,
      }),
    },
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
    },
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
    },
  );

  return response.json();
}

async function getTaskStatus(taskId) {
  const response = await authenticatedFetch(
    `${APP_BASE_URL}/gryd/status/${taskId}`,
  );
  return response.json();
}

async function getTaskResult(taskId) {
  const response = await authenticatedFetch(
    `${APP_BASE_URL}/gryd/result/${taskId}`,
  );

  updateAudienceTask(taskId, { fetched_result: true }).catch(console.error);
  return response.json();
}

/* ---------------------------------------------------
   Campaign Fetchers
--------------------------------------------------- */

// Update these three functions in your api.js

export async function fetchPreSalesCampaigns(
  page = 1,
  pageSize = 50,
  status = "all",
  channel = "all",
  search = "",
  dealershipId = getDealershipId(),
) {
  const dId = dealershipId || getDealershipId();
  let url = `${APP_BASE_URL}/gryd/db/objects/pre_sales_campaign?page_number=${page}&page_size=${pageSize}&dealership_id=${encodeURIComponent(dId)}&sort_by=created&sort_reverse=true`;

  if (status && status !== "all")
    url += `&campaign_status=${encodeURIComponent(status)}`;
  if (channel && channel !== "all")
    url += `&channels=${encodeURIComponent(channel)}`;
  if (search) url += `&search_term=~${encodeURIComponent(search)}`; // Added this line

  const response = await authenticatedFetch(url, { headers: {} });
  const json = await response.json();
  return { items: json?.data ?? [], total: json?.total_number ?? 0 };
}

export async function fetchPostSalesCampaigns(
  page = 1,
  pageSize = 50,
  status = "all",
  channel = "all",
  search = "",
  dealershipId = getDealershipId(),
) {
  const dId = dealershipId || getDealershipId();
  if (!dId) return { items: [], total: 0 };
  let url = `${APP_BASE_URL}/gryd/db/objects/post_sales_campaign?page_number=${page}&page_size=${pageSize}&dealership_id=${encodeURIComponent(dId)}&sort_by=created&sort_reverse=true`;

  if (status && status !== "all")
    url += `&campaign_status=${encodeURIComponent(status)}`;
  if (channel && channel !== "all")
    url += `&channels=${encodeURIComponent(channel)}`;
  if (search) url += `&search_term=~${encodeURIComponent(search)}`; // Added this line

  const response = await authenticatedFetch(url);
  const json = await response.json();
  return { items: json?.data ?? [], total: json?.total_number ?? 0 };
}

export async function fetchDealershipCampaigns(
  page = 1,
  pageSize = 50,
  status = "all",
  channel = "all",
  search = "",
) {
  let url = `${APP_BASE_URL}/gryd/db/objects/dealership_campaign?page_number=${page}&page_size=${pageSize}&sort_by=created&sort_reverse=true`;

  if (status && status !== "all")
    url += `&campaign_status=${encodeURIComponent(status)}`;
  if (channel && channel !== "all")
    url += `&channels=${encodeURIComponent(channel)}`;
  if (search) url += `&search_term=~${encodeURIComponent(search)}`; // Added this line

  const response = await authenticatedFetch(url, { headers: {} });
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
      dealershipId,
    )}`,
  );
  // const response = await authenticatedFetch(url);
  const json = await response.json();
  return json?.data ?? [];
}

// async function fetchAudienceTasks(page = 1, pageSize = 50) {
//   return fetchAPIData("audience_task", {
//     dealership_id: getDealershipId(),
//     page_number: page,
//     page_size: pageSize,
//     sort_by: "created",
//     sort_reverse: true,
//   });
// }
async function fetchAudienceTasks(page = 1, pageSize = 10, filterType = "all", campaignId = "") {
  const dealershipId = getDealershipId();
  if (!dealershipId) return { items: [], total: 0 };

  // 1. Build the base parameters
  const params = new URLSearchParams({
    dealership_id: dealershipId,
    page_number: String(page),
    page_size: String(pageSize),
    sort_by: "created",
    sort_reverse: "true",
  });

  if (campaignId) {
    params.append("campaign_id", campaignId);
  } else {
    // 2. Append the exact filter logic matching your backend
    if (filterType === "previous") {
      // Appends "&campaign_id~="
      params.append("campaign_id~", "");
    } else if (filterType === "fresh") {
      // Appends "&campaign_id="
      params.append("campaign_id", "");
    }
  }

  const url = `${APP_BASE_URL}/gryd/db/objects/audience_task?${params.toString()}`;

  // 3. Make the fetch call directly to bypass fetchAPIData's empty string blocker
  try {
    const response = await authenticatedFetch(url, { method: "GET" });
    if (!response.ok) throw new Error("API request failed");

    const json = await response.json();
    return {
      items: json?.data ?? [],
      total: json?.total ?? json?.total_number ?? 0,
    };
  } catch (error) {
    console.error("fetchAudienceTasks error:", error);
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
    console.warn("[fetchCampaignLeads] Missing required params:", {
      campaignId,
      campaignType,
    });
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
    if (disposition && disposition !== "all")
      params.append("disposition", disposition);

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
  dealershipId = getDealershipId(),
) {
  if (!userId || !campaignId || !dealershipId) {
    return { items: [], total: 0 };
  }

  try {
    // Build URL with query parameters matching the curl command
    const params = new URLSearchParams({
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
    const sessionLive = params.session_live !== undefined ? params.session_live : false;
    searchParams.append("session_live", sessionLive ? "True" : "False");
    searchParams.append("dealership_id", dealershipId);

    // Apply Pagination
    if (params.p) searchParams.append("page_number", params.p);
    if (params.page_size) searchParams.append("page_size", params.page_size);

    // Apply Sorting
    if (params.sort_by) searchParams.append("sort_by", params.sort_by);
    if (params.sort_order) {
      searchParams.append(
        "sort_reverse",
        params.sort_order === "desc" ? "true" : "false",
      );
    } else {
      searchParams.append("sort_reverse", "true");
    }

    // Apply Filters
    if (params.search) searchParams.append("search", params.search);
    if (params.channel) searchParams.append("channel", params.channel);
    if (params.status) searchParams.append("status", params.status);
    if (params.campaign_type)
      searchParams.append("campaign_type", params.campaign_type);

    // Apply Date Range - Sending as a comma-separated string: updated=min,max
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
      searchParams.append("updated", `${startEpoch},${endEpoch}`);
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
      console.error(
        "[fetchActiveSessions] API error:",
        response.status,
        errorText,
      );
      throw new Error(`API Error ${response.status}: ${errorText}`);
    }

    const json = await response.json();
    return json;
  } catch (error) {
    console.error("[fetchActiveSessions] Error:", error);
    return { data: [], total_number: 0, page_number: 1 };
  }
}

/**
 * Executes an asynchronous task, polls for status, and retrieves the final result.
 * * @param {string} service - The name of the service (e.g., 'autocrm-short-run-agent')
 * @param {string} taskName - The task to execute (e.g., 'generate_campaign_idea')
 * @param {object} payload - The arguments and kwargs for the task
 * @param {function} onProgress - Optional callback to handle status updates for the UI
 * @param {object} options - Optional config for polling (intervalMs, maxRetries)
 * @returns {Promise<any>} The final result object
 */
export const executeTaskWithPolling = async (
  service,
  taskName,
  payload,
  onProgress = null,
  options = {},
) => {
  const { intervalMs = 2000, maxRetries = 60 } = options; // Default: 2 mins total timeout

  // 1. Submit the task
  if (onProgress) onProgress("Submitting task to queue...");
  const taskRes = await api(
    `/gryd/task/${service}/${taskName}`,
    "POST",
    payload,
  );

  const taskId = taskRes?.job?.task_id || taskRes?.task_id;
  if (!taskId) {
    throw new Error("Failed to retrieve task ID from the server response.");
  }

  // 2. Poll the status API
  let attempts = 0;
  let isComplete = false;

  while (!isComplete && attempts < maxRetries) {
    attempts++;
    await new Promise((resolve) => setTimeout(resolve, intervalMs));

    try {
      const statusRes = await api(`/gryd/status/${taskId}`, "GET");
      const currentStatus = statusRes?.status?.toLowerCase();

      // Trigger the callback to update the UI
      if (onProgress && (statusRes?.message || currentStatus)) {
        onProgress(statusRes.message || `Status: ${currentStatus}...`);
      }

      if (currentStatus === "success" || currentStatus === "completed") {
        isComplete = true;
        if (onProgress) onProgress("Task complete. Retrieving results...");
      } else if (currentStatus === "failed" || currentStatus === "error") {
        throw new Error(
          statusRes?.error || statusRes?.message || "Task failed on the server.",
        );
      }
    } catch (error) {
      const is404 = error?.message?.includes("404") || error?.status === 404;
      if (is404) {
        if (onProgress) {
          onProgress(`Status check returned 404, retrying (${attempts}/${maxRetries})...`);
        }
        console.warn(`[executeTaskWithPolling] Status check returned 404, retrying...`, error);
      } else {
        throw error;
      }
    }
  }

  if (!isComplete) {
    throw new Error("Task timed out while waiting for completion.");
  }

  // 3. Fetch the final result
  let resultRes = null;
  while (attempts < maxRetries) {
    try {
      resultRes = await api(`/gryd/result/${taskId}`, "GET");
      if (resultRes && resultRes.result !== undefined && resultRes.result !== null && resultRes.result !== "null") {
        break;
      }
      throw new Error("Result is null");
    } catch (error) {
      const is404 = error?.message?.includes("404") || error?.status === 404;
      const isNullResult = error?.message === "Result is null";
      
      if ((is404 || isNullResult) && attempts < maxRetries - 1) {
        attempts++;
        if (onProgress) {
          const reason = isNullResult ? "null result" : "404";
          onProgress(`Result returned ${reason}, retrying retrieval (${attempts}/${maxRetries})...`);
        }
        console.warn(`[executeTaskWithPolling] Result check returned ${isNullResult ? "null" : "404"}, retrying...`, error);
        await new Promise((resolve) => setTimeout(resolve, intervalMs));
      } else {
        throw error;
      }
    }
  }

  if (!resultRes || resultRes.result === undefined || resultRes.result === null || resultRes.result === "null") {
    throw new Error("Failed to retrieve the final result data.");
  }

  return resultRes.result;
};

/**
 * Executes a fast, synchronous task directly and returns the immediate response data.
 * @param {string} service - The name of the service (e.g., 'autocrm-core')
 * @param {string} taskName - The task to execute (e.g., 'extract_csv_headers')
 * @param {object} payload - The arguments and kwargs for the task
 * @returns {Promise<any>} The direct execution result data
 */
export const directExecuteTask = async (service, taskName, payload) => {
  // Directly targets the blocking execute endpoint instead of /gryd/task/
  const response = await api(
    `/gryd/execute/${taskName}/${service}`,
    "POST",
    payload,
  );

  // If your api utility unpacks data natively, adjust this check if needed
  if (!response) {
    throw new Error(
      "Direct execution failed to return a response from the server.",
    );
  }

  return response;
};

/* ---------------------------------------------------
   Billing & Payments 
--------------------------------------------------- */

export async function createCreditPurchaseOrder(
  credits,
  dealershipId = getDealershipId(),
) {
  if (!dealershipId) {
    throw new Error("Dealership ID is required to purchase credits.");
  }

  const servicename =
    process.env.NEXT_PUBLIC_AUTOCRM_CORE_SERVICE_NAME || "autocrm-core";
  const url = `${APP_BASE_URL}/gryd/api/${servicename}/payment_service`;

  try {
    // We use authenticatedFetch here because it likely handles the
    // X-GRYD-TOKEN and X-GRYD-SESSION-ID headers automatically.
    const response = await authenticatedFetch(url, {
      method: "POST",
      body: JSON.stringify({
        args: ["purchase_credit"],
        kwargs: {
          dealership_id: dealershipId,
          credits: Number(credits),
          currency: "INR",
        },
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to create order: ${errorText}`);
    }

    return await response.json();
  } catch (error) {
    console.error("[createCreditPurchaseOrder] Error:", error);
    throw error;
  }
}

async function cloneLeadsTask(
  leadType,
  oldCampaignId,
  newCampaignId,
  dealershipId,
  onProgress = null,
) {
  const servicename =
    process.env.NEXT_PUBLIC_AUTOCRM_CORE_SERVICE_NAME || "autocrm-core";
  return executeTaskWithPolling(
    servicename,
    "clone_leads_between_campaigns",
    {
      args: [leadType, oldCampaignId, newCampaignId, dealershipId],
      kwargs: {},
      runtime_limit: 3600,
      cancellable: true,
    },
    onProgress,
  );
}

async function assignAudienceTask(
  leadType,
  campaignId,
  campaignObjectiveId,
  dealershipId,
  kwargs = {},
  onProgress = null,
) {
  const servicename =
    process.env.NEXT_PUBLIC_AUTOCRM_CORE_SERVICE_NAME || "autocrm-core";
  return executeTaskWithPolling(
    servicename,
    "assign_audience_to_campaign",
    {
      args: [leadType, campaignId, campaignObjectiveId, dealershipId],
      kwargs: kwargs,
      runtime_limit: 3600,
      cancellable: true,
    },
    onProgress,
  );
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
  fetchCampaignObjectives,
  fetchCampaignSummary,
  fetchCampaignPerformanceSummary,
  fetchCampaignLeads,
  fetchUserSessions,
  epochToIST,
  capitalize,
  getDealershipId,
  getBrands,
  cloneLeadsTask,
  assignAudienceTask,

  // createCreditPurchaseOrder, // <-- New billing export added here
};
