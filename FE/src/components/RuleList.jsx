import { useLanguage } from "../LanguageContext.jsx";
import { useMemo } from "react";
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
  const sortedRules = useMemo(() => {
    return [...rules].sort((a, b) => (Number(b.id) || 0) - (Number(a.id) || 0));
  }, [rules]);

  return (
    <section id="saved-rules" className="card" aria-labelledby="list-title">
      <div className="section-heading"><span className="section-icon"><Icon name="bookmark" size={19} /></span>
        <h2 id="list-title" className="card-title">{t("Cảnh báo đang theo dõi")} <span className="count">{rules.length}</span></h2></div>

      {error && <p className="banner error" role="alert">{localizedError(error)}</p>}
      {loading && <p className="muted">{t("Đang tải…")}</p>}
      {!loading && !error && rules.length === 0 && (
        <div className="empty"><span className="empty-icon"><Icon name="bookmark" size={25} /></span>
          <strong>{t("Điều kiện đầu tiên của bạn")}</strong><p>{t("Nhấn nút “Tạo cảnh báo mới” ở trên để thiết lập điều kiện theo dõi.")}</p></div>
      )}

      <ul className="rule-list">
        {sortedRules.map((r) => {
          const isSelected = activeSymbol === r.symbol;
          const triggerLabels = {
            once: "Chỉ 1 lần",
            once_per_bar_close: "Mỗi khi đóng nến",
            every_time: "Mọi lúc",
          };
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
                  {r.trigger_type ? ` · ${t(triggerLabels[r.trigger_type] || r.trigger_type)}` : ""}
                  {" · "}{r.enabled ? t("Đang bật") : t("Đang tắt")}
                </span>
                {r.message && (
                  <span style={{ fontSize: "0.75rem", opacity: 0.75, display: "block", marginTop: "2px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    💬 {r.message}
                  </span>
                )}
              </button>
              <label
                className="switch"
                title={r.enabled ? t("Đang bật") : t("Đang tắt")}
                onClick={(e) => e.stopPropagation()}
              >
                <input
                  type="checkbox"
                  checked={r.enabled}
                  aria-label={t("Bật/tắt cảnh báo {id}", { id: r.id })}
                  onChange={() => onToggle(r)}
                />
                <span className="slider" />
              </label>
              <button
                type="button"
                className="icon-btn"
                aria-label={t("Xóa cảnh báo {id}", { id: r.id })}
                onClick={(e) => {
                  e.stopPropagation();
                  if (window.confirm(t("Xóa cảnh báo này?"))) onDelete(r.id);
                }}
              >
                <Icon name="trash" size={17} />
              </button>
            </li>
          );
        })}
      </ul>
      <p className="local-note">{t("Bật/tắt lưu trạng thái trực tiếp trên Redis.")}</p>
    </section>
  );
}
