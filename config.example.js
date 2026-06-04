/**
 * AutoNage - Lead Operations Automation Configuration
 * 
 * Instructions:
 * 1. Copy/Rename this file to "config.js" in the same folder.
 * 2. Configure either the Secure Proxy URL (highly recommended) OR your API Key directly.
 */

window.JEJO_CONFIG = {
  // --- OPTION 1: SECURE PROXY ENDPOINT (RECOMMENDED) ---
  // If configured, the key is hidden on the server, and BAs don't need any local setup.
  // Example: "https://autonage-proxy.yourname.workers.dev"
  apiEndpoint: "",

  // Optional: A custom handshake token to authenticate with your proxy
  proxyHandshakeToken: "jejo-presales-secure-handshake",

  // --- OPTION 2: DIRECT NVIDIA API KEY (FALLBACK) ---
  // Use this if you are not running a proxy server. 
  nvidiaApiKey: "",

  // Optional: override the default model
  nvidiaModel: "mistralai/mistral-medium-3.5-128b",

  // Optional direct OpenRouter fallback. Leave apiEndpoint empty or set it to
  // "https://openrouter.ai/api/v1/chat/completions", then provide this key.
  // For a proxy/Worker, keep keys server-side instead.
  openRouterApiKey: "",

  // --- AI PERFORMANCE TUNING ---
  // These defaults are conservative for slower/free endpoints. Increase only
  // when using a fast paid endpoint.
  llmBatchSize: 12,
  llmMaxConcurrent: 2,
  llmMaxRetries: 1,
  llmRequestTimeoutMs: 70000,
  llmPromptCharLimit: 1200,
  llmMaxOutputTokens: 1600,

  // Disposition validation includes longer transcripts, so it uses smaller
  // defaults than the dashboard.
  llmDispositionBatchSize: 6,
  llmDispositionMaxConcurrent: 1,
  llmDispositionTimeoutMs: 90000,
  llmDispositionPromptCharLimit: 2500,
  llmDispositionMaxOutputTokens: 1800,

  // --- RECORDING DOWNLOAD PROXY (CORS FIX) ---
  // Some recording URLs are hosted on servers that block cross-origin requests (CORS).
  // Set this to a proxy endpoint (e.g., a Cloudflare Worker) that fetches the recording
  // and returns it with permissive CORS headers.
  // The proxy receives the target URL as a query param: <corsProxyUrl>?url=<encoded_recording_url>
  // Example: "https://autonage-cors-proxy.yourname.workers.dev"
  corsProxyUrl: ""
};
