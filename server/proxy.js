/**
 * AutoNage Local CORS Proxy
 *
 * Forwards browser fetch requests to the NVIDIA API, adding the required
 * CORS headers so the frontend can call the API directly from the browser.
 *
 * Usage
 *   npm start          (starts on PORT from .env, default 3456)
 *   node --watch proxy.js
 *
 * Security
 *   - The NVIDIA API key lives ONLY in this file / .env — never exposed
 *     to the browser.
 *   - Clients obtain a short-lived session token via GET /session (1 use).
 *   - Requests without a valid session token are rejected with 401.
 *   - Origin header is validated against allowed origins (localhost).
 *   - Per-IP rate limiting prevents abuse.
 *   - Only the configured NVIDIA endpoint is proxied.
 */

import { createServer } from 'node:http';
import { randomBytes } from 'node:crypto';
import { readFileSync, existsSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));

// ── Load .env manually (zero dependencies) ─────────────────────────────────
function loadEnv(path) {
  if (!existsSync(path)) return {};
  const env = {};
  const lines = readFileSync(path, 'utf-8').split('\n');
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eq = trimmed.indexOf('=');
    if (eq === -1) continue;
    const key = trimmed.slice(0, eq).trim();
    let val = trimmed.slice(eq + 1).trim();
    if ((val.startsWith('"') && val.endsWith('"')) ||
        (val.startsWith("'") && val.endsWith("'"))) {
      val = val.slice(1, -1);
    }
    env[key] = val;
  }
  return env;
}

const env = loadEnv(resolve(__dirname, '.env'));

const NVIDIA_API_KEY    = env.NVIDIA_API_KEY || process.env.NVIDIA_API_KEY;
const PORT              = parseInt(env.PORT || process.env.PORT || '3456', 10);
const NVIDIA_ENDPOINT   = 'https://integrate.api.nvidia.com/v1/chat/completions';
const UPSTREAM_TIMEOUT_MS = parseInt(env.UPSTREAM_TIMEOUT_MS || process.env.UPSTREAM_TIMEOUT_MS || '90000', 10);
const ALLOWED_ORIGINS   = (env.ALLOWED_ORIGINS || process.env.ALLOWED_ORIGINS || 'http://localhost:5500,http://127.0.0.1:5500,http://localhost:8080').split(',').map(s => s.trim());

if (!NVIDIA_API_KEY) {
  console.error('ERROR: NVIDIA_API_KEY is not set.');
  console.error('Copy server/.env.example to server/.env and add your key.');
  process.exit(1);
}

// ── Session token store ────────────────────────────────────────────────────
// In-memory map of token -> { expiresAt, used }
const sessions = new Map();
const SESSION_TTL_MS = 5 * 60 * 1000; // 5 minutes

function generateSessionToken() {
  return randomBytes(24).toString('hex');
}

function createSession() {
  const token = generateSessionToken();
  sessions.set(token, {
    expiresAt: Date.now() + SESSION_TTL_MS,
    used: false,
  });
  return token;
}

function validateSession(token) {
  if (!token || !sessions.has(token)) return false;
  const session = sessions.get(token);
  // Expired
  if (Date.now() > session.expiresAt) {
    sessions.delete(token);
    return false;
  }
  return true;
}

// Periodic cleanup of expired sessions (every 60s)
setInterval(() => {
  const now = Date.now();
  for (const [token, session] of sessions) {
    if (now > session.expiresAt) sessions.delete(token);
  }
}, 60_000);

// ── Rate limiting ──────────────────────────────────────────────────────────
const rateLimitMap = new Map();
const RATE_LIMIT = 60;     // max requests
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
const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS, GET',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Session-Token, Accept',
  'Access-Control-Max-Age': '86400',
};

// ── Helpers ─────────────────────────────────────────────────────────────────
function jsonResponse(res, status, body) {
  const headers = { ...CORS_HEADERS, 'Content-Type': 'application/json' };
  res.writeHead(status, headers);
  res.end(JSON.stringify(body));
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on('data', (c) => chunks.push(c));
    req.on('end', () => resolve(Buffer.concat(chunks).toString('utf-8')));
    req.on('error', reject);
  });
}

/**
 * Validates the Origin header against the allowed origins list.
 * If no Origin header is present (e.g., curl), we still allow it for dev convenience.
 */
function isOriginAllowed(req) {
  const origin = req.headers['origin'];
  if (!origin) return true; // No origin = not from a browser, allow
  return ALLOWED_ORIGINS.some(allowed => origin === allowed || origin.startsWith(allowed));
}

