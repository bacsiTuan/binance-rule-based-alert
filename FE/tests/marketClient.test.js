import assert from "node:assert/strict";
import test from "node:test";
import { createMarketApi } from "../src/api/marketClient.js";
import { buildIndicatorRequest, displayValue } from "../src/indicatorUtils.js";

test("symbols envelope and metadata are preserved", async () => {
  const result = { symbols: ["BTCUSDT"], source: "stale", stale: true, warning: "timeout" };
  const api = createMarketApi({ fetcher: async (url) => {
    assert.equal(url, "/api/symbols");
    return Response.json(result);
  } });
  assert.deepEqual(await api.getSymbols(), result);
});

test("form schema maps to actual POST contract for both sides and open candles", async () => {
  const payload = buildIndicatorRequest({
    symbol: "ETHUSDT", timeframe: "1w", candle_mode: "include_current",
    indicator: { type: "ema", length: 12 }, target: { type: "ema", length: 26 },
  });
  assert.deepEqual(payload, {
    symbol: "ETHUSDT", interval: "1w", limit: 300, include_open: true,
    indicators: [{ name: "ema", period: 12 }, { name: "ema", period: 26 }],
  });
  const controller = new AbortController();
  const api = createMarketApi({ fetcher: async (url, options) => {
    assert.equal(url, "/api/indicators");
    assert.equal(options.method, "POST");
    assert.equal(options.headers["Content-Type"], "application/json");
    assert.equal(options.signal, controller.signal);
    assert.deepEqual(JSON.parse(options.body), payload);
    return Response.json({ results: [{ latest: { value: null, status: "insufficient_data" } }] });
  } });
  const response = await api.getIndicators(payload, { signal: controller.signal });
  assert.equal(response.results[0].latest.value, null);
});

test("close is excluded, equal selections are deduplicated, default selections remain valid", () => {
  const rule = { symbol: "BTCUSDT", timeframe: "1h", candle_mode: "closed" };
  assert.deepEqual(buildIndicatorRequest({ ...rule,
    indicator: { type: "close" }, target: { type: "sma", length: 200 },
  }).indicators, [{ name: "sma", period: 200 }]);
  assert.equal(buildIndicatorRequest({ ...rule,
    indicator: { type: "sma", length: 50 }, target: { type: "sma", length: 50 },
  }).indicators.length, 1);
  const fallback = buildIndicatorRequest({ ...rule, indicator: { type: "close" }, target: 100 });
  assert.equal(fallback.indicators.length, 3);
  assert.equal(fallback.include_open, false);
});

test("FastAPI string, validation list, object errors and cooldown produce readable messages", async () => {
  for (const [body, status, message] of [
    [{ detail: "Redis unavailable" }, 503, "Redis unavailable"],
    [{ detail: [{ msg: "Invalid interval" }] }, 422, "Invalid interval"],
    [{ detail: { code: "invalid_indicator_data", message: "Bad candle order" } }, 502, "Bad candle order"],
    [{ detail: "Rate limited", retry_after: 60 }, 429, "Rate limited Try again in 60 seconds."],
  ]) {
    const api = createMarketApi({ fetcher: async () => Response.json(body, { status }) });
    await assert.rejects(api.getSymbols(), { message });
  }
});

test("offline, invalid JSON and cancellation do not become misleading indicator results", async () => {
  const offline = createMarketApi({ fetcher: async () => { throw new TypeError("fetch failed"); } });
  await assert.rejects(offline.getSymbols(), /Unable to connect to the backend/);
  const html = createMarketApi({ fetcher: async () => new Response("<html>proxy failed</html>", { status: 502 }) });
  await assert.rejects(html.getSymbols(), /HTTP 502/);
  const abort = new DOMException("Aborted", "AbortError");
  const cancelled = createMarketApi({ fetcher: async () => { throw abort; } });
  await assert.rejects(cancelled.getIndicators({}), (error) => error === abort);
});

test("display retains exact integer digits and handles missing and very small values", () => {
  assert.equal(displayValue("12345678901234567890.123456789"), "12345678901234567890.123456");
  assert.equal(displayValue("50.000000"), "50");
  assert.equal(displayValue(null), "—");
});
