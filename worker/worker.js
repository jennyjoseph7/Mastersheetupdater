/**
 * AutoNage Proxy — Cloudflare Worker
 *
 * Features:
 *   - Proxies /gryd/* POST requests to gryd backend (with CORS + origin stripping)
 *   - Proxies /v1/chat/completions to NVIDIA API
 *   - Handshake token auth for NVIDIA routes
 *   - CORS with origin whitelist
 *   - Rate limiting
 */

// ── Config ─────────────────────────────────────────────────────────────────
const ALLOWED_ORIGINS = [
  'https://jennyjoseph7.github.io',
  'http://localhost:3000',
  'http://127.0.0.1:3000',
  'http://192.168.1.2:3000',
  'http://192.168.1.4:3000',
];

const NVIDIA_ENDPOINT = 'https://integrate.api.nvidia.com/v1/chat/completions';
const GRYD_ENDPOINT = 'https://autobot-webapp-dev.gryd.in';
const DEFAULT_UPSTREAM_TIMEOUT_MS = 90_000;

// ── Rate limiting ──────────────────────────────────────────────────────────
const rateLimitMap = new Map();
const RATE_LIMIT = 1000;
const RATE_WINDOW = 60_000;

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

// ── CORS headers (origin-validated) ─────────────────────────────────────────
function corsHeaders(origin) {
  const allowed = ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0];
  return {
    'Access-Control-Allow-Origin': allowed,
    'Access-Control-Allow-Methods': 'POST, OPTIONS, GET',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Handshake-Token, X-GRYD-ENTERPRISE-ID, X-GRYD-TOKEN, X-GRYD-SESSION-ID, X-GRYD-SIGNUP-TOKEN, X-GRYD-APPLICATION-ID, Accept',
    'Access-Control-Max-Age': '86400',
    'Vary': 'Origin',
  };
}

function jsonResponse(status, body, origin, extraHeaders = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders(origin), 'Content-Type': 'application/json', ...extraHeaders },
  });
}

