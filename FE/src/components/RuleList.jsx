import { useLanguage } from "../LanguageContext.jsx";
import { describeRule } from "../ruleUtils.js";
import Icon from "./Icon.jsx";

export default function RuleList({
  rules,
  loading,
  error,
  onToggle,
  onDelete,
  activeSymbol,
  onSelectRule,
}) {
  const { t, language, localizedError } = useLanguage();
  return (
    <section id="saved-rules" className="card" aria-labelledby="list-title">
      <div className="section-heading"><span className="section-icon"><Icon name="bookmark" size={19} /></span>
        <h2 id="list-title" className="card-title">{t("Luật đã lưu")} <span className="count">{rules.length}</span></h2></div>

      {error && <p className="banner error" role="alert">{localizedError(error)}</p>}
      {loading && <p className="muted">{t("Đang tải…")}</p>}
      {!loading && !error && rules.length === 0 && (
        <div className="empty"><span className="empty-icon"><Icon name="bookmark" size={25} /></span>
          <strong>{t("Điều kiện đầu tiên của bạn")}</strong><p>{t("Chọn một luật mẫu ở trên, chỉnh điều kiện và nhấn “Lưu luật” để bắt đầu.")}</p></div>
      )}

      <ul className="rule-list">
        {rules.map((r) => {
          const isSelected = activeSymbol === r.symbol;
          return (
            <li
              key={r.id}
              className={`rule ${r.enabled ? "" : "off"} ${isSelected ? "selected" : ""}`}
            >
              <button type="button" className="rule-main" aria-pressed={isSelected}
                onClick={() => onSelectRule?.(r)} title={t("Xem biểu đồ của cặp này")}>
                <span className="rule-text">{describeRule(r, language)}</span>
                <span className="rule-meta">
                  {r.candle_mode === "closed" ? t("Nến đã đóng") : t("Gồm nến hiện tại")}
                  {" · "}{r.enabled ? t("Đang bật") : t("Đang tắt")}
                </span>
              </button>
              <label
                className="switch"
                title={r.enabled ? t("Đang bật") : t("Đang tắt")}
                onClick={(e) => e.stopPropagation()}
              >
                <input
                  type="checkbox"
                  checked={r.enabled}
                  aria-label={t("Bật/tắt luật {id}", { id: r.id })}
                  onChange={() => onToggle(r)}
                />
                <span className="slider" />
              </label>
              <button
                type="button"
                className="icon-btn"
                aria-label={t("Xóa luật {id}", { id: r.id })}
                onClick={(e) => {
                  e.stopPropagation();
                  if (window.confirm(t("Xóa luật này?"))) onDelete(r.id);
                }}
              >
                <Icon name="trash" size={17} />
              </button>
            </li>
          );
        })}
      </ul>
      <p className="local-note">{t("Bật/tắt lưu trạng thái trên máy này, chưa chạy cảnh báo.")}</p>
    </section>
  );
}
