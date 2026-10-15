import assert from "node:assert/strict";
import test from "node:test";
import { createAssistantApi } from "../src/api/assistantClient.js";
import { errorMessage } from "../src/i18n.js";

test("chat sends the selected context and bounded history to the backend", async () => {
  const calls = [];
  const api = createAssistantApi({ fetcher: async (...args) => {
    calls.push(args); return Response.json({ answer: "Conditional analysis" });
  } });
  const payload = { message: "Analyze", symbol: "ETHUSDT", interval: "1h", language: "vi",
    history: [{ role: "user", content: "Explain RSI" }] };
  assert.equal((await api.chat(payload)).answer, "Conditional analysis");
  assert.equal(calls[0][0], "/api/ai/chat");
  assert.deepEqual(JSON.parse(calls[0][1].body), payload);
});

test("provider errors are localized without exposing internal messages", async () => {
  const api = createAssistantApi({ fetcher: async () => Response.json({ detail: "ai_failed" }, { status: 502 }) });
  await assert.rejects(api.chat({ message: "hi" }), error => {
    assert.match(errorMessage(error, "en"), /could not respond/);
    assert.match(errorMessage(error, "vi"), /Chưa nhận được/);
    return true;
  });
});

test("network errors are readable and cancellation stays cancellation", async () => {
  const offline = createAssistantApi({ fetcher: async () => { throw new TypeError("offline"); } });
  await assert.rejects(offline.status(), error => /Unable to connect/.test(error.message));
  const cancelled = new DOMException("cancel", "AbortError");
  const api = createAssistantApi({ fetcher: async () => { throw cancelled; } });
  await assert.rejects(api.chat({}), error => error === cancelled);
});

test("manual Telegram test sends confirmation without putting the environment key in the browser request", async () => {
  const calls = [];
  const api = createAssistantApi({ fetcher: async (...args) => {
    calls.push(args); return Response.json({ status: "accepted", replayed: false });
  } });
  const payload = { request_id: "a-test-id", confirmed: true, symbol: "BTCUSDT", interval: "1h", language: "en" };
  assert.equal((await api.telegramTest(payload)).status, "accepted");
  assert.equal(calls[0][0], "/api/ai/telegram-test");
  assert.deepEqual(calls[0][1].headers, { "Content-Type": "application/json" });
  assert.deepEqual(JSON.parse(calls[0][1].body), payload);
  assert.ok(!calls[0][1].body.includes("mock-key"));
});

test("manual test authorization and rate-limit errors remain actionable in both languages", async () => {
  for (const code of ["telegram_test_unauthorized", "telegram_test_rate_limited"]) {
    const api = createAssistantApi({ fetcher: async () => Response.json({ detail: code }, { status: 403 }) });
    await assert.rejects(api.telegramTest({}), error => {
      assert.equal(error.code, code);
      assert.notEqual(errorMessage(error, "en"), errorMessage(error, "vi"));
      return true;
    });
  }
});
