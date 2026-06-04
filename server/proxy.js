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
 *   - Requests without a valid handshake token are rejected with 401.
 *   - Only the configured NVIDIA endpoint is proxied.
 */

import { createServer } from 'node:http';
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
    // Strip surrounding quotes if present
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
const HANDSHAKE_TOKEN   = env.HANDSHAKE_TOKEN || process.env.HANDSHAKE_TOKEN || 'jejo-presales-secure-handshake';
const NVIDIA_ENDPOINT   = 'https://integrate.api.nvidia.com/v1/chat/completions';
const UPSTREAM_TIMEOUT_MS = parseInt(env.UPSTREAM_TIMEOUT_MS || process.env.UPSTREAM_TIMEOUT_MS || '90000', 10);

if (!NVIDIA_API_KEY) {
  console.error('ERROR: NVIDIA_API_KEY is not set.');
  console.error('Copy server/.env.example to server/.env and add your key.');
  process.exit(1);
}

// ── CORS headers ────────────────────────────────────────────────────────────
const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Handshake-Token, Accept',
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

// ── Server ──────────────────────────────────────────────────────────────────
const server = createServer(async (req, res) => {
  const { method, url } = req;

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

  // ── Only proxy POST /v1/chat/completions ──────────────────────────────
  if (method !== 'POST' || url !== '/v1/chat/completions') {
    jsonResponse(res, 404, { error: 'Not found. Use POST /v1/chat/completions' });
    return;
  }

  // ── Validate handshake token ──────────────────────────────────────────
  const token = req.headers['x-handshake-token'];
  if (!token || token !== HANDSHAKE_TOKEN) {
    jsonResponse(res, 401, {
      error: 'Unauthorized',
      message: 'Missing or invalid X-Handshake-Token header. Set proxyHandshakeToken in config.js to match server/.env.'
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
  ║  Upstream: ${NVIDIA_ENDPOINT.slice(0, 35)}  ║
  ║  CORS:    Enabled (all origins)                 ║
  ╚══════════════════════════════════════════════════╝
  `);
});
