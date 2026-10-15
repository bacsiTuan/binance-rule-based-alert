import assert from "node:assert/strict";
import test from "node:test";
import { createRulesApi } from "../src/api/rulesClient.js";
import { errorMessage } from "../src/i18n.js";

test("rule trigger sends a confirmed request ID without browser credentials", async (t) => {
  const calls = [];
  t.mock.method(globalThis, "fetch", async (...args) => {
    calls.push(args);
    return Response.json({ status: "complete", stats: { accepted: 1 }, replayed: false });
  });
  const result = await createRulesApi().triggerAll("same-id-on-repeat");
  assert.equal(result.stats.accepted, 1);
  assert.equal(calls[0][0], "/api/telegram/trigger");
  assert.deepEqual(JSON.parse(calls[0][1].body), { request_id: "same-id-on-repeat", confirmed: true });
  assert.deepEqual(calls[0][1].headers, { "Content-Type": "application/json" });
});

test("disabled watcher points to the separate AI test instead of an untranslated server error", async (t) => {
  t.mock.method(globalThis, "fetch", async () => Response.json(
    { detail: "Telegram notifications are not enabled" }, { status: 503 }));
  await assert.rejects(createRulesApi().triggerAll("id"), error => {
    assert.match(errorMessage(error, "en"), /Connection check/);
    assert.match(errorMessage(error, "vi"), /Kiểm tra kết nối/);
    return true;
  });
});
