import { useEffect, useMemo, useState } from "react";
import {
  CANDLE_MODES, LEFT_INDICATORS, OPERATORS, TARGET_INDICATORS, TEMPLATES, TIMEFRAMES, MAX_LENGTH,
} from "../constants.js";
import { buildPayload, describeRule, initialForm, validateForm } from "../ruleUtils.js";

function Field({ id, label, error, hint, children }) {
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {children}
      {error ? <p className="field-error" role="alert">{error}</p> : hint ? <p className="field-hint">{hint}</p> : null}
    </div>
  );
}

export default function RuleForm({ symbols, onSubmit }) {
  const [form, setForm] = useState(initialForm);
  const [touched, setTouched] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [serverError, setServerError] = useState("");

  // Khi danh sách symbol tải xong mà symbol hiện tại không có trong đó, chọn symbol đầu tiên.
  useEffect(() => {
    if (symbols.length && !symbols.includes(form.symbol)) {
      setForm((f) => ({ ...f, symbol: symbols[0] }));
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
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setTouched(true);
    setServerError("");
    if (hasErrors) return;
    setSubmitting(true);
    try {
      await onSubmit(buildPayload(form));
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

  return (
    <form className="card" onSubmit={handleSubmit} noValidate aria-labelledby="form-title">
      <h2 id="form-title" className="card-title">Tạo luật mới</h2>

      <Field id="template" label="Luật mẫu" hint="Chọn nhanh một luật phổ biến, rồi chỉnh lại nếu cần.">
        <select id="template" defaultValue="" onChange={(e) => applyTemplate(e.target.value)}>
          <option value="">— Chọn luật mẫu —</option>
          {TEMPLATES.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
      </Field>

      <div className="row">
        <Field id="symbol" label="Symbol" error={shown.symbol}>
          <select id="symbol" value={form.symbol} onChange={(e) => setForm({ ...form, symbol: e.target.value })}>
            {symbols.length === 0 && <option value="">Đang tải…</option>}
            {symbols.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </Field>
        <Field id="timeframe" label="Khung thời gian">
          <select id="timeframe" value={form.timeframe} onChange={(e) => setForm({ ...form, timeframe: e.target.value })}>
            {TIMEFRAMES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
        </Field>
      </div>

      <fieldset className="group">
        <legend>Điều kiện</legend>

        <div className="row">
          <Field id="left-type" label="Chỉ báo (vế trái)">
            <select id="left-type" value={form.left.type} onChange={(e) => onLeftTypeChange(e.target.value)}>
              {LEFT_INDICATORS.map((i) => <option key={i.value} value={i.value}>{i.label}</option>)}
            </select>
          </Field>
          {leftDef?.hasLength && (
            <Field id="left-length" label="Length" error={shown.leftLength}>
              <input
                id="left-length" type="number" min="1" max={MAX_LENGTH} inputMode="numeric"
                value={form.left.length} onChange={(e) => setLeft({ length: e.target.value })}
              />
            </Field>
          )}
        </div>

        <Field id="operator" label="Toán tử" hint={opDef?.hint}>
          <select id="operator" value={form.operator} onChange={(e) => setForm({ ...form, operator: e.target.value })}>
            {OPERATORS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </Field>

        <div className="field">
          <span className="label" id="target-label">So với (vế phải)</span>
          <div className="segmented" role="radiogroup" aria-labelledby="target-label">
            {[["value", "Giá trị"], ["indicator", "Chỉ báo"]].map(([mode, text]) => (
              <button
                key={mode} type="button" role="radio" aria-checked={form.target.mode === mode}
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
            <Field id="target-length" label="Length" error={shown.targetLength}>
              <input
                id="target-length" type="number" min="1" max={MAX_LENGTH} inputMode="numeric"
                value={form.target.length} onChange={(e) => setTarget({ length: e.target.value })}
              />
            </Field>
          </div>
        )}
      </fieldset>

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
        <details>
          <summary>Xem JSON gửi lên backend</summary>
          <pre>{JSON.stringify(payload, null, 2)}</pre>
        </details>
      </div>

      {serverError && <p className="banner error" role="alert">{serverError}</p>}

      <button id="submit-rule" className="btn primary" type="submit" disabled={submitting}>
        {submitting ? "Đang lưu…" : "Tạo luật"}
      </button>
    </form>
  );
}
