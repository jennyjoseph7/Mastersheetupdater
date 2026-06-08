/**
 * AutoNage NVIDIA API Proxy — Cloudflare Worker
 *
 * Deploy this Worker to bypass corporate network blocks on NVIDIA domains.
 * The Worker runs on Cloudflare's network, which CAN reach the NVIDIA API.
 *
 * Features:
 *   - Forwards POST requests to the NVIDIA API
 *   - NVIDIA API key stays server-side (never exposed to browsers)
 *   - Handshake token authenticates your frontend
 *   - CORS headers allow browser access
 *   - Rate limiting (100 req/min per IP)
 */

// ── Configuration ──────────────────────────────────────────────────────────

// Set these via Cloudflare Dashboard → Worker → Settings → Variables
// NEVER hardcode secrets in this file!

const HANDSHAKE_TOKEN_VAR = 'HANDSHAKE_TOKEN';
const ALLOWED_ORIGINS = '*';  // ⚠ RESTRICT THIS in production: set to your frontend URL(s), e.g. ['http://localhost:5500', 'https://yourdomain.com']

const NVIDIA_ENDPOINT = 'https://integrate.api.nvidia.com/v1/chat/completions';
const DEFAULT_UPSTREAM_TIMEOUT_MS = 90_000;

// ── Rate limiting (simple in-memory per IP) ──────────────────────────────
const rateLimitMap = new Map();
const RATE_LIMIT = 100;     // max requests
const RATE_WINDOW = 60_000; // per 60 seconds

function checkRateLimit(ip) {
  const now = Date.now();
  const entry = rateLimitMap.get(ip);
  if (!entry || now - entry.windowStart > RATE_WINDOW) {
    rateLimitMap.set(ip, { windowStart: now, count: 1 });
    return true;
  }
  if (entry.count >= RATE_LIMIT) return false;
  entry.count++;
  return true;
}

// ── CORS headers ────────────────────────────────────────────────────────────
const corsHeaders = {
  'Access-Control-Allow-Origin': ALLOWED_ORIGINS,
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Handshake-Token, Accept',
  'Access-Control-Max-Age': '86400',
};

function jsonResponse(status, body, extraHeaders = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      ...corsHeaders,
      'Content-Type': 'application/json',
      ...extraHeaders,
    },
  });
}

// ── Request handler ─────────────────────────────────────────────────────────
export default {
  async fetch(request, env, ctx) {
    const { method } = request;
    const clientIP = request.headers.get('CF-Connecting-IP') || 'unknown';
    const startedAt = Date.now();

    // Read secrets from env (set via Cloudflare Dashboard → Settings → Variables)
    const NVIDIA_API_KEY = env.NVIDIA_API_KEY;
    const HANDSHAKE_TOKEN = env.HANDSHAKE_TOKEN || 'jejo-presales-secure-handshake';
    const UPSTREAM_TIMEOUT_MS = Number(env.UPSTREAM_TIMEOUT_MS) > 0
      ? Number(env.UPSTREAM_TIMEOUT_MS)
      : DEFAULT_UPSTREAM_TIMEOUT_MS;

    // ── Preflight ───────────────────────────────────────────────────────
    if (method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders });
    }

    // ── Health check ────────────────────────────────────────────────────
    if (method === 'GET') {
      const url = new URL(request.url);
      if (url.pathname !== '/health') {
        return jsonResponse(404, { error: 'Not found. Use GET /health' });
      }
      return jsonResponse(200, { status: 'ok', proxy: 'autonage-cloudflare' });
    }

    // ── Only proxy POST ─────────────────────────────────────────────────
    if (method !== 'POST') {
      return jsonResponse(404, { error: 'Use POST /v1/chat/completions' });
    }

    // ── Rate limit ──────────────────────────────────────────────────────
    if (!checkRateLimit(clientIP)) {
      return jsonResponse(429, {
        error: 'Too Many Requests',
        message: 'Rate limit exceeded. Max 100 requests per minute.',
      });
    }

    // ── Validate handshake token ────────────────────────────────────────
    const token = request.headers.get('X-Handshake-Token');
    if (!token || token !== HANDSHAKE_TOKEN) {
      return jsonResponse(401, {
        error: 'Unauthorized',
        message: 'Missing or invalid X-Handshake-Token header.',
      });
    }

    // ── Validate API key is configured ──────────────────────────────────
    if (!NVIDIA_API_KEY) {
      return jsonResponse(500, {
        error: 'Server Error',
        message: 'NVIDIA_API_KEY is not configured on the server. Add it in Worker Settings > Variables.',
      });
    }

    // ── Forward to NVIDIA ───────────────────────────────────────────────
    try {
      // Enforce request body size limit BEFORE reading (prevent DoS via oversized payloads)
      const contentLength = parseInt(request.headers.get('Content-Length') || '0', 10);
      if (contentLength > 1024 * 1024) {  // 1 MB max
        return jsonResponse(413, {
          error: 'Payload Too Large',
          message: 'Request body exceeds 1 MB limit.',
        });
      }

      const body = await request.text();

      // Double-check actual body size (Content-Length may be absent or inaccurate)
      if (body.length > 1024 * 1024) {
        return jsonResponse(413, {
          error: 'Payload Too Large',
          message: 'Request body exceeds 1 MB limit.',
        });
      }
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), UPSTREAM_TIMEOUT_MS);

      const nvResponse = await fetch(NVIDIA_ENDPOINT, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${NVIDIA_API_KEY}`,
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body,
        signal: controller.signal,
      });
      clearTimeout(timeout);

      const responseText = await nvResponse.text();
      const contentType = nvResponse.headers.get('content-type') || 'application/json';
      const durationMs = String(Date.now() - startedAt);

      return new Response(responseText, {
        status: nvResponse.status,
        headers: {
          ...corsHeaders,
          'Content-Type': contentType,
          'X-AutoNage-Upstream-Duration-Ms': durationMs,
        },
      });

    } catch (err) {
      if (err.name === 'AbortError') {
        return jsonResponse(504, {
          error: 'Gateway Timeout',
          message: `NVIDIA API did not respond within ${Math.round(UPSTREAM_TIMEOUT_MS / 1000)} seconds. Reduce AI batch size or try again later.`,
        }, {
          'X-AutoNage-Upstream-Duration-Ms': String(Date.now() - startedAt),
        });
      }
      console.error('Proxy error:', err.message);
      return jsonResponse(502, {
        error: 'Bad Gateway',
        message: `Failed to reach NVIDIA API: ${err.message}`,
      }, {
        'X-AutoNage-Upstream-Duration-Ms': String(Date.now() - startedAt),
      });
    }
  },
};
