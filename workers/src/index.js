const APP_AREAS = new Set(["niknolig", "niknolig-defense"]);
const ALLOWED_METHODS = new Set(["GET", "HEAD"]);

function responseHeaders(source) {
  const headers = new Headers(source);
  headers.set("X-Content-Type-Options", "nosniff");
  headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  headers.set("X-Frame-Options", "DENY");
  headers.set(
    "Content-Security-Policy",
    "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'self' mailto:",
  );
  headers.set("Permissions-Policy", "camera=(), microphone=(), geolocation=()");
  return headers;
}

function jsonError(status, requestId) {
  return new Response(
    JSON.stringify({ error: "service_unavailable", requestId }),
    {
      status,
      headers: responseHeaders({
        "Cache-Control": "no-store",
        "Content-Type": "application/json; charset=utf-8",
      }),
    },
  );
}

function logRequest({ app, method, status, requestId, event }) {
  console.log(
    JSON.stringify({
      event,
      app,
      method,
      status,
      requestId,
    }),
  );
}

export default {
  async fetch(request, env) {
    const requestId = crypto.randomUUID();
    const app = APP_AREAS.has(env.APP_AREA) ? env.APP_AREA : "unconfigured";
    const method = ALLOWED_METHODS.has(request.method) ? request.method : "other";

    if (!APP_AREAS.has(env.APP_AREA)) {
      logRequest({ app, method, status: 503, requestId, event: "configuration_error" });
      return jsonError(503, requestId);
    }

    if (!ALLOWED_METHODS.has(request.method)) {
      const headers = responseHeaders({
        Allow: "GET, HEAD",
        "Cache-Control": "no-store",
        "Content-Type": "application/json; charset=utf-8",
      });
      logRequest({ app, method, status: 405, requestId, event: "request" });
      return new Response(JSON.stringify({ error: "method_not_allowed", requestId }), {
        status: 405,
        headers,
      });
    }

    if (!env.ASSETS || typeof env.ASSETS.fetch !== "function") {
      logRequest({ app, method, status: 503, requestId, event: "asset_binding_missing" });
      return jsonError(503, requestId);
    }

    try {
      const assetResponse = await env.ASSETS.fetch(request);
      const response = new Response(
        request.method === "HEAD" ? null : assetResponse.body,
        {
          status: assetResponse.status,
          statusText: assetResponse.statusText,
          headers: responseHeaders(assetResponse.headers),
        },
      );
      logRequest({
        app,
        method,
        status: response.status,
        requestId,
        event: "request",
      });
      return response;
    } catch {
      logRequest({ app, method, status: 503, requestId, event: "asset_error" });
      return jsonError(503, requestId);
    }
  },
};
