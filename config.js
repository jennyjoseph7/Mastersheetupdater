/**
 * AutoNage - Lead Operations Automation Configuration
 *
 * ⚠ This file is gitignored. Copy config.example.js to config.js and fill in your tokens.
 */

window.JEJO_CONFIG = {
  // --- GRYD AI BACKEND ---
  grydEndpoint: "https://autongagetools.jennyjoseph-k.workers.dev",
  grydModel: "gcp-gemini-3.1-flash-lite-preview",

  // ⚠ REPLACE THIS with your actual gryd signup token
  grydSignupToken: "YXV0b2NybTE3NjI2MTAzOTUgMjY0NTI0",

  useGrydLlm: true,

  // --- Proxy settings (for Cloudflare Worker auth) ---
  apiEndpoint: "https://autongagetools.jennyjoseph-k.workers.dev",
  proxyHandshakeToken: "autonage-2026-jejo3214",

  // --- AI PERFORMANCE TUNING ---
  llmBatchSize: 30,
  llmMaxConcurrent: 5,
  llmMaxRetries: 1,
  llmRequestTimeoutMs: 45000,
  llmPromptCharLimit: 1200,
  llmMaxOutputTokens: 1600,

  llmDispositionBatchSize: 25,
  llmDispositionMaxConcurrent: 5,
  llmDispositionTimeoutMs: 60000,
  llmDispositionPromptCharLimit: 2500,
  llmDispositionMaxOutputTokens: 1800,

  // --- RECORDING DOWNLOAD PROXY ---
  corsProxyUrl: ""
};
