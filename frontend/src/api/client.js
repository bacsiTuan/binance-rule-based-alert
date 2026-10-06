import { MOCK_RULES, MOCK_SYMBOLS } from "./mockData.js";

const USE_MOCK = import.meta.env.VITE_USE_MOCK !== "false";
const BASE = "/api"; // Vite proxy chuyển tiếp tới FastAPI (xem vite.config.js)
const STORE_KEY = "mock_rules";

const delay = (ms = 350) => new Promise((r) => setTimeout(r, ms));

// ---------- Mock: lưu luật trong localStorage để F5 không mất ----------
function loadMockRules() {
  try {
    const saved = localStorage.getItem(STORE_KEY);
    if (saved) return JSON.parse(saved);
  } catch {
    /* bỏ qua, dùng dữ liệu mặc định */
  }
  return structuredClone(MOCK_RULES);
}
const saveMockRules = (rules) => localStorage.setItem(STORE_KEY, JSON.stringify(rules));

const mockApi = {
  async getSymbols() {
    await delay(200);
    return MOCK_SYMBOLS;
  },
  async getRules() {
    await delay();
    return loadMockRules();
  },
  async createRule(payload) {
    await delay();
    const rules = loadMockRules();
    const rule = {
      ...payload,
      id: Math.max(0, ...rules.map((r) => r.id)) + 1,
      enabled: true,
      created_at: new Date().toISOString(),
    };
    rules.push(rule);
    saveMockRules(rules);
    return rule;
  },
  async updateRule(id, patch) {
    await delay(150);
    const rules = loadMockRules().map((r) => (r.id === id ? { ...r, ...patch } : r));
    saveMockRules(rules);
    return rules.find((r) => r.id === id);
  },
  async deleteRule(id) {
    await delay(150);
    saveMockRules(loadMockRules().filter((r) => r.id !== id));
  },
};

// ---------- API thật (FastAPI) ----------
async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = `Lỗi ${res.status}`;
    try {
      const body = await res.json();
      // FastAPI trả {detail: "..."} hoặc {detail: [{msg: "..."}]}
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail)) detail = body.detail.map((d) => d.msg).join("; ");
    } catch {
      /* giữ thông báo mặc định */
    }
    throw new Error(detail);
  }
  return res.status === 204 ? null : res.json();
}

const realApi = {
  getSymbols: () => request("/symbols"),
  getRules: () => request("/rules"),
  createRule: (payload) => request("/rules", { method: "POST", body: JSON.stringify(payload) }),
  updateRule: (id, patch) => request(`/rules/${id}`, { method: "PATCH", body: JSON.stringify(patch) }),
  deleteRule: (id) => request(`/rules/${id}`, { method: "DELETE" }),
};

export const api = USE_MOCK ? mockApi : realApi;
export const isMock = USE_MOCK;
