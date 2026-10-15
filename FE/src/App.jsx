import { useLanguage } from "./LanguageContext.jsx";
import { useEffect, useRef, useState } from "react";
import { api, isMock } from "./api/client.js";
import { createRulesApi } from "./api/rulesClient.js";
import IndicatorPanel from "./components/IndicatorPanel.jsx";
import RuleForm from "./components/RuleForm.jsx";
import RuleList from "./components/RuleList.jsx";
import TradingViewWidget from "./components/TradingViewWidget.jsx";
import Icon from "./components/Icon.jsx";
import MarketAssistant from "./components/MarketAssistant.jsx";
import { TIMEFRAMES } from "./constants.js";
import { LocalizedError } from "./i18n.js";
import { buildIndicatorRequest } from "./indicatorUtils.js";

const ruleStore = createRulesApi(isMock);

export default function App() {
  const { t, language, setLanguage, localizedError } = useLanguage();
  const [theme, setTheme] = useState(() => document.documentElement.dataset.theme === "light" ? "light" : "dark");
  const [symbols, setSymbols] = useState([]);
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [symbolError, setSymbolError] = useState("");
  const [symbolWarning, setSymbolWarning] = useState("");
  const [symbolRetry, setSymbolRetry] = useState(0);
  const [indicatorRequest, setIndicatorRequest] = useState(null);

  // Đồng bộ symbol và timeframe đang xem giữa Biểu đồ và Form tạo luật
  const [activeSymbol, setActiveSymbol] = useState("BTCUSDT");
  const [activeTimeframe, setActiveTimeframe] = useState("1d");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingRule, setEditingRule] = useState(null);
  const [triggering, setTriggering] = useState(false);
  const [triggerResult, setTriggerResult] = useState(null);
  const [triggerError, setTriggerError] = useState("");
  const [triggerConfirming, setTriggerConfirming] = useState(false);
  const triggerInFlight = useRef(false);
  const triggerRequestId = useRef(null);
  const alertDialog = useRef(null);
  const alertDialogOpen = isModalOpen || !!editingRule;

  useEffect(() => {
    if (!alertDialogOpen) return;
    const previousFocus = document.activeElement;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const dialog = alertDialog.current;
    const focusableElements = () => [...dialog.querySelectorAll(
      'button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), a[href], [tabindex="0"]',
    )].filter(element => element.getClientRects().length);
    const keepFocusInside = (event) => {
      if (event.key !== "Tab") return;
      const elements = focusableElements();
      const first = elements[0];
      const last = elements.at(-1);
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault(); last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault(); first?.focus();
      }
    };
    focusableElements()[0]?.focus();
    dialog.addEventListener("keydown", keepFocusInside);
    return () => {
      dialog.removeEventListener("keydown", keepFocusInside);
      document.body.style.overflow = previousOverflow;
      if (previousFocus?.isConnected) previousFocus.focus({ preventScroll: true });
    };
  }, [alertDialogOpen]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && (isModalOpen || editingRule)) {
        setIsModalOpen(false);
        setEditingRule(null);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isModalOpen, editingRule]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem("indicator_alert_theme", theme); } catch { /* Vẫn đổi giao diện khi trình duyệt chặn lưu trữ. */ }
  }, [theme]);

  useEffect(() => {
    let cancelled = false;
    ruleStore.getRules().then((items) => {
      if (!cancelled) {
        const sorted = [...items].sort((a, b) => (Number(b.id) || 0) - (Number(a.id) || 0));
        setRules(sorted);
      }
    }).catch((err) => {
      if (!cancelled) setError(err);
    }).finally(() => {
      if (!cancelled) setLoading(false);
    });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setSymbolError("");
    setSymbolWarning("");
    api.getSymbols({ signal: controller.signal }).then((result) => {
      if (controller.signal.aborted) return;
      setSymbols(result.symbols);
      setActiveSymbol((current) => result.symbols.length && !result.symbols.includes(current)
        ? result.symbols[0] : current);
      if (result.stale || result.warning) setSymbolWarning(result.warning || true);
    }).catch((err) => {
      if (!controller.signal.aborted) setSymbolError(err);
    });
    return () => controller.abort();
  }, [symbolRetry]);

  const createRule = async (payload) => {
    const rule = await ruleStore.createRule(payload);
    setRules((prev) => [rule, ...prev]);
  };

  const updateRule = async (id, payload) => {
    try {
      const updated = await ruleStore.updateRule(id, payload);
      setRules((prev) => prev.map((r) => (r.id === id ? updated : r)));
    } catch (e) {
      setError(e);
      throw e;
    }
  };

  const toggleRule = async (rule) => {
    try {
      const updated = await ruleStore.updateRule(rule.id, { enabled: !rule.enabled });
      setRules((prev) => prev.map((r) => (r.id === rule.id ? updated : r)));
    } catch (e) {
      setError(e);
    }
  };

  const deleteRule = async (id) => {
    try {
      await ruleStore.deleteRule(id);
      setRules((prev) => prev.filter((r) => r.id !== id));
    } catch (e) {
      setError(e);
    }
  };

  const triggerAll = async () => {
    if (!triggerConfirming || triggerInFlight.current) return;
    triggerInFlight.current = true;
    setTriggering(true);
    setTriggerResult(null);
    setTriggerError("");
    try {
      const result = await ruleStore.triggerAll(triggerRequestId.current);
      if (result.status === "complete") setTriggerResult(result.stats);
      else setTriggerError(new LocalizedError("Lần gửi này đang xử lý hoặc chưa có kết quả xác nhận. Kiểm tra Telegram, không gửi lặp lại."));
    } catch (e) {
      setTriggerError(e instanceof TypeError ? new LocalizedError("Chưa xác định tin đã tới Telegram chưa. Kiểm tra cuộc trò chuyện trước khi gửi thêm.") : e);
    } finally {
      triggerInFlight.current = false;
      setTriggering(false);
      setTriggerConfirming(false);
    }
  };

  const handleSelectRule = (rule) => {
    if (rule.symbol) setActiveSymbol(rule.symbol);
    if (rule.timeframe) setActiveTimeframe(rule.timeframe);
    setIndicatorRequest(buildIndicatorRequest(rule));
  };

  const visibleIndicatorRequest = isModalOpen || editingRule ? indicatorRequest : {
    ...(indicatorRequest || buildIndicatorRequest({ candle_mode: "closed" })),
    symbol: activeSymbol,
    interval: activeTimeframe,
  };

  return (
    <div className="app-container">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark"><Icon name="chart" size={24} /></span>
          <div><span className="brand-name">Indicator Alert</span><span className="brand-caption">{t("Không gian theo dõi thị trường")}</span></div>
        </div>
        <nav className="main-nav" aria-label={t("Điều hướng chính")}>
          <a className="nav-active" href="#market">{t("Tổng quan")}</a>
          <a href="#saved-rules">{t("Cảnh báo")} <span>{rules.length}</span></a>
        </nav>
        <div className="topbar-actions">
          <div className="language-switch" role="group" aria-label={t("Ngôn ngữ")}>
            <button type="button" lang="en" aria-label="English" aria-pressed={language === "en"}
              onClick={() => setLanguage("en")}>EN</button>
            <button type="button" lang="vi" aria-label="Tiếng Việt" aria-pressed={language === "vi"}
              onClick={() => setLanguage("vi")}>VI</button>
          </div>
          <button type="button" className="tv-link-btn theme-toggle"
            aria-label={theme === "dark" ? t("Chuyển sang giao diện sáng") : t("Chuyển sang giao diện tối")}
            title={theme === "dark" ? t("Chuyển sang giao diện sáng") : t("Chuyển sang giao diện tối")}
            onClick={() => setTheme(current => current === "dark" ? "light" : "dark")}>
            <Icon name={theme === "dark" ? "sun" : "moon"} size={18} />
            <span>{theme === "dark" ? t("Sáng") : t("Tối")}</span>
          </button>
          <span className={isMock ? "pill mock" : "pill live"}>
            <span className="status-dot" />{isMock ? t("Dữ liệu mẫu") : t("Dữ liệu Binance")}
          </span>
        </div>
      </header>

      <section className="page-heading" aria-labelledby="page-title">
        <div><p className="eyebrow">{t("THỊ TRƯỜNG / TỔNG QUAN")}</p>
          <h1 id="page-title">{t("Theo dõi thị trường")}</h1>
          <p className="subtitle">{t("Quan sát xu hướng, xem chỉ báo và thiết lập điều kiện của bạn.")}</p>
        </div>
        <button
          type="button"
          className="btn primary heading-action"
          onClick={() => { triggerRequestId.current = crypto.randomUUID(); setTriggerConfirming(true); }}
          disabled={triggering || triggerConfirming}
        >
          <Icon name="send" size={18} /> {triggering ? t("Đang kiểm tra…") : t("Kiểm tra tất cả luật")}
        </button>
      </section>

      {triggerConfirming && <section className="banner warning trigger-confirmation" aria-label={t("Xác nhận kiểm tra luật")}
        onKeyDown={event => { if (event.key === "Escape" && !triggering) setTriggerConfirming(false); }}>
        <p>{t("Kiểm tra các luật đang bật và gửi tin thật tới Telegram nếu thỏa điều kiện? Phân tích AI sẽ được đính kèm khi sẵn sàng.")}</p>
        <button className="btn primary" type="button" disabled={triggering} onClick={triggerAll}>
          {triggering ? t("Đang kiểm tra…") : t("Xác nhận kiểm tra và gửi")}</button>
        <button className="tv-link-btn" type="button" disabled={triggering} onClick={() => setTriggerConfirming(false)}>{t("Hủy")}</button>
      </section>}
      {triggerError && <div className="banner error" role="alert">{localizedError(triggerError)}</div>}
      {triggerResult && <p className={`banner ${triggerResult.failed || triggerResult.unknown ? "warning" : "success"}`} role="status">
        <Icon name="check" size={16} />
        {t("Đã kiểm tra {scanned} luật: {triggered} thỏa điều kiện, {accepted} tin được chấp nhận, {failed} bị từ chối, {unknown} chưa rõ kết quả, {skipped} bỏ qua, {cancelled} đã hủy.", {
          scanned: triggerResult.scanned, triggered: triggerResult.triggered,
          accepted: triggerResult.accepted, failed: triggerResult.failed, unknown: triggerResult.unknown,
          skipped: triggerResult.skipped, cancelled: triggerResult.cancelled || 0,
        })}
      </p>}

      {symbolError && <div className="banner error" role="alert">
        {t("Không tải được symbol")}: {localizedError(symbolError)} <button type="button" className="tv-link-btn"
          onClick={() => setSymbolRetry((value) => value + 1)}>{t("Thử lại")}</button>
      </div>}
      {symbolWarning && <p className="banner warning" role="status">{t("Danh sách symbol lấy từ cache cũ.")} {typeof symbolWarning === "string" && t(symbolWarning)}</p>}

      {/* Layout tỷ lệ 2/3 (Biểu đồ) và 1/3 (Tạo luật + Danh sách luật xếp dọc) */}
      <main className="main-grid">
        <div className="market-workspace" id="market">
        <section className="card chart-panel" aria-label={t("Biểu đồ kỹ thuật")}>
          <div className="chart-header">
            <div className="chart-title-group">
              <span className="asset-icon">{activeSymbol.slice(0, 1)}</span>
              <div><h2 className="card-title">{activeSymbol.replace(/USDT$/, " / USDT")}</h2>
                <p className="chart-subtitle">{t("Biểu đồ giá · TradingView")}</p></div>
            </div>
            <div className="timeframe-tabs" role="group" aria-label={t("Khung thời gian biểu đồ")}>
              {TIMEFRAMES.map((item) => <button key={item.value} type="button"
                aria-pressed={activeTimeframe === item.value}
                className={activeTimeframe === item.value ? "active" : ""}
                onClick={() => setActiveTimeframe(item.value)}>{item.value.toUpperCase()}</button>)}
            </div>
            <a
              href={`https://${language === "vi" ? "vn" : "www"}.tradingview.com/chart/?symbol=BINANCE%3A${encodeURIComponent(activeSymbol)}`}
              target="_blank"
              rel="noopener noreferrer"
              className="tv-link-btn"
              title={t("Mở TradingView trong tab mới")}
            >
              TradingView <Icon name="arrow" size={16} />
            </a>
          </div>

          <div className="chart-body">
            <TradingViewWidget
              symbol={activeSymbol}
              interval={activeTimeframe}
              theme={theme}
            />
          </div>
          <div className="chart-foot"><span><span className="status-dot" /> {t("Biểu đồ từ TradingView")}</span><span>{t("Nhấn nút Tạo cảnh báo để đặt điều kiện")}</span></div>
        </section>

        <IndicatorPanel request={visibleIndicatorRequest} />
        </div>

        {/* CỘT 2: 1/3 CÒN LẠI DÀNH TRỌN VẸN CHO QUẢN LÝ DANH SÁCH LUẬT VÀ NÚT TẠO CẢNH BÁO */}
        <aside className="sidebar-panels">
          <div className="sidebar-action-header">
            <button
              type="button"
              className="btn-open-alert-modal"
              onClick={() => setIsModalOpen(true)}
            >
              <Icon name="plus" size={18} /> {t("Tạo cảnh báo mới")}
            </button>
          </div>

          <div className="sidebar-item">
            <RuleList
              rules={rules}
              loading={loading}
              error={error}
              onToggle={toggleRule}
              onEdit={(rule) => setEditingRule(rule)}
              onDelete={deleteRule}
              activeSymbol={activeSymbol}
              activeTimeframe={activeTimeframe}
              onSelectRule={handleSelectRule}
            />
          </div>
        </aside>
      </main>

      <footer className="footnote">
        {t("Tín hiệu chỉ là cảnh báo, không phải dự đoán hay lời khuyên đầu tư.")}
      </footer>

      <MarketAssistant symbol={activeSymbol} interval={activeTimeframe} />

      {/* MODAL POPUP CHUẨN TRADINGVIEW (CREATE / UPDATE ALERT MODAL) */}
      {(isModalOpen || !!editingRule) && (
        <div
          className="modal-backdrop"
          onClick={() => {
            setIsModalOpen(false);
            setEditingRule(null);
          }}
          role="presentation"
        >
          <div
            ref={alertDialog}
            className="modal-container"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="modal-alert-title"
          >
            <div className="modal-header">
              <div className="modal-title-group">
                <span className="modal-icon"><Icon name={editingRule ? "edit" : "chart"} size={18} /></span>
                <h2 id="modal-alert-title" className="modal-title">
                  {editingRule
                    ? t("Cập nhật cảnh báo #{id}", { id: editingRule.id })
                    : t("Tạo cảnh báo trên {symbol}", { symbol: activeSymbol })}
                </h2>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => {
                  setIsModalOpen(false);
                  setEditingRule(null);
                }}
                aria-label={t("Đóng")}
              >
                ✕
              </button>
            </div>
            <div className="modal-body">
              <RuleForm
                symbols={symbols}
                initialRule={editingRule}
                onSubmit={async (payload) => {
                  if (editingRule) {
                    await updateRule(editingRule.id, payload);
                    setEditingRule(null);
                  } else {
                    await createRule(payload);
                    setIsModalOpen(false);
                  }
                }}
                activeSymbol={editingRule ? editingRule.symbol : activeSymbol}
                onSymbolChange={setActiveSymbol}
                activeTimeframe={editingRule ? editingRule.timeframe : activeTimeframe}
                onTimeframeChange={setActiveTimeframe}
                onIndicatorRequestChange={setIndicatorRequest}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
