import { useLanguage } from "../LanguageContext.jsx";
import { cloneElement, useEffect, useMemo, useState } from "react";
import {
  CANDLE_MODES, LEFT_INDICATORS, OPERATORS, TEMPLATES, TIMEFRAMES, TRIGGER_TYPES, MAX_LENGTH,
} from "../constants.js";
import { buildPayload, describeRule, initialForm, validateForm } from "../ruleUtils.js";
import { buildIndicatorRequest } from "../indicatorUtils.js";
import Icon from "./Icon.jsx";

function Field({ id, label, error, hint, children }) {
  const messageId = `${id}-help`;
  const control = typeof children.type === "string" && ["input", "select"].includes(children.type)
    ? cloneElement(children, { "aria-invalid": !!error, "aria-describedby": error || hint ? messageId : undefined })
    : children;
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {control}
      {error ? <p id={messageId} className="field-error" role="alert">{error}</p> : hint ? <p id={messageId} className="field-hint">{hint}</p> : null}
    </div>
  );
}

export default function RuleForm({
  symbols,
  onSubmit,
  activeSymbol,
  onSymbolChange,
  activeTimeframe,
  onTimeframeChange,
  onIndicatorRequestChange,
  initialRule = null,
}) {
  const { t, language, localizedError } = useLanguage();
  const isEdit = !!initialRule;

  const toFormState = (rule) => {
    if (!rule) return structuredClone(initialForm);
    return {
      symbol: rule.symbol || "BTCUSDT",
      timeframe: rule.timeframe || "1d",
      left: {
        type: rule.indicator?.type || "rsi",
        length: rule.indicator?.length ?? 14,
      },
      operator: rule.operator || "lt",
      target: {
        mode: "value",
        value: typeof rule.target === "number" ? rule.target : (rule.target?.value ?? 30),
      },
      candleMode: rule.candle_mode || "closed",
      triggerType: rule.trigger_type || "once_per_bar_close",
      message: rule.message || "",
    };
  };

  const [form, setForm] = useState(() => toFormState(initialRule));
  const [touched, setTouched] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [serverError, setServerError] = useState("");
  const [symbolSearch, setSymbolSearch] = useState("");
  const [saved, setSaved] = useState(false);
  const filteredSymbols = symbols.filter((symbol) => symbol.includes(symbolSearch.trim().toUpperCase()));
  const visibleSymbols = filteredSymbols.includes(form.symbol) ? filteredSymbols
    : symbols.includes(form.symbol) ? [form.symbol, ...filteredSymbols] : filteredSymbols;

  useEffect(() => {
    setForm(toFormState(initialRule));
    setTouched(false);
    setServerError("");
    setSaved(false);
  }, [initialRule]);

  // Đồng bộ symbol khi chọn từ ngoài (chỉ khi tạo mới)
  useEffect(() => {
    if (!isEdit && activeSymbol && activeSymbol !== form.symbol) {
      setForm((f) => ({ ...f, symbol: activeSymbol }));
    }
  }, [activeSymbol, isEdit]);

  // Đồng bộ timeframe khi chọn từ ngoài (chỉ khi tạo mới)
  useEffect(() => {
    if (!isEdit && activeTimeframe && activeTimeframe !== form.timeframe) {
      setForm((f) => ({ ...f, timeframe: activeTimeframe }));
    }
  }, [activeTimeframe, isEdit]);

  // Khi danh sách symbol tải xong mà symbol hiện tại không có trong đó, chọn symbol đầu tiên.
  useEffect(() => {
    if (symbols.length && !symbols.includes(form.symbol)) {
      const defaultSymbol = symbols[0];
      setForm((f) => ({ ...f, symbol: defaultSymbol }));
      if (onSymbolChange) onSymbolChange(defaultSymbol);
    }
  }, [symbols]); // eslint-disable-line react-hooks/exhaustive-deps

  const errors = useMemo(() => validateForm(form, language), [form, language]);
  const hasErrors = Object.keys(errors).length > 0;
  const shown = touched ? errors : {};

  const setLeft = (patch) => setForm((f) => ({ ...f, left: { ...f.left, ...patch } }));
  const setTarget = (patch) => setForm((f) => ({ ...f, target: { ...f.target, ...patch } }));

  const onLeftTypeChange = (type) => {
    const def = LEFT_INDICATORS.find((i) => i.value === type);
    setLeft({ type, length: def?.hasLength ? def.defaultLength : "" });
  };

  const applyTemplate = (id) => {
    const template = TEMPLATES.find((x) => x.id === id);
    if (!template) return;
    setForm((f) => ({
      ...f,
      left: { ...template.left },
      operator: template.operator,
      target: { ...f.target, ...template.target },
      candleMode: template.candleMode || "closed",
      triggerType: template.triggerType || "once_per_bar_close",
      message: "",
    }));
    setTouched(false);
    setServerError("");
    setSaved(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setTouched(true);
    setServerError("");
    if (hasErrors) {
      const fields = { symbol: "symbol", leftLength: "left-length", targetValue: "target-value", targetLength: "target-length" };
      e.currentTarget.querySelector(`#${fields[Object.keys(errors)[0]]}`)?.focus();
      return;
    }
    setSubmitting(true);
    try {
      await onSubmit(buildPayload(form));
      setSaved(true);
    } catch (err) {
      setServerError(err);
    } finally {
      setSubmitting(false);
    }
  };

  const leftDef = LEFT_INDICATORS.find((i) => i.value === form.left.type);
  const opDef = OPERATORS.find((o) => o.value === form.operator);
  const modeDef = CANDLE_MODES.find((m) => m.value === form.candleMode);
  const payload = buildPayload(form);
  const indicatorRequestKey = JSON.stringify(hasErrors ? null : buildIndicatorRequest(payload));

  useEffect(() => {
    onIndicatorRequestChange?.(JSON.parse(indicatorRequestKey));
  }, [indicatorRequestKey, onIndicatorRequestChange]);

  useEffect(() => {
    setSaved(false);
  }, [form]);

  return (
    <form id="rule-form" className="card rule-form" onSubmit={handleSubmit} noValidate aria-labelledby="form-title">
      <div className="section-heading"><span className="section-icon"><Icon name={isEdit ? "edit" : "plus"} size={19} /></span>
        <div><h2 id="form-title" className="card-title">{isEdit ? t("Cập nhật cảnh báo #{id}", { id: initialRule.id }) : t("Tạo cảnh báo mới")}</h2><p className="section-description">{isEdit ? t("Chỉnh sửa các thông số điều kiện của cảnh báo.") : t("Thiết lập điều kiện cảnh báo bạn muốn theo dõi.")}</p></div></div>

      <Field id="template" label={t("Mẫu cảnh báo có sẵn")}>
        <select id="template" defaultValue="" onChange={(e) => applyTemplate(e.target.value)}>
          <option value="">{t("— Chọn mẫu cảnh báo —")}</option>
          {TEMPLATES.map((item) => <option key={item.id} value={item.id}>{t(item.name)}</option>)}
        </select>
      </Field>

      <div className="form-step"><span>01</span> {t("Chọn thị trường")}</div>
      <Field id="symbol-search" label={t("Tìm cặp giao dịch")}>
        <div className="search-field"><Icon name="search" size={17} /><input id="symbol-search" type="search"
          placeholder={t("Tìm BTC, ETH, SOL…")} value={symbolSearch}
          onKeyDown={(event) => { if (event.key === "Enter") event.preventDefault(); }}
          onChange={(event) => setSymbolSearch(event.target.value)} /></div>
        {symbolSearch && <p className="field-hint" role="status">{filteredSymbols.length ? t("{count} cặp phù hợp", { count: filteredSymbols.length }) : t("Không tìm thấy cặp phù hợp. Cặp đang chọn được giữ lại.")}</p>}
      </Field>

      <div className="row">
        <Field id="symbol" label={t("Cặp giao dịch")} error={shown.symbol}>
          <select
            id="symbol"
            value={form.symbol}
            onChange={(e) => {
              const val = e.target.value;
              setForm({ ...form, symbol: val });
              if (onSymbolChange) onSymbolChange(val);
            }}
          >
            {symbols.length === 0 && <option value="">{t("Đang tải…")}</option>}
            {visibleSymbols.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </Field>
        <Field id="timeframe" label={t("Khung thời gian")}>
          <select
            id="timeframe"
            value={form.timeframe}
            onChange={(e) => {
              const val = e.target.value;
              setForm({ ...form, timeframe: val });
              if (onTimeframeChange) onTimeframeChange(val);
            }}
          >
            {TIMEFRAMES.map((item) => <option key={item.value} value={item.value}>{t(item.label)}</option>)}
          </select>
        </Field>
      </div>

      <fieldset className="group">
        <legend><span className="step-number">02</span> {t("Thiết lập điều kiện")}</legend>

        <div className="row">
          <Field id="left-type" label={t("Chỉ báo cần theo dõi")}>
            <select id="left-type" value={form.left.type} onChange={(e) => onLeftTypeChange(e.target.value)}>
              {LEFT_INDICATORS.map((i) => <option key={i.value} value={i.value}>{t(i.label)}</option>)}
            </select>
          </Field>
          {leftDef?.hasLength && (
            <Field id="left-length" label={t("Chu kỳ (số nến)")} error={shown.leftLength}>
              <input
                id="left-length" type="number" min="1" max={MAX_LENGTH} inputMode="numeric"
                value={form.left.length} onChange={(e) => setLeft({ length: e.target.value })}
              />
            </Field>
          )}
        </div>

        <Field id="operator" label={t("Điều kiện so sánh")} hint={t(opDef?.hint)}>
          <select id="operator" value={form.operator} onChange={(e) => setForm({ ...form, operator: e.target.value })}>
            {OPERATORS.map((o) => (
              <option key={o.value} value={o.value} disabled={o.disabled}>
                {t(o.label)}{o.disabled ? ` — (${t("Vô hiệu hóa")})` : ""}
              </option>
            ))}
          </select>
        </Field>

        <div className="field">
          <span className="label" id="target-label">{t("So sánh với")}</span>
          <div className="segmented" role="group" aria-labelledby="target-label">
            <button
              type="button"
              className="seg active"
              aria-pressed="true"
            >
              {t("Giá trị")}
            </button>
            <button
              type="button"
              className="seg disabled"
              disabled
              aria-disabled="true"
              style={{ opacity: 0.45, cursor: "not-allowed" }}
              title={t("Chỉ áp dụng so sánh với giá trị số")}
            >
              {t("Chỉ báo")}
            </button>
          </div>
        </div>

        <Field id="target-value" label={t("Giá trị")} error={shown.targetValue}
          hint={form.left.type === "rsi" ? t("RSI nằm trong khoảng 0–100.") : undefined}>
          <input
            id="target-value" type="number" step="any" inputMode="decimal"
            value={form.target.value} onChange={(e) => setTarget({ mode: "value", value: e.target.value })}
          />
        </Field>
      </fieldset>

      <div className="form-step"><span>03</span> {t("Chọn dữ liệu nến")}</div>

      <Field id="candle-mode" label={t("Chế độ nến")} hint={t(modeDef?.hint)}>
        <select id="candle-mode" value={form.candleMode} onChange={(e) => setForm({ ...form, candleMode: e.target.value })}>
          {CANDLE_MODES.map((m) => (
            <option key={m.value} value={m.value} disabled={m.disabled}>
              {t(m.label)}{m.disabled ? ` — (${t("Vô hiệu hóa")})` : ""}
            </option>
          ))}
        </select>
      </Field>

      <div className="form-step"><span>04</span> {t("Tùy chọn cảnh báo TradingView")}</div>

      <Field id="trigger-type" label={t("Cơ chế kích hoạt")}>
        <select id="trigger-type" value={form.triggerType || "once_per_bar_close"} onChange={(e) => setForm({ ...form, triggerType: e.target.value })}>
          {TRIGGER_TYPES.map((tr) => <option key={tr.value} value={tr.value}>{t(tr.label)}</option>)}
        </select>
      </Field>

      <div className="preview" aria-live="polite">
        <span className="preview-label">{t("Xem trước")}</span>
        <p className="preview-text">
          {hasErrors ? t("Hoàn tất các trường để xem mô tả cảnh báo.") : describeRule(payload, language)}
        </p>
      </div>

      {serverError && <p className="banner error" role="alert">{localizedError(serverError) || t("Không thể tạo cảnh báo.")}</p>}
      {saved && <p className="banner success" role="status"><Icon name="check" size={17} /> {isEdit ? t("Đã cập nhật cảnh báo.") : t("Đã tạo cảnh báo. Bạn có thể xem trong danh sách bên cạnh.")}</p>}

      <button id="submit-rule" className="btn primary" type="submit" disabled={submitting || !symbols.length}>
        <Icon name={isEdit ? "check" : "plus"} size={18} />{submitting ? (isEdit ? t("Đang cập nhật…") : t("Đang tạo…")) : (isEdit ? t("Cập nhật cảnh báo") : t("Tạo cảnh báo"))}
      </button>
      <p className="local-note">{t("Cảnh báo được lưu và quản lý trên cơ sở dữ liệu Redis")}</p>
    </form>
  );
}
