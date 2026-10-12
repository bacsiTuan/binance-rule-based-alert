import { useLanguage } from "./LanguageContext.jsx";
import { useEffect, useState } from "react";
import { api, isMock } from "./api/client.js";
import { createRulesApi } from "./api/rulesClient.js";
import IndicatorPanel from "./components/IndicatorPanel.jsx";
import RuleForm from "./components/RuleForm.jsx";
import RuleList from "./components/RuleList.jsx";
import TradingViewWidget from "./components/TradingViewWidget.jsx";
import Icon from "./components/Icon.jsx";
import { TIMEFRAMES } from "./constants.js";

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

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem("indicator_alert_theme", theme); } catch { /* Vẫn đổi giao diện khi trình duyệt chặn lưu trữ. */ }
  }, [theme]);

  useEffect(() => {
    let cancelled = false;
    ruleStore.getRules().then((items) => {
      if (!cancelled) setRules(items);
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
    setRules((prev) => [...prev, rule]);
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

  const handleSelectRule = (rule) => {
    if (rule.symbol) setActiveSymbol(rule.symbol);
    if (rule.timeframe) setActiveTimeframe(rule.timeframe);
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
          <a href="#saved-rules">{t("Luật đã lưu")} <span>{rules.length}</span></a>
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
        <a className="btn primary heading-action" href="#rule-form"><Icon name="plus" size={18} /> {t("Tạo luật mới")}</a>
      </section>

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
          <div className="chart-foot"><span><span className="status-dot" /> {t("Biểu đồ từ TradingView")}</span><span>{t("Chọn cặp giao dịch trong form bên cạnh")}</span></div>
        </section>

        <IndicatorPanel request={indicatorRequest} />
        </div>

        {/* CỘT 2: 1/3 CÒN LẠI PHÂN BỐ DỌC TỪ TRÊN XUỐNG DƯỚI */}
        <aside className="sidebar-panels">
          {/* PHẦN 1: TẠO LUẬT MỚI */}
          <div className="sidebar-item">
            <RuleForm
              symbols={symbols}
              onSubmit={createRule}
              activeSymbol={activeSymbol}
              onSymbolChange={setActiveSymbol}
              activeTimeframe={activeTimeframe}
              onTimeframeChange={setActiveTimeframe}
              onIndicatorRequestChange={setIndicatorRequest}
            />
          </div>

          {/* PHẦN 2: LUẬT ĐÃ TẠO */}
          <div className="sidebar-item">
            <RuleList
              rules={rules}
              loading={loading}
              error={error}
              onToggle={toggleRule}
              onDelete={deleteRule}
              activeSymbol={activeSymbol}
              onSelectRule={handleSelectRule}
            />
          </div>
        </aside>
      </main>

      <footer className="footnote">
        {t("Tín hiệu chỉ là cảnh báo, không phải dự đoán hay lời khuyên đầu tư.")}
      </footer>
    </div>
  );
}
