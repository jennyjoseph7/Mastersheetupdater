/* ═══════════════════════════════════════════════════════════════════════
   ai-config.js — Shared AI configuration for all AutoNage pages
   ═══════════════════════════════════════════════════════════════════════
   Load BEFORE any page-specific script that calls these functions.

   Functions defined here use `var` and are intentionally global so every
   page's inline script block can call them without refactoring.
   ═══════════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  // ── ENDPOINTS ──────────────────────────────────────────────────────────
  window.NVIDIA_DIRECT_ENDPOINT = 'https://integrate.api.nvidia.com/v1/chat/completions';
  window.OPENROUTER_DIRECT_ENDPOINT = 'https://openrouter.ai/api/v1/chat/completions';
  window.NVIDIA_KEY_STORAGE = 'llm-api-key';

  // ── CONFIG READER ─────────────────────────────────────────────────────
  // Reads a numeric config value from JEJO_CONFIG. Returns fallback if
  // the value is missing, non-positive, or not a finite number.
  window.getConfigNumber = function (key, fallback) {
    var cfg = window.JEJO_CONFIG || {};
    var value = Number(cfg[key]);
    return Number.isFinite(value) && value > 0 ? value : fallback;
  };

  // ── API ENDPOINT ───────────────────────────────────────────────────────
  // Returns the proxy endpoint from JEJO_CONFIG (if set and valid), or the
  // default NVIDIA direct endpoint as a fallback.
  window.getApiEndpoint = function () {
    if (window.JEJO_CONFIG && window.JEJO_CONFIG.apiEndpoint) {
      var url = window.JEJO_CONFIG.apiEndpoint.trim();
      if (url && url !== 'YOUR_PROXY_URL_HERE') return url;
    }
    return window.NVIDIA_DIRECT_ENDPOINT;
  };

  // ── PROXY CHECK ───────────────────────────────────────────────────────
  // Returns true if the given endpoint is NOT one of the known direct
  // endpoints (NVIDIA or OpenRouter), meaning the user configured a proxy.
  window.isProxyEndpoint = function (endpoint) {
    return endpoint !== window.NVIDIA_DIRECT_ENDPOINT &&
           endpoint !== window.OPENROUTER_DIRECT_ENDPOINT;
  };

  // ── LLM MODEL ──────────────────────────────────────────────────────────
  // Returns the configured model from JEJO_CONFIG (nvidiaModel or
  // openRouterModel), or the default Mistral medium as a fallback.
  window.getLlmModel = function () {
    var cfg = window.JEJO_CONFIG || {};
    return cfg.nvidiaModel || cfg.openRouterModel || 'mistralai/mistral-medium-3.5-128b';
  };

  // ── STRING HASH ────────────────────────────────────────────────────────
  // Fast non-cryptographic hash used for cache-key generation. Prefix
  // ensures the result starts with a letter so it's safe in object keys.
  window.hashStr = function (str) {
    var h = 0;
    for (var i = 0; i < str.length; i++) {
      h = ((h << 5) - h) + str.charCodeAt(i);
      h |= 0;
    }
    return 'llm-' + Math.abs(h).toString(36);
  };
  // ── API KEY ───────────────────────────────────────────────────────────
  // Shared API key resolution across all pages. Handles:
  // 1. Proxy mode (no key needed)
  // 2. In-memory cached key (dashboard sets window._inMemoryApiKey)
  // 3. Typed input field (checks both openRouterApiKey and nvidiaApiKeyInput IDs)
  // 4. JEJO_CONFIG configured key
  // 5. localStorage fallback
  window.getApiKey = function () {
    if (window.isProxyEndpoint(window.getApiEndpoint())) return 'PROXY_ACTIVE';

    if (window._inMemoryApiKey) return window._inMemoryApiKey;

    // Check typed key from whichever input field exists on this page
    var input = document.getElementById('openRouterApiKey') ||
                document.getElementById('nvidiaApiKeyInput');
    var typedKey = input ? input.value.trim() : '';
    if (typedKey) {
      window._inMemoryApiKey = typedKey;
      return typedKey;
    }

    // Check configured key in JEJO_CONFIG
    var cfg = window.JEJO_CONFIG || {};
    var configKey = cfg.nvidiaApiKey || cfg.openRouterApiKey || '';
    if (configKey && configKey !== 'YOUR_NVIDIA_API_KEY_HERE') {
      window._inMemoryApiKey = configKey;
      return configKey;
    }

    // Fallback to localStorage
    var saved = (localStorage.getItem(window.NVIDIA_KEY_STORAGE) || '').trim();
    if (saved) window._inMemoryApiKey = saved;
    return saved;
  };

  // ── PROMPT SANITIZER ──────────────────────────────────────────────────
  // Cleans user-provided text before inserting into an LLM prompt.
  // Strips control characters, replaces double-quotes, removes known
  // prompt-injection / jailbreak keywords, and truncates to charLimit.
  // Each page passes its own LLM_PROMPT_CHAR_LIMIT as the second argument.
  window.sanitizeForPrompt = function (text, charLimit) {
    if (!text) return '';
    charLimit = charLimit || 2500;
    var s = String(text);
    // Strip control characters except \n, \t, \r
    s = s.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '');
    // Replace double quotes with single quotes
    s = s.replace(/"/g, "'");
    // Remove known prompt-injection / jailbreak patterns
    s = s.replace(/ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|directions|prompts?)/gi, '[REDACTED]');
    s = s.replace(/forget\s+(all\s+)?(previous|prior|above)\s+(instructions|directions|prompts?)/gi, '[REDACTED]');
    s = s.replace(/you\s+are\s+(now|not\s+required\s+to)/gi, '[REDACTED]');
    s = s.replace(/system\s+(prompt|message|instruction)/gi, '[REDACTED]');
    s = s.replace(/\bDAN\b|do\s+anything\s+now/gi, '[REDACTED]');
    s = s.replace(/output\s+(format|as|in)\s+json/i, '[REDACTED]');
    // Truncate to prevent token flooding
    if (s.length > charLimit) s = s.substring(0, charLimit) + '...[truncated]';
    return s;
  };

})();
