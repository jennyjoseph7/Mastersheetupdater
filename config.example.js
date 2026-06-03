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

  // --- OPTION 2: DIRECT OPENROUTER KEY (FALLBACK) ---
  // Use this if you are not running a proxy server. 
  openRouterApiKey: "",

  // Optional: override the default DeepSeek model
  openRouterModel: "deepseek/deepseek-v4-flash",

  // --- RECORDING DOWNLOAD PROXY (CORS FIX) ---
  // Some recording URLs are hosted on servers that block cross-origin requests (CORS).
  // Set this to a proxy endpoint (e.g., a Cloudflare Worker) that fetches the recording
  // and returns it with permissive CORS headers.
  // The proxy receives the target URL as a query param: <corsProxyUrl>?url=<encoded_recording_url>
  // Example: "https://autonage-cors-proxy.yourname.workers.dev"
  corsProxyUrl: ""
};
