"use client";

import {
  APP_BASE_URL,
  authenticatedFetch,
  FILE_UPLOAD_URL,
  FILE_UPLOAD_HEADERS,
} from "./headers";

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
  campaignIdOrObjectiveId = ""
) {
  const kwargs = {
    audience_name: audienceName,
    workshop_id: "ambal-auto - ambal-auto---service-center - coimbatore",
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
        args: [category || "post-sales", "ambal-auto-south-india", fileUrl],
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
   Campaign Fetchers (Admin override supported)
--------------------------------------------------- */

async function fetchPreSalesCampaigns(page = 1, pageSize = 50) {
  const response = await authenticatedFetch(
    `${APP_BASE_URL}/gryd/db/objects/pre_sales_campaign?page_number=${page}&page_size=${pageSize}`,
    {
      headers: { "X-GRYD-ROLE": "admin" },
    }
  );

  const json = await response.json();
  return {
    items: json?.data ?? [],
    total: json?.total_number ?? 0,
  };
}

async function fetchPostSalesCampaigns(dealershipId) {
  const response = await authenticatedFetch(
    `${APP_BASE_URL}/gryd/db/objects/post_sales_campaign?dealership_id=${encodeURIComponent(
      dealershipId
    )}`
  );

  const json = await response.json();
  return {
    items: json?.data ?? [],
    total: json?.total_number ?? 0,
  };
}

async function fetchCampaignObjectives(campaignType) {
  return fetchAPIData("campaign_objective", {
    campaign_type: campaignType?.replace(/_/g, "-"),
  });
}

async function fetchCampaignSummary(dealershipId) {
  const url = dealershipId
    ? `${APP_BASE_URL}/gryd/db/objects/campaign_summary?dealership_id=${encodeURIComponent(
        dealershipId
      )}`
    : `${APP_BASE_URL}/gryd/db/objects/campaign_summary`;

  const response = await authenticatedFetch(url);
  const json = await response.json();
  return json?.data ?? [];
}
async function fetchAudienceTasks(page = 1, pageSize = 50) {
  return fetchAPIData("audience_task", {
    page_number: page,
    page_size: pageSize,
  });
}

/* ---------------------------------------------------
   Utils
--------------------------------------------------- */

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
  fetchPreSalesCampaigns,
  fetchPostSalesCampaigns,
  fetchCampaignObjectives,
  fetchCampaignSummary,
  epochToIST,
  capitalize,
};
