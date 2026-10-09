import { useCallback, useEffect, useState } from "react";
import { api, isMock } from "./api/client.js";
import RuleForm from "./components/RuleForm.jsx";
import RuleList from "./components/RuleList.jsx";
import TradingViewWidget from "./components/TradingViewWidget.jsx";

export default function App() {
  const [symbols, setSymbols] = useState([]);
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Đồng bộ symbol và timeframe đang xem giữa Biểu đồ và Form tạo luật
  const [activeSymbol, setActiveSymbol] = useState("BTCUSDT");
  const [activeTimeframe, setActiveTimeframe] = useState("1d");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [s, r] = await Promise.all([api.getSymbols(), api.getRules()]);
      setSymbols(s);
      setRules(r);
      if (s.length > 0 && !s.includes(activeSymbol)) {
        setActiveSymbol(s[0]);
      }
    } catch (e) {
      setError(`Không tải được dữ liệu: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }, [activeSymbol]);

  useEffect(() => {
    load();
  }, [load]);

  const createRule = async (payload) => {
    const rule = await api.createRule(payload);
    setRules((prev) => [...prev, rule]);
  };

  const toggleRule = async (rule) => {
    try {
      const updated = await api.updateRule(rule.id, { enabled: !rule.enabled });
      setRules((prev) => prev.map((r) => (r.id === rule.id ? updated : r)));
    } catch (e) {
      setError(e.message);
    }
  };

  const deleteRule = async (id) => {
    try {
      await api.deleteRule(id);
      setRules((prev) => prev.filter((r) => r.id !== id));
    } catch (e) {
      setError(e.message);
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
          <h1>Indicator Alert</h1>
          <p className="subtitle">
            Cảnh báo chỉ báo kỹ thuật cho dữ liệu Binance · 1h / 1D / 1W
          </p>
        </div>
        <div className="topbar-actions">
          <span className={isMock ? "pill mock" : "pill live"}>
            {isMock ? "Chế độ Mock (Dữ liệu giả)" : "Kết nối API thật"}
          </span>
        </div>
      </header>

      {/* Layout tỷ lệ 2/3 (Biểu đồ) và 1/3 (Tạo luật + Danh sách luật xếp dọc) */}
      <main className="main-grid">
        {/* CỘT 1: BIỂU ĐỒ TRADINGVIEW (CHIẾM 2/3 DIỆN TÍCH) */}
        <section className="card chart-panel" aria-label="Biểu đồ kỹ thuật">
          <div className="chart-header">
            <div className="chart-title-group">
              <h2 className="card-title" style={{ margin: 0 }}>
                Biểu đồ phân tích kỹ thuật
              </h2>
              <span className="badge-ticker">
                BINANCE:{activeSymbol} · {activeTimeframe.toUpperCase()}
              </span>
            </div>
            <a
              href="https://vn.tradingview.com/chart/wrq6D5Ts/"
              target="_blank"
              rel="noopener noreferrer"
              className="tv-link-btn"
              title="Mở layout TradingView cá nhân của bạn trên tab mới"
            >
              Mở layout cá nhân (wrq6D5Ts) ↗
            </a>
          </div>

          <div className="chart-body">
            <TradingViewWidget
              symbol={activeSymbol}
              interval={activeTimeframe}
            />
          </div>
        </section>

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
        Tín hiệu chỉ là cảnh báo, không phải dự đoán hay lời khuyên đầu tư.
      </footer>
    </div>
  );
}
