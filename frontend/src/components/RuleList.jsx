import { describeRule } from "../ruleUtils.js";

// Danh sách luật tối giản để xem kết quả của form. Ticket E4-3 sẽ hoàn thiện thêm.
export default function RuleList({ rules, loading, error, onToggle, onDelete }) {
  return (
    <section className="card" aria-labelledby="list-title">
      <h2 id="list-title" className="card-title">
        Luật đã tạo <span className="count">{rules.length}</span>
      </h2>

      {error && <p className="banner error" role="alert">{error}</p>}
      {loading && <p className="muted">Đang tải…</p>}
      {!loading && !error && rules.length === 0 && (
        <p className="empty">Chưa có luật nào. Hãy tạo luật đầu tiên ở bên trái.</p>
      )}

      <ul className="rule-list">
        {rules.map((r) => (
          <li key={r.id} className={r.enabled ? "rule" : "rule off"}>
            <div className="rule-main">
              <p className="rule-text">{describeRule(r)}</p>
              <p className="rule-meta">
                {r.candle_mode === "closed" ? "Nến đã đóng" : "Gồm nến hiện tại"}
                {" · "}#{r.id}
              </p>
            </div>
            <label className="switch" title={r.enabled ? "Đang bật" : "Đang tắt"}>
              <input
                type="checkbox" checked={r.enabled}
                aria-label={`Bật/tắt luật ${r.id}`}
                onChange={() => onToggle(r)}
              />
              <span className="slider" />
            </label>
            <button
              type="button" className="icon-btn" aria-label={`Xóa luật ${r.id}`}
              onClick={() => window.confirm("Xóa luật này?") && onDelete(r.id)}
            >
              ✕
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
