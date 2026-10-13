const SYSTEM_PROMPTS = Object.freeze({
  niknolig: "You are the NIKNOLIG assistant. Answer only using the information supplied for NIKNOLIG.",
  "elektro-engel": "You are the Elektro-Engel assistant. Answer only using the information supplied for Elektro-Engel.",
  "niknolig-defense": "You are the NIKNOLIG Defense assistant. Answer only using the information supplied for NIKNOLIG Defense.",
});

const FALLBACK = "Der KI-Dienst ist gerade nicht verfügbar. Bitte versuche es später erneut.";
const MAX_INPUT_BYTES = 8_192;
const MAX_INPUT_CHARACTERS = 4_000;
const MAX_OUTPUT_TOKENS = 300;
const OPENAI_TIMEOUT_MS = 20_000;
const ACCESS_KEYS_TTL_MS = 5 * 60_000;

let cachedAccessKeys;
let cachedAccessKeysAt = 0;

function json(body, status) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
  });
}

function fallback(status = 503) {
  return json({ error: "service_unavailable", fallback: true, output: FALLBACK }, status);
}

function decodeBase64Url(value) {
  const base64 = value.replace(/-/g, "+").replace(/_/g, "/");
  return Uint8Array.from(atob(base64.padEnd(Math.ceil(base64.length / 4) * 4, "=")), (char) => char.charCodeAt(0));
}

function decodeJsonSegment(value) {
  return JSON.parse(new TextDecoder().decode(decodeBase64Url(value)));
}

function accessIssuer(env) {
  const domain = env.ACCESS_TEAM_DOMAIN;
  if (typeof domain !== "string" || !/^(?:[a-z0-9-]+\.)*cloudflareaccess\.com$/i.test(domain)) {
    return null;
  }
  return `https://${domain}`;
}

async function getAccessKeys(issuer, now) {
  if (cachedAccessKeys && now - cachedAccessKeysAt < ACCESS_KEYS_TTL_MS) {
    return cachedAccessKeys;
  }
  const response = await fetch(`${issuer}/cdn-cgi/access/certs`, {
    headers: { accept: "application/json" },
    signal: AbortSignal.timeout(5_000),
  });
  if (!response.ok) {
    throw new Error("Access signing keys unavailable");
  }
  const body = await response.json();
  if (!Array.isArray(body.keys)) {
    throw new Error("Invalid Access signing keys");
  }
  cachedAccessKeys = body.keys;
  cachedAccessKeysAt = now;
  return cachedAccessKeys;
}

