// utils/api.js
import { APP_BASE_URL, HEADERS, FILE_UPLOAD_URL, FILE_UPLOAD_HEADERS } from "./headers";

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
            "pre_sales": (preJson?.data?.campaign_id ?? 0),
            "post_sales": (postJson?.data?.campaign_id ?? 0)
        }
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
async function startImportTask(category, audienceName, fileUrl, tags = [], sourceName = "", fieldMapping = {}) {
    const response = await fetch(
        `${APP_BASE_URL}/gryd/task/autocrm-core/import_leads_from_csv`,
        {
            method: "POST",
            headers: HEADERS,
            body: JSON.stringify({
                args: [
                    category || "post-sales", 
                      "ambal-auto-south-india", 
                    fileUrl
                ],
                kwargs: {
                      campaign_id: "626952a0-1ac7-3a7c-85aa-c46d30897ea4",
                    campaign_objective_id: "626952a0-1ac7-3a7c-85aa-c46d30897ea4",
                    workshop_id: "ambal-auto - ambal-auto---service-center - coimbatore",
                    source: "csv",
                    tags: tags,
                    source_name: sourceName || "Uploaded via csv",
                    mapping: fieldMapping },
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
    const response = await fetch(`${APP_BASE_URL}/gryd/db/objects/audience_task`, {
        method: "PUT",
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

// --- Helpers ---
function epochToIST(epochTime) {
    if (!epochTime) return "";
    const date = new Date(epochTime * 1000);
    const options = {
        timeZone: 'Asia/Kolkata',
        year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', second: '2-digit'
    };
    let a = new Intl.DateTimeFormat('en-IN', options).format(date);
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
    epochToIST, 
    capitalize 
};