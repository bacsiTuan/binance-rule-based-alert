import { MOCK_RULES } from "./mockData.js";

// Rules remain browser-local until the backend provides rule CRUD and an engine.
const STORE_KEY = "indicator_alert_rules";
const MOCK_STORE_KEY = "mock_rules";

function loadRules(mock) {
  const saved = localStorage.getItem(mock ? MOCK_STORE_KEY : STORE_KEY);
  if (saved) {
    const parsed = JSON.parse(saved);
    if (!Array.isArray(parsed)) throw new Error("Dữ liệu luật trong trình duyệt không hợp lệ.");
    return parsed;
  }
  return mock ? structuredClone(MOCK_RULES) : [];
}

export function createLocalRules(mock = false) {
  const save = (rules) => localStorage.setItem(
    mock ? MOCK_STORE_KEY : STORE_KEY, JSON.stringify(rules),
  );
  return {
    getRules: async () => loadRules(mock),
    async createRule(payload) {
      const rules = loadRules(mock);
      const rule = {
        ...payload,
        id: Math.max(0, ...rules.map((item) => item.id)) + 1,
        enabled: true,
        created_at: new Date().toISOString(),
      };
      save([...rules, rule]);
      return rule;
    },
    async updateRule(id, patch) {
      const rules = loadRules(mock);
      const rule = rules.find((item) => item.id === id);
      if (!rule) throw new Error("Không tìm thấy luật trong trình duyệt.");
      const updated = { ...rule, ...patch };
      save(rules.map((item) => item.id === id ? updated : item));
      return updated;
    },
    async deleteRule(id) {
      save(loadRules(mock).filter((item) => item.id !== id));
    },
  };
}
