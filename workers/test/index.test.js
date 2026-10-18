import test from "node:test";
import assert from "node:assert/strict";
import worker from "../src/index.js";

async function captureLogs(run) {
  const entries = [];
  const original = console.log;
  console.log = (entry) => entries.push(JSON.parse(entry));
  try {
    const response = await run();
    return { response, entries };
  } finally {
    console.log = original;
  }
}

function environment(app, assets) {
  return { APP_AREA: app, ASSETS: assets };
}

test("serves assets only in the configured app area and adds security headers", async () => {
  const requested = [];
  const assets = {
    async fetch(request) {
      requested.push(request);
      return new Response("public page", {
        headers: { "Content-Type": "text/html; charset=utf-8" },
      });
    },
  };

  for (const app of ["niknolig", "niknolig-defense"]) {
    const { response, entries } = await captureLogs(() =>
      worker.fetch(new Request("https://example.test/index.html"), environment(app, assets)),
    );

    assert.equal(await response.text(), "public page");
    assert.equal(response.headers.get("X-Content-Type-Options"), "nosniff");
    assert.equal(response.headers.get("X-Frame-Options"), "DENY");
    assert.match(response.headers.get("Content-Security-Policy"), /frame-ancestors 'none'/);
    assert.deepEqual(entries[0].app, app);
    assert.equal(entries[0].status, 200);
  }

  assert.equal(requested.length, 2);
});

test("HEAD responses do not include an asset body", async () => {
  const response = await worker.fetch(
    new Request("https://example.test/index.html", { method: "HEAD" }),
    environment("niknolig", {
      async fetch() {
        return new Response("not included");
      },
    }),
  );

  assert.equal(response.status, 200);
  assert.equal(await response.text(), "");
});

test("rejects methods outside the public read-only asset contract", async () => {
  let called = false;
  const { response } = await captureLogs(() =>
    worker.fetch(
      new Request("https://example.test/index.html", { method: "POST" }),
      environment("niknolig", {
        async fetch() {
          called = true;
          return new Response("unexpected");
        },
      }),
    ),
  );

  assert.equal(response.status, 405);
  assert.equal(response.headers.get("Allow"), "GET, HEAD");
  assert.equal(called, false);
});

test("fails closed for unknown app configuration or missing asset binding", async () => {
  for (const env of [environment("other-app", {}), environment("niknolig", null)]) {
    const { response } = await captureLogs(() =>
      worker.fetch(new Request("https://example.test/private?token=do-not-log"), env),
    );
    assert.equal(response.status, 503);
    assert.equal(response.headers.get("Cache-Control"), "no-store");
  }
});

test("asset failures return a generic response and logs exclude request data", async () => {
  const { response, entries } = await captureLogs(() =>
    worker.fetch(
      new Request("https://example.test/private?token=do-not-log"),
      environment("niknolig-defense", {
        async fetch() {
          throw new Error("sensitive internal detail");
        },
      }),
    ),
  );

  assert.equal(response.status, 503);
  assert.deepEqual(await response.json(), {
    error: "service_unavailable",
    requestId: entries[0].requestId,
  });
  assert.equal(entries[0].event, "asset_error");
  assert.equal(JSON.stringify(entries), JSON.stringify(entries).replace(/do-not-log|sensitive internal detail/, ""));
  assert.equal("url" in entries[0], false);
  assert.equal("headers" in entries[0], false);
});
