import { describeRule } from "../ruleUtils.js";

export default function RuleList({
  rules,
  loading,
  error,
  onToggle,
  onDelete,
  activeSymbol,
  onSelectRule,
}) {
  return (
    <section className="card" aria-labelledby="list-title">
      <h2 id="list-title" className="card-title">
        Luật đã tạo <span className="count">{rules.length}</span>
      </h2>

      {error && <p className="banner error" role="alert">{error}</p>}
      {loading && <p className="muted">Đang tải…</p>}
      {!loading && !error && rules.length === 0 && (
        <p className="empty">Chưa có luật nào. Hãy tạo luật đầu tiên ở phía trên.</p>
      )}

      <ul className="rule-list">
        {rules.map((r) => {
          const isSelected = activeSymbol === r.symbol;
          return (
            <li
              key={r.id}
              className={`rule ${r.enabled ? "" : "off"} ${isSelected ? "selected" : ""}`}
              onClick={() => onSelectRule && onSelectRule(r)}
              title="Bấm để xem biểu đồ của cặp này"
              style={{ cursor: "pointer" }}
            >
              <div className="rule-main">
                <p className="rule-text">{describeRule(r)}</p>
                <p className="rule-meta">
                  {r.candle_mode === "closed" ? "Nến đã đóng" : "Gồm nến hiện tại"}
                  {" · "}#{r.id}
                </p>
              </div>
              <label
                className="switch"
                title={r.enabled ? "Đang bật" : "Đang tắt"}
                onClick={(e) => e.stopPropagation()}
              >
                <input
                  type="checkbox"
                  checked={r.enabled}
                  aria-label={`Bật/tắt luật ${r.id}`}
                  onChange={() => onToggle(r)}
                />
                <span className="slider" />
              </label>
              <button
                type="button"
                className="icon-btn"
                aria-label={`Xóa luật ${r.id}`}
                onClick={(e) => {
                  e.stopPropagation();
                  if (window.confirm("Xóa luật này?")) onDelete(r.id);
                }}
              >
                ✕
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