async function authenticate(request, env, system, now = Date.now()) {
  const issuer = accessIssuer(env);
  const audience = env.SYSTEM_AUDIENCES?.[system];
  const authorization = request.headers.get("authorization") ?? "";
  const token = authorization.match(/^******;
  if (!issuer || typeof audience !== "string" || !audience || !token) {
    return { status: 401 };
  }

  try {
    const segments = token.split(".");
    if (segments.length !== 3) {
      return { status: 401 };
    }
    const header = decodeJsonSegment(segments[0]);
    const claims = decodeJsonSegment(segments[1]);
    if (header.alg !== "RS256" || typeof header.kid !== "string") {
      return { status: 401 };
    }
    const keys = await getAccessKeys(issuer, now);
    const jwk = keys.find((key) => key.kid === header.kid && key.kty === "RSA");
    if (!jwk) {
      return { status: 401 };
    }
    const publicKey = await crypto.subtle.importKey(
      "jwk",
      jwk,
      { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
      false,
      ["verify"],
    );
    const validSignature = await crypto.subtle.verify(
      "RSASSA-PKCS1-v1_5",
      publicKey,
      decodeBase64Url(segments[2]),
      new TextEncoder().encode(`${segments[0]}.${segments[1]}`),
    );
    const audiences = Array.isArray(claims.aud) ? claims.aud : [claims.aud];
    if (
      !validSignature
      || claims.iss !== issuer
      || !audiences.includes(audience)
      || typeof claims.sub !== "string"
      || !claims.sub
      || !Number.isFinite(claims.exp)
      || claims.exp <= Math.floor(now / 1_000)
      || (claims.nbf !== undefined && (!Number.isFinite(claims.nbf) || claims.nbf > Math.floor(now / 1_000)))
    ) {
      return { status: 401 };
    }
    return { principal: claims.sub };
  } catch {
    return { status: 401 };
  }
}

async function handleAssist(request, env) {
  if (!env.OPENAI_API_KEY || !env.AI_LIMITER || typeof env.AI_LIMITER.limit !== "function") {
    return fallback();
  }

  const contentType = request.headers.get("content-type") ?? "";
  const declaredLength = Number(request.headers.get("content-length") ?? 0);
  if (!contentType.toLowerCase().startsWith("application/json")) {
    return json({ error: "unsupported_media_type" }, 415);
  }
  if (declaredLength > MAX_INPUT_BYTES) {
    return json({ error: "request_too_large" }, 413);
  }

  let payload;
  try {
    const text = await request.text();
    if (new TextEncoder().encode(text).byteLength > MAX_INPUT_BYTES) {
      return json({ error: "request_too_large" }, 413);
    }
    payload = JSON.parse(text);
  } catch {
    return json({ error: "invalid_json" }, 400);
  }

  if (
    !payload
    || typeof payload !== "object"
    || Array.isArray(payload)
    || Object.keys(payload).some((key) => !["system", "input"].includes(key))
    || typeof payload.system !== "string"
    || !Object.hasOwn(SYSTEM_PROMPTS, payload.system)
    || typeof payload.input !== "string"
    || !payload.input.trim()
    || payload.input.length > MAX_INPUT_CHARACTERS
  ) {
    return json({ error: "invalid_request" }, 400);
  }

  const auth = await authenticate(request, env, payload.system);
  if (auth.status) {
    return json({ error: "unauthorized" }, auth.status);
  }

  try {
    const { success } = await env.AI_LIMITER.limit({ key: `${payload.system}:${auth.principal}` });
    if (!success) {
      return json({ error: "rate_limited" }, 429);
    }
  } catch {
    return fallback();
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), OPENAI_TIMEOUT_MS);
  try {
    const response = await fetch("https://api.openai.com/v1/responses", {
      method: "POST",
      headers: {
        authorization: `******
        "content-type": "application/json",
      },
      body: JSON.stringify({
        model: "gpt-4o-mini",
        store: false,
        max_output_tokens: MAX_OUTPUT_TOKENS,
        input: [
          { role: "system", content: SYSTEM_PROMPTS[payload.system] },
          { role: "user", content: payload.input.trim() },
        ],
      }),
      signal: controller.signal,
    });
    if (!response.ok) {
      return fallback();
    }
    const result = await response.json();
    const output = Array.isArray(result.output)
      ? result.output
        .filter((item) => item.type === "message")
        .flatMap((item) => Array.isArray(item.content) ? item.content : [])
        .filter((item) => item.type === "output_text" && typeof item.text === "string")
        .map((item) => item.text)
        .join("")
      : "";
    if (!output) {
      return fallback();
    }
    return json({
      system: payload.system,
      output,
      usage: {
        input_tokens: Number.isInteger(result.usage?.input_tokens) ? result.usage.input_tokens : null,
        output_tokens: Number.isInteger(result.usage?.output_tokens) ? result.usage.output_tokens : null,
      },
    }, 200);
  } catch {
    return fallback();
  } finally {
    clearTimeout(timeout);
  }
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname !== "/v1/assist") {
      return json({ error: "not_found" }, 404);
    }
    if (request.method !== "POST") {
      return json({ error: "method_not_allowed" }, 405);
    }
    return handleAssist(request, env);
  },
};