// ── Request handler ─────────────────────────────────────────────────────────
export default {
  async fetch(request, env, ctx) {
    const { method } = request;
    const clientIP = request.headers.get('CF-Connecting-IP') || 'unknown';
    const startedAt = Date.now();
    const url = new URL(request.url);
    const origin = request.headers.get('Origin') || '';

    const NVIDIA_API_KEY = env.NVIDIA_API_KEY;
    const UPSTREAM_TIMEOUT_MS = Number(env.UPSTREAM_TIMEOUT_MS) > 0
      ? Number(env.UPSTREAM_TIMEOUT_MS) : DEFAULT_UPSTREAM_TIMEOUT_MS;

    // ── Preflight ─────────────────────────────────────────────────────
    if (method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders(origin) });
    }

    // ── Auth check ───────────────────────────────────────────────────
    if (method === 'GET' && url.pathname === '/auth/check') {
      const token = request.headers.get('X-GRYD-TOKEN');
      if (!token) return jsonResponse(401, { error: 'Unauthorized', message: 'No token' }, origin);
      try {
        const resp = await fetch(GRYD_ENDPOINT + '/gryd/execute/get_llm_response/ai_service', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json', 'Accept': 'application/json',
            'x-gryd-enterprise-id': 'autocrm', 'x-gryd-application-id': 'autocrm',
            'x-gryd-token': token,
            'x-gryd-session-id': request.headers.get('X-GRYD-SESSION-ID') || '',
          },
          body: JSON.stringify({ kwargs: { user_query: 'ping', system_prompt: 'respond with OK', model_identifier: 'gcp-gemini-3.1-flash-lite-preview' } }),
          signal: AbortSignal.timeout(10000),
        });
        if (resp.status === 401 || resp.status === 403) {
          return jsonResponse(401, { error: 'Session expired', message: 'Token rejected by gryd.' }, origin);
        }
        if (resp.status === 526 || resp.status === 525 || resp.status === 520 || resp.status >= 500) {
          // ponytail: gryd origin down/cert expired — don't kill session, trust client
          return jsonResponse(200, { valid: true, degraded: true, upstreamStatus: resp.status }, origin);
        }
        return jsonResponse(200, { valid: true }, origin);
      } catch {
        // If gryd is unreachable, trust the token (degraded mode)
        return jsonResponse(200, { valid: true, degraded: true }, origin);
      }
    }

    // ── Health check ───────────────────────────────────────────────────
    if (method === 'GET') {
      if (url.pathname !== '/health') {
        return jsonResponse(404, { error: 'Not found. Use GET /health' }, origin);
      }
      return jsonResponse(200, { status: 'ok', proxy: 'autonage-cloudflare' }, origin);
    }

    if (method !== 'POST') {
      return jsonResponse(404, { error: 'Use POST' }, origin);
    }

    // ── Rate limit ────────────────────────────────────────────────────
    if (!checkRateLimit(clientIP)) {
      return jsonResponse(429, { error: 'Too Many Requests', message: 'Rate limit exceeded.' }, origin);
    }

    // ── GRYD LLM TRANSLATION ROUTE ─────────────────────────────────────
    // Translates NVIDIA-format chat requests to gryd's LLM endpoint
    if (url.pathname === '/gryd/v1/chat/completions') {
      const body = await request.text();
      let nvidiaReq;
      try { nvidiaReq = JSON.parse(body); } catch { return jsonResponse(400, { error: 'Invalid JSON' }, origin); }

      const messages = nvidiaReq.messages || [];
      let systemPrompt = '';
      let userQuery = '';
      for (const msg of messages) {
        if (msg.role === 'system') systemPrompt = msg.content || '';
        if (msg.role === 'user') userQuery = msg.content || '';
      }

      const grydBody = JSON.stringify({
        kwargs: {
          user_query: userQuery,
          system_prompt: systemPrompt,
          model_identifier: env.GRYD_MODEL || 'gcp-gemini-3.1-flash-lite-preview'
        }
      });

      const grydHeaders = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'x-gryd-enterprise-id': 'autocrm',
        'x-gryd-application-id': 'autocrm'
      };
      for (const h of ['x-gryd-token', 'x-gryd-session-id', 'x-gryd-signup-token']) {
        const v = request.headers.get(h);
        if (v) grydHeaders[h] = v;
      }
      // Inject signup token from Worker env if frontend didn't send one
      if (!grydHeaders['x-gryd-signup-token'] && env.GRYD_SIGNUP_TOKEN) {
        grydHeaders['x-gryd-signup-token'] = env.GRYD_SIGNUP_TOKEN;
      }

      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 90000);
      try {
        const upstream = await fetch(GRYD_ENDPOINT + '/gryd/execute/get_llm_response/ai_service', {
          method: 'POST', headers: grydHeaders, body: grydBody, signal: controller.signal,
        });
        clearTimeout(timeout);
        const responseText = await upstream.text();
        if (!upstream.ok) {
          if (upstream.status === 526) return jsonResponse(502, { error: 'Bad Gateway', message: 'Gryd origin cert expired (526). Contact gryd infra to renew *.gryd.in.' }, origin);
          if (upstream.status >= 500) return jsonResponse(502, { error: 'Gryd LLM error', message: responseText.slice(0, 500) || `Upstream ${upstream.status}` }, origin);
          return jsonResponse(upstream.status, { error: 'Gryd LLM error', message: responseText.slice(0, 500) }, origin);
        }
        let content = responseText;
        if (content.startsWith('"') && content.endsWith('"')) {
          try { content = JSON.parse(content); } catch {
            content = content.slice(1, -1).replace(/\\"/g, '"').replace(/\\\\/g, '\\').replace(/\\n/g, '\n');
          }
        }
        if (typeof content !== 'string') content = JSON.stringify(content);
        return jsonResponse(200, { choices: [{ message: { content: content } }] }, origin);
      } catch (err) {
        clearTimeout(timeout);
        if (err.name === 'AbortError') return jsonResponse(504, { error: 'Gateway Timeout', message: 'Gryd LLM timed out.' }, origin);
        return jsonResponse(502, { error: 'Bad Gateway', message: 'Upstream LLM request failed.' }, origin);
      }
    }

    // ── GRYD PROXY ROUTE (login, etc.) ───────────────────────────────
    // Forwards /gryd/* requests to gryd backend, strips browser origin.
    // Signup token is injected from Worker env (GRYD_SIGNUP_TOKEN) so the
    // frontend never needs to expose it.
    if (url.pathname.startsWith('/gryd/')) {
      const grydHeaders = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      };

      for (const h of ['x-gryd-enterprise-id', 'x-gryd-token', 'x-gryd-session-id', 'x-gryd-signup-token', 'x-gryd-application-id']) {
        const val = request.headers.get(h);
        if (val) grydHeaders[h] = val;
      }
      // Inject signup token from Worker env if frontend didn't send one
      if (!grydHeaders['x-gryd-signup-token'] && env.GRYD_SIGNUP_TOKEN) {
        grydHeaders['x-gryd-signup-token'] = env.GRYD_SIGNUP_TOKEN;
      }

      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 30000);

      try {
        const body = await request.text();
        if (body.length > 1024 * 1024) {
          return jsonResponse(413, { error: 'Payload Too Large', message: 'Request body exceeds 1 MB limit.' }, origin);
        }
        const upstream = await fetch(GRYD_ENDPOINT + url.pathname, {
          method: 'POST', headers: grydHeaders, body, signal: controller.signal,
        });
        clearTimeout(timeout);
        const text = await upstream.text();
        // ponytail: never forward 526/5xx as-is — map to 502 JSON with CORS so frontend gets usable error
        if (upstream.status === 526 || upstream.status === 525 || upstream.status === 520) {
          return jsonResponse(502, { error: 'Bad Gateway', message: 'Gryd origin cert expired (526). Gryd infra must renew *.gryd.in on 34.14.184.212.', upstreamStatus: upstream.status }, origin);
        }
        if (upstream.status >= 500) {
          return jsonResponse(502, { error: 'Bad Gateway', message: text.slice(0, 500) || `Upstream ${upstream.status}` }, origin);
        }
        const ctype = upstream.headers.get('content-type') || 'application/json';
        // ensure 4xx HTML doesn't leak as text/plain — wrap as JSON
        if (upstream.status >= 400 && !ctype.includes('application/json')) {
          return jsonResponse(upstream.status, { error: 'Upstream error', message: text.slice(0, 500) }, origin);
        }
        return new Response(text, { status: upstream.status, headers: { ...corsHeaders(origin), 'Content-Type': ctype } });
      } catch (err) {
        clearTimeout(timeout);
        if (err.name === 'AbortError') return jsonResponse(504, { error: 'Gateway Timeout', message: 'Gryd backend timed out.' }, origin);
        return jsonResponse(502, { error: 'Bad Gateway', message: 'Upstream gryd request failed.' }, origin);
      }
    }

    // ── NVIDIA PROXY ────────────────────────────────────────────────────
    const HANDSHAKE_TOKEN = env.HANDSHAKE_TOKEN;
    if (HANDSHAKE_TOKEN) {
      const token = request.headers.get('X-Handshake-Token');
      if (!token || token !== HANDSHAKE_TOKEN) {
        return jsonResponse(401, { error: 'Unauthorized', message: 'Missing or invalid handshake token.' }, origin);
      }
    }
    if (!NVIDIA_API_KEY) {
      return jsonResponse(500, { error: 'Server Error', message: 'NVIDIA_API_KEY not configured on the Worker.' }, origin);
    }

    try {
      const contentLength = parseInt(request.headers.get('Content-Length') || '0', 10);
      if (contentLength > 1024 * 1024) {
        return jsonResponse(413, { error: 'Payload Too Large', message: 'Request body exceeds 1 MB limit.' }, origin);
      }
      const body = await request.text();
      if (body.length > 1024 * 1024) {
        return jsonResponse(413, { error: 'Payload Too Large', message: 'Request body exceeds 1 MB limit.' }, origin);
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
        headers: { ...corsHeaders(origin), 'Content-Type': contentType, 'X-AutoNage-Upstream-Duration-Ms': durationMs },
      });
    } catch (err) {
      if (err.name === 'AbortError') {
        return jsonResponse(504, { error: 'Gateway Timeout', message: `NVIDIA API did not respond within ${Math.round(UPSTREAM_TIMEOUT_MS / 1000)} seconds.` }, origin);
      }
      return jsonResponse(502, { error: 'Bad Gateway', message: 'Failed to reach NVIDIA API.' }, origin);
    }
  },
};
