// utils/api.js
import { APP_BASE_URL, HEADERS, FILE_UPLOAD_URL, FILE_UPLOAD_HEADERS } from "./headers";

// --- Existing Functions ---
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

// --- File Upload Flow Functions ---

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

// 2. Start Import Task (Updated with new kwargs)
async function startImportTask(category, audienceName, fileUrl, tags = [], sourceName = "") {
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
                    source_name: sourceName || "Uploaded via csv"
                },
                runtime_limit: 3600
            }),
        }
    );

    if (!response.ok) {
        const errorBody = await response.text();
        throw new Error(`Task start failed: ${errorBody}`);
    }

    return response.json();
}

// 3. Get Status
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

// 4. Get Result
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

function epochToIST(epochTime) {
    if (!epochTime) return "";
    const date = new Date(epochTime * 1000);
    const options = {
        timeZone: 'Asia/Kolkata',
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    };
    let a = new Intl.DateTimeFormat('en-IN', options).format(date);
    return a.replaceAll("/", "-").replace(",", " ");
}

function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
}

export { 
    fetchAPIData, 
    fetchPivotCountForCampaign, 
    uploadFileToGryd, 
    startImportTask, 
    getTaskStatus, 
    getTaskResult,
    epochToIST, 
    capitalize 
};