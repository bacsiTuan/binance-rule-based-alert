import { cloneElement, useEffect, useMemo, useState } from "react";
import {
  CANDLE_MODES, LEFT_INDICATORS, OPERATORS, TARGET_INDICATORS, TEMPLATES, TIMEFRAMES, MAX_LENGTH,
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
}) {
  const [form, setForm] = useState(initialForm);
  const [touched, setTouched] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [serverError, setServerError] = useState("");
  const [symbolSearch, setSymbolSearch] = useState("");
  const [saved, setSaved] = useState(false);
  const filteredSymbols = symbols.filter((symbol) => symbol.includes(symbolSearch.trim().toUpperCase()));
  const visibleSymbols = filteredSymbols.includes(form.symbol) ? filteredSymbols
    : symbols.includes(form.symbol) ? [form.symbol, ...filteredSymbols] : filteredSymbols;

  // Đồng bộ symbol khi chọn từ ngoài
  useEffect(() => {
    if (activeSymbol && activeSymbol !== form.symbol) {
      setForm((f) => ({ ...f, symbol: activeSymbol }));
    }
  }, [activeSymbol]);

  // Đồng bộ timeframe khi chọn từ ngoài
  useEffect(() => {
    if (activeTimeframe && activeTimeframe !== form.timeframe) {
      setForm((f) => ({ ...f, timeframe: activeTimeframe }));
    }
  }, [activeTimeframe]);

  // Khi danh sách symbol tải xong mà symbol hiện tại không có trong đó, chọn symbol đầu tiên.
  useEffect(() => {
    if (symbols.length && !symbols.includes(form.symbol)) {
      const defaultSymbol = symbols[0];
      setForm((f) => ({ ...f, symbol: defaultSymbol }));
      if (onSymbolChange) onSymbolChange(defaultSymbol);
    }
  }, [symbols]); // eslint-disable-line react-hooks/exhaustive-deps

  const errors = useMemo(() => validateForm(form), [form]);
  const hasErrors = Object.keys(errors).length > 0;
  const shown = touched ? errors : {};

  const setLeft = (patch) => setForm((f) => ({ ...f, left: { ...f.left, ...patch } }));
  const setTarget = (patch) => setForm((f) => ({ ...f, target: { ...f.target, ...patch } }));

  const onLeftTypeChange = (type) => {
    const def = LEFT_INDICATORS.find((i) => i.value === type);
    setLeft({ type, length: def?.hasLength ? def.defaultLength : "" });
  };

  const applyTemplate = (id) => {
    const t = TEMPLATES.find((x) => x.id === id);
    if (!t) return;
    setForm((f) => ({
      ...f,
      left: { ...t.left },
      operator: t.operator,
      target: { ...f.target, ...t.target },
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
      setServerError(err.message || "Không thể tạo luật.");
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
      <div className="section-heading"><span className="section-icon"><Icon name="plus" size={19} /></span>
        <div><h2 id="form-title" className="card-title">Tạo luật mới</h2><p className="section-description">Bắt đầu với một điều kiện bạn muốn theo dõi.</p></div></div>

      <Field id="template" label="Bắt đầu từ luật mẫu">
        <select id="template" defaultValue="" onChange={(e) => applyTemplate(e.target.value)}>
          <option value="">— Chọn luật mẫu —</option>
          {TEMPLATES.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
      </Field>

      <div className="form-step"><span>01</span> Chọn thị trường</div>
      <Field id="symbol-search" label="Tìm cặp giao dịch">
        <div className="search-field"><Icon name="search" size={17} /><input id="symbol-search" type="search"
          placeholder="Tìm BTC, ETH, SOL…" value={symbolSearch}
          onKeyDown={(event) => { if (event.key === "Enter") event.preventDefault(); }}
          onChange={(event) => setSymbolSearch(event.target.value)} /></div>
        {symbolSearch && <p className="field-hint" role="status">{filteredSymbols.length ? `${filteredSymbols.length} cặp phù hợp` : "Không tìm thấy cặp phù hợp. Cặp đang chọn được giữ lại."}</p>}
      </Field>

      <div className="row">
        <Field id="symbol" label="Cặp giao dịch" error={shown.symbol}>
          <select
            id="symbol"
            value={form.symbol}
            onChange={(e) => {
              const val = e.target.value;
              setForm({ ...form, symbol: val });
              if (onSymbolChange) onSymbolChange(val);
            }}
          >
            {symbols.length === 0 && <option value="">Đang tải…</option>}
            {visibleSymbols.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </Field>
        <Field id="timeframe" label="Khung thời gian">
          <select
            id="timeframe"
            value={form.timeframe}
            onChange={(e) => {
              const val = e.target.value;
              setForm({ ...form, timeframe: val });
              if (onTimeframeChange) onTimeframeChange(val);
            }}
          >
            {TIMEFRAMES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
        </Field>
      </div>

      <fieldset className="group">
        <legend><span className="step-number">02</span> Thiết lập điều kiện</legend>

        <div className="row">
          <Field id="left-type" label="Chỉ báo cần theo dõi">
            <select id="left-type" value={form.left.type} onChange={(e) => onLeftTypeChange(e.target.value)}>
              {LEFT_INDICATORS.map((i) => <option key={i.value} value={i.value}>{i.label}</option>)}
            </select>
          </Field>
          {leftDef?.hasLength && (
            <Field id="left-length" label="Chu kỳ (số nến)" error={shown.leftLength}>
              <input
                id="left-length" type="number" min="1" max={MAX_LENGTH} inputMode="numeric"
                value={form.left.length} onChange={(e) => setLeft({ length: e.target.value })}
              />
            </Field>
          )}
        </div>

        <Field id="operator" label="Điều kiện so sánh" hint={opDef?.hint}>
          <select id="operator" value={form.operator} onChange={(e) => setForm({ ...form, operator: e.target.value })}>
            {OPERATORS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </Field>

        <div className="field">
          <span className="label" id="target-label">So sánh với</span>
          <div className="segmented" role="group" aria-labelledby="target-label">
            {[["value", "Giá trị"], ["indicator", "Chỉ báo"]].map(([mode, text]) => (
              <button
                key={mode} type="button" aria-pressed={form.target.mode === mode}
                className={form.target.mode === mode ? "seg active" : "seg"}
                onClick={() => setTarget({ mode })}
              >
                {text}
              </button>
            ))}
          </div>
        </div>

        {form.target.mode === "value" ? (
          <Field id="target-value" label="Giá trị" error={shown.targetValue}
            hint={form.left.type === "rsi" ? "RSI nằm trong khoảng 0–100." : undefined}>
            <input
              id="target-value" type="number" step="any" inputMode="decimal"
              value={form.target.value} onChange={(e) => setTarget({ value: e.target.value })}
            />
          </Field>
        ) : (
          <div className="row">
            <Field id="target-type" label="Chỉ báo đích">
              <select id="target-type" value={form.target.type} onChange={(e) => setTarget({ type: e.target.value })}>
                {TARGET_INDICATORS.map((i) => <option key={i.value} value={i.value}>{i.label}</option>)}
              </select>
            </Field>
            <Field id="target-length" label="Chu kỳ (số nến)" error={shown.targetLength}>
              <input
                id="target-length" type="number" min="1" max={MAX_LENGTH} inputMode="numeric"
                value={form.target.length} onChange={(e) => setTarget({ length: e.target.value })}
              />
            </Field>
          </div>
        )}
      </fieldset>

      <div className="form-step"><span>03</span> Chọn dữ liệu nến</div>

      <Field id="candle-mode" label="Chế độ nến" hint={modeDef?.hint}>
        <select id="candle-mode" value={form.candleMode} onChange={(e) => setForm({ ...form, candleMode: e.target.value })}>
          {CANDLE_MODES.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
        </select>
      </Field>

      <div className="preview" aria-live="polite">
        <span className="preview-label">Xem trước</span>
        <p className="preview-text">
          {hasErrors ? "Hoàn tất các trường để xem mô tả luật." : describeRule(payload)}
        </p>
      </div>

      {serverError && <p className="banner error" role="alert">{serverError}</p>}
      {saved && <p className="banner success" role="status"><Icon name="check" size={17} /> Đã lưu luật. Bạn có thể xem trong danh sách bên dưới.</p>}

      <button id="submit-rule" className="btn primary" type="submit" disabled={submitting || !symbols.length}>
        <Icon name="plus" size={18} />{submitting ? "Đang lưu…" : "Lưu luật"}
      </button>
      <p className="local-note">Lưu trên trình duyệt này · Chưa gửi cảnh báo tự động</p>
    </form>
  );
}
