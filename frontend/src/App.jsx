import { useCallback, useEffect, useState } from "react";
import { api, isMock } from "./api/client.js";
import RuleForm from "./components/RuleForm.jsx";
import RuleList from "./components/RuleList.jsx";

export default function App() {
  const [symbols, setSymbols] = useState([]);
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [s, r] = await Promise.all([api.getSymbols(), api.getRules()]);
      setSymbols(s);
      setRules(r);
    } catch (e) {
      setError(`Không tải được dữ liệu: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const createRule = async (payload) => {
    const rule = await api.createRule(payload); // lỗi sẽ được RuleForm hiển thị
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

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <h1>Indicator Alert</h1>
          <p className="subtitle">Cảnh báo chỉ báo kỹ thuật cho dữ liệu Binance · 1h / 1D / 1W</p>
        </div>
        <span className={isMock ? "pill mock" : "pill live"}>
          {isMock ? "Dữ liệu giả" : "API thật"}
        </span>
      </header>

      <main className="layout">
        <RuleForm symbols={symbols} onSubmit={createRule} />
        <RuleList
          rules={rules} loading={loading} error={error}
          onToggle={toggleRule} onDelete={deleteRule}
        />
      </main>

      <footer className="footnote">
        Tín hiệu chỉ là cảnh báo, không phải dự đoán hay lời khuyên đầu tư.
      </footer>
    </div>
  );
}
