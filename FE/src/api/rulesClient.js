import { createLocalRules } from "./localRules.js";
import { LocalizedError } from "../i18n.js";

const BASE = "/api";
const triggerErrors = {
  telegram_test_disabled: "Gửi thử chưa được bật trên backend.",
  telegram_test_unauthorized: "Khóa kiểm thử không đúng.",
  telegram_test_local_only: "Hãy mở web bằng localhost hoặc 127.0.0.1 trên máy chạy frontend để gửi thử.",
  telegram_test_proxy_unconfigured: "Chưa đọc được khóa kiểm thử. Kiểm tra .env gốc và khởi động lại frontend.",
  telegram_test_rate_limited: "Mỗi phút chỉ gửi thử một lần. Vui lòng đợi rồi thử lại.",
  "Telegram notifications are not enabled": "Lịch cảnh báo Telegram đang tắt. Bạn vẫn có thể gửi thử AI trong mục Kiểm tra kết nối.",
};

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
    throw new LocalizedError(triggerErrors[detail] || detail);
  }

  return res.status === 204 ? null : res.json();
}

export function createRulesApi(isMock = false) {
  if (isMock) {
    return createLocalRules(true);
  }

  return {
    triggerAll: async (requestId) => request("/telegram/trigger", {
      method: "POST", body: JSON.stringify({ request_id: requestId, confirmed: true }),
    }),
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
