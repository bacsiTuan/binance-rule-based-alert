import assert from "node:assert/strict";
import test from "node:test";
import { createTelegramTestMiddleware } from "../server/telegramTestProxy.js";

const key = "server-only-secret-key-for-tests";
function exercise({ enabled = true, secret = key, ...changes } = {}) {
  const req = { url: "/api/ai/telegram-test", method: "POST",
    socket: { remoteAddress: "127.0.0.1" },
    headers: { host: "127.0.0.1:5173", origin: "http://127.0.0.1:5173", "content-type": "application/json" },
    ...changes };
  let forwarded = false;
  const res = { setHeader() {}, end(body) { this.body = body; } };
  createTelegramTestMiddleware({ enabled, key: secret })(req, res, () => { forwarded = true; });
  assert.ok(!res.body?.includes(key));
  return { req, res, forwarded };
}

test("server injects environment key only for a local same-origin JSON test request", () => {
  const result = exercise();
  assert.equal(result.req.headers["x-telegram-test-key"], key);
  assert.equal(result.forwarded, true);
  const batch = exercise({ url: "/api/telegram/trigger" });
  assert.equal(batch.req.headers["x-telegram-test-key"], key);
  assert.equal(batch.forwarded, true);
  const ordinary = exercise({ url: "/api/ai/chat" });
  assert.equal(ordinary.forwarded, true);
  assert.equal(ordinary.req.headers["x-telegram-test-key"], undefined);
});

test("cross-origin, remote, missing-origin and form requests cannot use automatic credentials", () => {
  for (const changes of [
    { socket: { remoteAddress: "192.168.1.20" } },
    { headers: { host: "127.0.0.1:5173", origin: "https://evil.example", "content-type": "application/json" } },
    { headers: { host: "evil.example", origin: "http://evil.example", "content-type": "application/json" } },
    { headers: { host: "127.0.0.1:5173", origin: "http://127.0.0.1:5174", "content-type": "application/json" } },
    { headers: { host: "127.0.0.1:5173", "content-type": "application/json" } },
    { headers: { host: "127.0.0.1:5173", origin: "http://127.0.0.1:5173", "content-type": "text/plain" } },
    { method: "GET" },
  ]) {
    for (const url of ["/api/ai/telegram-test", "/api/telegram/trigger"]) {
      const result = exercise({ ...changes, url });
      assert.equal(result.res.statusCode, 403);
      assert.equal(result.forwarded, false);
      assert.equal(result.req.headers["x-telegram-test-key"], undefined);
    }
  }
});

test("missing configuration fails closed instead of forwarding an unauthenticated test", () => {
  for (const config of [{ enabled: false }, { secret: "" }, { secret: "short" }]) {
    const result = exercise(config);
    assert.equal(result.res.statusCode, 503);
    assert.equal(result.forwarded, false);
  }
});
