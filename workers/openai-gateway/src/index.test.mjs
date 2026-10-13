import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import worker from "./index.mjs";

const originalFetch = globalThis.fetch;
const audienceBySystem = {
  niknolig: "aud-niknolig",
  "elektro-engel": "aud-elektro",
  "niknolig-defense": "aud-defense",
};
const env = {
  ACCESS_TEAM_DOMAIN: "example.cloudflareaccess.com",
  SYSTEM_AUDIENCES: JSON.stringify(audienceBySystem),
  OPENAI_API_KEY: "test",
  AI_LIMITER: { limit: async () => ({ success: true }) },
};

let signingKey;
let publicJwk;
let openAIRequest;
let openAIResponse = {
  output: [{ type: "message", content: [{ type: "output_text", text: "Testantwort" }] }],
  usage: { input_tokens: 12, output_tokens: 8 },
};

function encodeBase64Url(bytes) {
  return btoa(String.fromCharCode(...new Uint8Array(bytes)))
    .replace(/=/g, "")
    .replace(/\+/g, "-")
    .replace(/\//g, "_");
}

async function accessToken(audience, overrides = {}) {
  const header = encodeBase64Url(new TextEncoder().encode(JSON.stringify({ alg: "RS256", kid: "test-key" })));
  const claims = encodeBase64Url(new TextEncoder().encode(JSON.stringify({
    iss: "https://example.cloudflareaccess.com",
    aud: audience,
    sub: "test-principal",
    exp: Math.floor(Date.now() / 1_000) + 60,
    ...overrides,
  })));
  const input = `${header}.${claims}`;
  const signature = await crypto.subtle.sign("RSASSA-PKCS1-v1_5", signingKey, new TextEncoder().encode(input));
  return `${input}.${encodeBase64Url(signature)}`;
}

function createRequest({ system = "niknolig", input = "Hallo", token, method = "POST", body, contentType = "application/json" } = {}) {
  const headers = new Headers({ "content-type": contentType });
  if (token) {
    headers.set("authorization", ["Bearer", token].join(" "));
  }
  return new Request("https://gateway.example/v1/assist", {
    method,
    headers,
    ...(method === "POST" ? { body: body ?? JSON.stringify({ system, input }) } : {}),
  });
}

before(async () => {
  const pair = await crypto.subtle.generateKey(
    { name: "RSASSA-PKCS1-v1_5", modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]), hash: "SHA-256" },
    true,
    ["sign", "verify"],
  );
  signingKey = pair.privateKey;
  publicJwk = await crypto.subtle.exportKey("jwk", pair.publicKey);
  publicJwk.kid = "test-key";
  globalThis.fetch = async (url, options = {}) => {
    if (String(url).endsWith("/cdn-cgi/access/certs")) {
      return Response.json({ keys: [publicJwk] });
    }
    openAIRequest = { url: String(url), ...options };
    return Response.json(openAIResponse);
  };
});

after(() => {
  globalThis.fetch = originalFetch;
});

test("authenticates an Access token and calls OpenAI with bounded, isolated input", async () => {
  const token = await accessToken(audienceBySystem.niknolig);
  const response = await worker.fetch(createRequest({ token }), env);
  const result = await response.json();
  const sent = JSON.parse(openAIRequest.body);

  assert.equal(response.status, 200);
  assert.equal(result.output, "Testantwort");
  assert.equal(result.system, "niknolig");
  assert.equal(sent.model, "gpt-4o-mini");
  assert.equal(sent.store, false);
  assert.equal(sent.max_output_tokens, 300);
  assert.match(sent.input[0].content, /NIKNOLIG assistant/);
  assert.equal(sent.input[1].content, "Hallo");
  assert.ok(new Headers(openAIRequest.headers).get("authorization").endsWith([" ", "test"].join("")));
});

test("rejects using one system's Access audience for another system", async () => {
  const token = await accessToken(audienceBySystem.niknolig);
  const response = await worker.fetch(createRequest({ system: "elektro-engel", token }), env);
  assert.equal(response.status, 401);
});

test("rejects unauthenticated requests before contacting OpenAI", async () => {
  const response = await worker.fetch(createRequest(), env);
  assert.equal(response.status, 401);
});

test("rejects oversized or cross-system payload fields", async () => {
  const token = await accessToken(audienceBySystem.niknolig);
  const oversized = await worker.fetch(createRequest({ token, input: "x".repeat(4_001) }), env);
  const crossSystem = await worker.fetch(createRequest({
    token,
    body: JSON.stringify({ system: "niknolig", input: "Hallo", shareWith: ["elektro-engel"] }),
  }), env);
  assert.equal(oversized.status, 400);
  assert.equal(crossSystem.status, 400);
});

test("applies the per-system principal rate limit", async () => {
  const token = await accessToken(audienceBySystem.niknolig);
  let limiterKey;
  const limitedEnv = { ...env, AI_LIMITER: { limit: async ({ key }) => { limiterKey = key; return { success: false }; } } };
  const response = await worker.fetch(createRequest({ token }), limitedEnv);
  assert.equal(response.status, 429);
  assert.equal(limiterKey, "niknolig:test-principal");
});

test("returns a safe offline fallback if the API secret is unavailable", async () => {
  const response = await worker.fetch(createRequest(), { ...env, OPENAI_API_KEY: undefined });
  const result = await response.json();
  assert.equal(response.status, 503);
  assert.equal(result.fallback, true);
  assert.equal(JSON.stringify(result).includes("test"), false);
});

test("returns a safe fallback for upstream errors", async () => {
  const token = await accessToken(audienceBySystem.niknolig);
  globalThis.fetch = async (url) => String(url).endsWith("/cdn-cgi/access/certs")
    ? Response.json({ keys: [publicJwk] })
    : new Response("sensitive upstream error", { status: 429 });
  const response = await worker.fetch(createRequest({ token }), env);
  const result = await response.json();
  assert.equal(response.status, 503);
  assert.equal(result.fallback, true);
  assert.equal(JSON.stringify(result).includes("sensitive upstream error"), false);
});