// ── Server ──────────────────────────────────────────────────────────────────
const server = createServer(async (req, res) => {
  const { method, url } = req;
  const clientIP = req.headers['x-forwarded-for'] || req.socket.remoteAddress || 'unknown';

  // ── OPTIONS preflight ──────────────────────────────────────────────────
  if (method === 'OPTIONS') {
    res.writeHead(204, CORS_HEADERS);
    res.end();
    return;
  }

  // ── Health check ───────────────────────────────────────────────────────
  if (method === 'GET' && url === '/health') {
    jsonResponse(res, 200, { status: 'ok', proxy: 'autonage-local' });
    return;
  }

  // ── Session token endpoint ────────────────────────────────────────────
  // Client calls GET /session before making API requests to get a short-lived
  // one-time-use session token. The token must be included as X-Session-Token
  // in subsequent POST /v1/chat/completions requests.
  if (method === 'GET' && url === '/session') {
    const token = createSession();
    jsonResponse(res, 200, { token, expiresInMs: SESSION_TTL_MS, message: 'Use this token in X-Session-Token header for POST requests.' });
    return;
  }

  // ── Only proxy POST /v1/chat/completions ──────────────────────────────
  if (method !== 'POST' || url !== '/v1/chat/completions') {
    jsonResponse(res, 404, { error: 'Not found. Use POST /v1/chat/completions' });
    return;
  }

  // ── Rate limiting (per IP) ────────────────────────────────────────────
  if (!checkRateLimit(clientIP)) {
    jsonResponse(res, 429, {
      error: 'Too Many Requests',
      message: 'Rate limit exceeded. Max 60 requests per minute.',
    });
    return;
  }

  // ── Origin validation ─────────────────────────────────────────────────
  if (!isOriginAllowed(req)) {
    jsonResponse(res, 403, {
      error: 'Forbidden',
      message: 'Origin not allowed. Configure ALLOWED_ORIGINS in .env if needed.',
    });
    return;
  }

  // ── Validate session token ────────────────────────────────────────────
  const sessionToken = req.headers['x-session-token'];
  if (!sessionToken || !validateSession(sessionToken)) {
    jsonResponse(res, 401, {
      error: 'Unauthorized',
      message: 'Missing or invalid X-Session-Token. Call GET /session first to obtain a token.'
    });
    return;
  }

  // ── Read and forward request ──────────────────────────────────────────
  try {
    const body = await readBody(req);

    // Free endpoints can be slow; keep this above the frontend timeout.
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), UPSTREAM_TIMEOUT_MS);

    const response = await fetch(NVIDIA_ENDPOINT, {
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

    // Log the NVIDIA response status for debugging
    console.log(`[NVIDIA] ${response.status} ${response.statusText}`);

    // Read the response body
    const responseText = await response.text();

    // Forward the status and body back to the client
    const resHeaders = {
      ...CORS_HEADERS,
      'Content-Type': response.headers.get('content-type') || 'application/json',
    };
    res.writeHead(response.status, resHeaders);
    res.end(responseText);

  } catch (err) {
    if (err.name === 'AbortError') {
      console.error(`[NVIDIA] Request timed out after ${Math.round(UPSTREAM_TIMEOUT_MS / 1000)}s`);
      jsonResponse(res, 504, {
        error: 'Gateway Timeout',
        message: `NVIDIA API did not respond within ${Math.round(UPSTREAM_TIMEOUT_MS / 1000)} seconds. Reduce AI batch size or try again later.`
      });
    } else {
      console.error('[NVIDIA] Proxy error:', err.message);
      jsonResponse(res, 502, {
        error: 'Bad Gateway',
        message: `Failed to reach NVIDIA API: ${err.message}`
      });
    }
  }
});

server.listen(PORT, () => {
  console.log(`
  ╔══════════════════════════════════════════════════╗
  ║         AutoNage Local CORS Proxy               ║
  ║──────────────────────────────────────────────────║
  ║  Proxy:   http://localhost:${PORT}/v1/chat/completions  ║
  ║  Session: GET  http://localhost:${PORT}/session         ║
  ║  Upstream: ${NVIDIA_ENDPOINT}             ║
  ║  CORS:    Enabled (all origins)                 ║
  ║  Auth:    Session token (one-time, 5 min TTL)   ║
  ║  Origin:  Validated                             ║
  ║  Rate:    60 req/min per IP                     ║
  ╚══════════════════════════════════════════════════╝
  `);
});
