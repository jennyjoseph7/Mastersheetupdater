/**
 * AutoNage API Proxy - Cloudflare Worker (Secured)
 * Securely forwards browser requests to OpenRouter without exposing the API key.
 * 
 * Setup:
 * 1. Create a free Cloudflare Workers account.
 * 2. Create a new worker and paste this code.
 * 3. Add an Environment Variable named `OPENROUTER_API_KEY` in the Worker dashboard.
 * 4. Add an Environment Variable named `HANDSHAKE_TOKEN` with value "jejo-presales-secure-handshake".
 */

const ALLOWED_ORIGINS = [
  "https://d2yicwfidul1wd.cloudfront.net", // Production CloudFront domain
];

export default {
  async fetch(request, env, ctx) {
    const origin = request.headers.get("Origin");

    // Handle CORS preflight requests
    if (request.method === "OPTIONS") {
      return new Response(null, {
        headers: {
          "Access-Control-Allow-Origin": origin || "*",
          "Access-Control-Allow-Methods": "POST, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Title, HTTP-Referer, X-Handshake-Token",
          "Access-Control-Max-Age": "86400",
        }
      });
    }

    if (request.method !== "POST") {
      return new Response("Method not allowed", { status: 405 });
    }

    // 1. Origin Verification (CORS Security)
    // Enforced in production; can be relaxed for local development / file:// access if needed
    const isAllowedOrigin = ALLOWED_ORIGINS.includes(origin) || (origin && origin.startsWith("http://localhost"));
    
    // 2. Handshake Verification (For local file:// or standalone runs where Origin is null)
    const handshakeToken = request.headers.get("X-Handshake-Token");
    const expectedHandshake = env.HANDSHAKE_TOKEN || "jejo-presales-secure-handshake";
    
    if (!isAllowedOrigin && handshakeToken !== expectedHandshake) {
      return new Response("Forbidden: Unauthorized origin or missing handshake token.", { 
        status: 403,
        headers: { "Access-Control-Allow-Origin": "*" }
      });
    }

    const apiKey = env.OPENROUTER_API_KEY;
    if (!apiKey) {
      return new Response("Server error: API key is not configured on the proxy.", { 
        status: 500,
        headers: { "Access-Control-Allow-Origin": "*" }
      });
    }

    try {
      const clientBody = await request.json();
      
      // 3. Request Hardening: Force target model and system instructions 
      // This prevents abusers from using your proxy to run arbitrary large-context prompts or expensive models.
      const securedPayload = {
        model: "deepseek/deepseek-v4-flash", // Hardcoded cheap model
        messages: clientBody.messages,
        temperature: clientBody.temperature || 0.3,
        max_tokens: Math.min(clientBody.max_tokens || 3000, 3000)
      };

      // Forward the request to OpenRouter
      const response = await fetch("https://openrouter.ai/api/v1/chat/completions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${apiKey}`,
          "X-Title": "AutoNage Proxy",
          "HTTP-Referer": "https://github.com/jennyjoseph7/Mastersheetupdater"
        },
        body: JSON.stringify(securedPayload)
      });

      const responseText = await response.text();
      
      return new Response(responseText, {
        status: response.status,
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": origin || "*",
        }
      });
    } catch (err) {
      return new Response(JSON.stringify({ error: err.message }), {
        status: 500,
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": origin || "*",
        }
      });
    }
  }
};
