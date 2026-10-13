import { createLocalRules } from "./localRules.js";
import { LocalizedError } from "../i18n.js";

const BASE = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    let detail = `Lỗi máy chủ (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") {
        detail = body.detail;
      } else if (Array.isArray(body.detail)) {
        detail = body.detail.map((d) => d.msg || JSON.stringify(d)).join("; ");
      }
    } catch {
      /* fallback */
    }
    throw new LocalizedError(detail);
  }

  return res.status === 204 ? null : res.json();
}

export function createRulesApi(isMock = false) {
  if (isMock) {
    return createLocalRules(true);
  }

  return {
    getRules: async () => request("/rules"),
    createRule: async (payload) =>
      request("/rules", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    updateRule: async (id, patch) =>
      request(`/rules/${id}`, {
        method: "PATCH",
        body: JSON.stringify(patch),
      }),
    deleteRule: async (id) =>
      request(`/rules/${id}`, {
        method: "DELETE",
      }),
  };
}
