import { MAX_LENGTH, OPERATORS } from "./constants.js";
import { translate } from "./i18n.js";

export const initialForm = {
  symbol: "BTCUSDT",
  timeframe: "1d",
  left: { type: "rsi", length: 14 },
  operator: "cross_above",
  target: { mode: "value", value: 30, type: "sma", length: 200 },
  candleMode: "closed",
  triggerType: "once_per_bar_close",
  message: "",
};

const isInt = (v) => Number.isInteger(Number(v)) && String(v).trim() !== "";

function validateLength(length, label, errors, key, language) {
  if (!isInt(length) || Number(length) < 1 || Number(length) > MAX_LENGTH) {
    errors[key] = translate("{label}: chu kỳ phải là số nguyên từ 1 đến {max}.", language,
      { label: translate(label, language), max: MAX_LENGTH });
  }
}

// Trả về object lỗi theo từng trường; rỗng nghĩa là hợp lệ.
export function validateForm(form, language = "en") {
  const errors = {};
  if (!form.symbol) errors.symbol = translate("Hãy chọn symbol.", language);

  if (form.left.type !== "close") {
    validateLength(form.left.length, "Chỉ báo", errors, "leftLength", language);
  }

  if (form.target.mode === "value") {
    const raw = form.target.value;
    if (raw === "" || raw === null || !Number.isFinite(Number(raw))) {
      errors.targetValue = translate("Hãy nhập một con số.", language);
    } else if (form.left.type === "rsi" && (Number(raw) < 0 || Number(raw) > 100)) {
      errors.targetValue = translate("RSI luôn nằm trong khoảng 0–100.", language);
    }
  } else {
    validateLength(form.target.length, "Chỉ báo đích", errors, "targetLength", language);
    if (
      !errors.targetLength &&
      !errors.leftLength &&
      form.left.type === form.target.type &&
      Number(form.left.length) === Number(form.target.length)
    ) {
      errors.targetLength = translate("Hai vế giống hệt nhau nên luật không bao giờ kích hoạt.", language);
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

  const payload = {
    symbol: form.symbol,
    timeframe: form.timeframe,
    indicator,
    operator: form.operator,
    target,
    candle_mode: form.candleMode,
    trigger_type: form.triggerType || "once_per_bar_close",
  };
  if (form.message && form.message.trim()) {
    payload.message = form.message.trim();
  }
  return payload;
}

const indicatorText = (i, language) => {
  if (!i) return "";
  if (i.type === "close") return translate("Giá", language);
  if (i.type === "mass_index") return `Mass Index(${i.length || 10})`;
  return `${i.type.toUpperCase()}(${i.length})`;
};

// Mô tả luật bằng chữ dễ đọc, ví dụ "BTCUSDT · 1D · RSI(14) cắt lên 30".
export function describeRule(rule, language = "en") {
  const op = OPERATORS.find((o) => o.value === rule.operator);
  const opText = op ? translate(op.label.split(" (")[0], language).toLowerCase() : rule.operator;
  const target = typeof rule.target === "number" ? rule.target : indicatorText(rule.target, language);
  return `${rule.symbol} · ${rule.timeframe.toUpperCase()} · ${indicatorText(rule.indicator, language)} ${opText} ${target}`;
}
