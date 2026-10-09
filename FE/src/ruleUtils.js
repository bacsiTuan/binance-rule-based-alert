import { MAX_LENGTH, OPERATORS } from "./constants.js";

export const initialForm = {
  symbol: "BTCUSDT",
  timeframe: "1d",
  left: { type: "rsi", length: 14 },
  operator: "cross_above",
  target: { mode: "value", value: 30, type: "sma", length: 200 },
  candleMode: "closed",
};

const isInt = (v) => Number.isInteger(Number(v)) && String(v).trim() !== "";

function validateLength(length, label, errors, key) {
  if (!isInt(length) || Number(length) < 1 || Number(length) > MAX_LENGTH) {
    errors[key] = `${label}: length phải là số nguyên từ 1 đến ${MAX_LENGTH}.`;
  }
}

// Trả về object lỗi theo từng trường; rỗng nghĩa là hợp lệ.
export function validateForm(form) {
  const errors = {};
  if (!form.symbol) errors.symbol = "Hãy chọn symbol.";

  if (form.left.type !== "close") {
    validateLength(form.left.length, "Chỉ báo", errors, "leftLength");
  }

  if (form.target.mode === "value") {
    const raw = form.target.value;
    if (raw === "" || raw === null || Number.isNaN(Number(raw))) {
      errors.targetValue = "Hãy nhập một con số.";
    } else if (form.left.type === "rsi" && (Number(raw) < 0 || Number(raw) > 100)) {
      errors.targetValue = "RSI luôn nằm trong khoảng 0–100.";
    }
  } else {
    validateLength(form.target.length, "Chỉ báo đích", errors, "targetLength");
    if (
      !errors.targetLength &&
      !errors.leftLength &&
      form.left.type === form.target.type &&
      Number(form.left.length) === Number(form.target.length)
    ) {
      errors.targetLength = "Hai vế giống hệt nhau nên luật không bao giờ kích hoạt.";
    }
  }
  return errors;
}

// Chuyển state của form thành JSON gửi backend (khớp mục 5.3 của plan).
export function buildPayload(form) {
  const indicator =
    form.left.type === "close"
      ? { type: "close" }
      : { type: form.left.type, length: Number(form.left.length) };

  const target =
    form.target.mode === "value"
      ? Number(form.target.value)
      : { type: form.target.type, length: Number(form.target.length) };

  return {
    symbol: form.symbol,
    timeframe: form.timeframe,
    indicator,
    operator: form.operator,
    target,
    candle_mode: form.candleMode,
  };
}

const indicatorText = (i) =>
  i.type === "close" ? "Giá" : `${i.type.toUpperCase()}(${i.length})`;

// Mô tả luật bằng chữ dễ đọc, ví dụ "BTCUSDT · 1D · RSI(14) cắt lên 30".
export function describeRule(rule) {
  const op = OPERATORS.find((o) => o.value === rule.operator);
  const opText = op ? op.label.split(" (")[0].toLowerCase() : rule.operator;
  const target = typeof rule.target === "number" ? rule.target : indicatorText(rule.target);
  return `${rule.symbol} · ${rule.timeframe.toUpperCase()} · ${indicatorText(rule.indicator)} ${opText} ${target}`;
}
