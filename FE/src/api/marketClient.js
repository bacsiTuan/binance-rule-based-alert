// Injectable fetch keeps the HTTP contract testable without a running backend.
export function createMarketApi({ base = "/api", fetcher = globalThis.fetch } = {}) {
  async function request(path, options = {}) {
    let response;
    try {
      response = await fetcher(`${base}${path}`, options);
    } catch (error) {
      if (error.name === "AbortError") throw error;
      throw new Error("Không kết nối được backend. Kiểm tra BE và cấu hình VITE_API_TARGET.");
    }
    let body;
    try {
      body = await response.json();
    } catch {
      throw new Error(`Backend trả dữ liệu không hợp lệ (HTTP ${response.status}).`);
    }
    if (!response.ok) {
      const detail = body.detail;
      const message = typeof detail === "string" ? detail
        : Array.isArray(detail) ? detail.map((item) => item.msg).join("; ")
        : detail?.message || `Lỗi HTTP ${response.status}`;
      const retry = body.retry_after ? ` Thử lại sau ${body.retry_after} giây.` : "";
      throw new Error(message + retry);
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
