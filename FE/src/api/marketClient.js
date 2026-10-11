import { BackendError, LocalizedError } from "../i18n.js";

// Injectable fetch keeps the HTTP contract testable without a running backend.
export function createMarketApi({ base = "/api", fetcher = globalThis.fetch } = {}) {
  async function request(path, options = {}) {
    let response;
    try {
      response = await fetcher(`${base}${path}`, options);
    } catch (error) {
      if (error.name === "AbortError") throw error;
      throw new LocalizedError("Không kết nối được backend. Kiểm tra BE và cấu hình VITE_API_TARGET.");
    }
    let body;
    try {
      body = await response.json();
    } catch {
      throw new LocalizedError("Backend trả dữ liệu không hợp lệ (HTTP {status}).", { status: response.status });
    }
    if (!response.ok) {
      const detail = body.detail;
      const message = typeof detail === "string" ? detail
        : Array.isArray(detail) ? detail.map((item) => item.msg).join("; ")
        : detail?.message || `HTTP error ${response.status}`;
      throw new BackendError(message, body.retry_after);
    }
    return body;
  }
  return {
    getSymbols: (options = {}) => request("/symbols", options),
    getIndicators: (payload, { signal } = {}) => request("/indicators", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal,
    }),
  };
}
