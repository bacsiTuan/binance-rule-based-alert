import assert from "node:assert/strict";
import test from "node:test";
import { english, LANGUAGE_KEY, readLanguage, translate, errorMessage, LocalizedError, BackendError } from "../src/i18n.js";
import { CANDLE_MODES, LEFT_INDICATORS, OPERATORS, TEMPLATES, TIMEFRAMES } from "../src/constants.js";
import { buildPayload, describeRule, initialForm, validateForm } from "../src/ruleUtils.js";

test("English is the default; saved Vietnamese is respected and unavailable storage falls back safely", () => {
  assert.equal(readLanguage({ getItem: () => null }), "en");
  assert.equal(readLanguage({ getItem: () => "fr" }), "en");
  assert.equal(readLanguage({ getItem: (key) => { assert.equal(key, LANGUAGE_KEY); return "vi"; } }), "vi");
  assert.equal(readLanguage({ getItem: () => { throw new Error("Storage blocked"); } }), "en");
  assert.equal(translate("Luật đã lưu"), "Saved rules");
  assert.equal(translate("Luật đã lưu", "vi"), "Luật đã lưu");
});

test("Every form option and template has an English translation with matching interpolation parameters", () => {
  for (const item of [...CANDLE_MODES, ...LEFT_INDICATORS, ...OPERATORS, ...TEMPLATES, ...TIMEFRAMES]) {
    for (const text of [item.label, item.name, item.hint].filter(Boolean)) {
      assert.ok(english[text], `Missing English translation: ${text}`);
    }
  }
  for (const [vi, en] of Object.entries(english)) {
    assert.deepEqual((vi.match(/\{\w+\}/g) || []).sort(), (en.match(/\{\w+\}/g) || []).sort(), vi);
  }
  assert.equal(translate("{count} cặp phù hợp", "en", { count: 3 }), "3 matching pairs");
});

test("Rule previews and validation change language without changing stored rule data or the request payload", () => {
  const form = structuredClone(initialForm);
  const payload = buildPayload(form);
  assert.equal(describeRule(payload), "BTCUSDT · 1D · RSI(14) crosses above 30");
  assert.equal(describeRule(payload, "vi"), "BTCUSDT · 1D · RSI(14) cắt lên 30");
  form.left.length = 0;
  assert.match(validateForm(form).leftLength, /period must be an integer/);
  assert.match(validateForm(form, "vi").leftLength, /chu kỳ phải là số nguyên/);
  assert.deepEqual(payload, buildPayload(initialForm));
});

test("An existing error can be rendered in either language without making a new request", () => {
  const invalid = new LocalizedError("Backend trả dữ liệu không hợp lệ (HTTP {status}).", { status: 502 });
  assert.equal(errorMessage(invalid, "en"), "The backend returned invalid data (HTTP 502).");
  assert.equal(errorMessage(invalid, "vi"), "Backend trả dữ liệu không hợp lệ (HTTP 502).");
  const limited = new BackendError("Rate limited", 60);
  assert.equal(errorMessage(limited, "en"), "Rate limited Try again in 60 seconds.");
  assert.equal(errorMessage(limited, "vi"), "Rate limited Thử lại sau 60 giây.");
});
