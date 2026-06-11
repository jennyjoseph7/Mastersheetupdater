/**
 * AutoNage - Lead Operations Automation Configuration
 *
 * Instructions:
 * 1. This file is gitignored (see .gitignore) so your keys stay local.
 * 2. Configure either the Secure Proxy URL (recommended) OR paste your NVIDIA API Key.
 * 3. For recording downloads, set corsProxyUrl to a CORS proxy endpoint.
 *
 * How each tool uses these settings:
 *   - Pre-Sales Sync & Post-Sales Sync: "Validate with AI" button → apiEndpoint or nvidiaApiKey
 *   - Dashboard: "Generate Dashboard" + AI insights → apiEndpoint or nvidiaApiKey
 *   - Recording Renamer: Download recordings → corsProxyUrl (toggle button in UI)
 */

window.JEJO_CONFIG = {
  // ────── OPTION 1: Secure Proxy Endpoint (RECOMMENDED) ──────
  // If configured, API keys stay on your server — BAs don't need to paste any key.
  // Example: "https://autonage-proxy.yourname.workers.dev"
  // Local dev: set to "http://localhost:3456" and run: cd server && npm start
  // Production: deploy a Cloudflare Worker and point here
  apiEndpoint: "https://autnongageleadoperations.jennyjosephofc1.workers.dev",

  // ── REQUIRED for Cloudflare Worker auth ──
  // Must match HANDSHAKE_TOKEN in: Cloudflare Dashboard → Worker → Settings → Variables
  // If left empty AND HANDSHAKE_TOKEN is set on the Worker, all AI calls will return 401.
  proxyHandshakeToken: "autonage-2026-jejo3214",

  // ────── OPTION 2: Direct NVIDIA API Key (fallback) ──────
  // Only used if apiEndpoint is empty above.
  // Get a key at: https://build.nvidia.com/explore/discover
  nvidiaApiKey: "",

  // NVIDIA model override (optional, default: mistralai/mistral-medium-3.5-128b)
  nvidiaModel: "mistralai/mistral-medium-3.5-128b",
  openRouterModel: "mistralai/mistral-medium-3.5-128b",

  // Performance tuning for slower/free endpoints
  llmBatchSize: 12,
  llmMaxConcurrent: 2,
  llmMaxRetries: 3,
  llmRequestTimeoutMs: 120000,
  llmPromptCharLimit: 1200,
  llmMaxOutputTokens: 1600,
  llmThemeBatchSize: 5,

  // Disposition validation uses longer transcripts, so keep it smaller.
  llmDispositionBatchSize: 5,
  llmDispositionMaxConcurrent: 3,
  llmDispositionTimeoutMs: 90000,
  llmDispositionPromptCharLimit: 2500,
  llmDispositionMaxOutputTokens: 1800,

  // ────── Recording Download CORS Proxy ──────
  // Some recording servers block cross-origin fetches (CORS).
  // Set this to a proxy (e.g., Cloudflare Worker) that fetches the recording and
  // returns it with permissive CORS headers.
  // The proxy receives: <corsProxyUrl>?url=<encoded_recording_url>
  // Example: "https://autonage-cors-proxy.yourname.workers.dev"
  corsProxyUrl: ""
};
