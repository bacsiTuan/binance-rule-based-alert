import { LocalizedError } from "../i18n.js";

const errors = {
  ai_unavailable: "Trợ lý AI chưa sẵn sàng. Vui lòng thử lại sau.",
  ai_busy: "Trợ lý đang bận. Vui lòng đợi một phút rồi thử lại.",
  ai_failed: "Chưa nhận được phản hồi từ AI. Bạn có thể thử lại.",
  telegram_test_disabled: "Gửi thử chưa được bật trên backend.",
  telegram_test_unauthorized: "Khóa kiểm thử không đúng.",
  telegram_test_local_only: "Hãy mở web bằng localhost hoặc 127.0.0.1 trên máy chạy frontend để gửi thử.",
  telegram_test_proxy_unconfigured: "Chưa đọc được khóa kiểm thử. Kiểm tra .env gốc và khởi động lại frontend.",
  telegram_test_rate_limited: "Mỗi phút chỉ gửi thử một lần. Vui lòng đợi rồi thử lại.",
  telegram_test_conflict: "Phiên kiểm thử không hợp lệ. Hãy mở lại mục kiểm tra.",
};

export function createAssistantApi({ fetcher = globalThis.fetch } = {}) {
  async function request(path, options) {
    let response;
    try { response = await fetcher(`/api/ai/${path}`, options); }
    catch (error) {
      if (error.name === "AbortError") throw error;
      throw new LocalizedError("Không kết nối được trợ lý. Kiểm tra kết nối và thử lại.");
    }
    let data;
    try { data = await response.json(); }
    catch { throw new LocalizedError("Chưa nhận được phản hồi từ AI. Bạn có thể thử lại."); }
    if (!response.ok) {
      const error = new LocalizedError(errors[data.detail] || "Không lấy được dữ liệu cho trợ lý. Vui lòng thử lại.");
      error.code = typeof data.detail === "string" ? data.detail : null;
      throw error;
    }
    return data;
  }
  return {
    status: ({ signal } = {}) => request("status", { signal }),
    chat: (body, { signal } = {}) => request("chat", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body), signal,
    }),
    telegramTest: (body) => request("telegram-test", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  };
}
