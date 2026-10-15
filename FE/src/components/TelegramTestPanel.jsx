import { useRef, useState } from "react";
import { useLanguage } from "../LanguageContext.jsx";

const outcomes = {
  accepted: "Telegram đã nhận bản phân tích. Mở cuộc trò chuyện với bot để xem.",
  failed: "Telegram từ chối tin nhắn. Kiểm tra bot token, chat ID và quyền gửi tin.",
  unknown: "Chưa xác định tin đã tới Telegram chưa. Kiểm tra cuộc trò chuyện trước khi gửi thêm.",
  pending: "Lần gửi này đang xử lý hoặc chưa có kết quả xác nhận. Kiểm tra Telegram, không gửi lặp lại.",
  generation_failed: "Chưa tạo được phân tích AI, chưa gửi Telegram.",
  not_sent: "Yêu cầu bị từ chối trước khi gửi Telegram. Sửa lỗi rồi mở lại mục kiểm tra.",
};

export default function TelegramTestPanel({ api, symbol, interval, onBack, onBusyChange }) {
  const { t, localizedError } = useLanguage();
  // Freeze context throughout confirmation and delivery, even if the dashboard changes.
  const [scope] = useState({ symbol, interval, language: "en" });
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const requestId = useRef(crypto.randomUUID());
  const inFlight = useRef(false);

  async function send() {
    if (!confirming || inFlight.current || result) return;
    inFlight.current = true; setBusy(true); onBusyChange(true); setError(null);
    try {
      const response = await api.telegramTest({ ...scope, request_id: requestId.current, confirmed: true });
      setResult(outcomes[response.status] ? response.status : "unknown");
    } catch (err) {
      setError(err);
      // A lost HTTP response does not prove that delivery failed. Never retry automatically.
      setResult(["telegram_test_disabled", "telegram_test_unauthorized", "telegram_test_rate_limited",
        "telegram_test_conflict", "telegram_test_local_only", "telegram_test_proxy_unconfigured",
        "ai_busy", "ai_failed", "ai_data_unavailable"].includes(err.code) ? "not_sent" : "unknown");
    } finally {
      setBusy(false); onBusyChange(false); inFlight.current = false;
    }
  }

  return <div className="assistant-test">
    <button className="assistant-test-back" type="button" disabled={busy} onClick={onBack}>← {t("Quay lại trò chuyện")}</button>
    <span className="assistant-test-label">{t("KIỂM TRA KẾT NỐI")}</span>
    <h3>{t("Gửi nhận định qua Telegram")}</h3>
    <p>{t("Gửi nhận định thị trường của cặp đang xem tới Telegram. Thời gian hiển thị theo múi giờ đã cấu hình.")}</p>
    <div className="assistant-test-scope">{scope.symbol} · {scope.interval.toUpperCase()} · {scope.language.toUpperCase()}</div>
    {!result && <>
      <small>{t("Khóa được tự nhận từ .env trên máy chủ, không cần nhập tại đây.")}</small>
      {!confirming ? <button className="btn primary" type="button"
        onClick={() => setConfirming(true)}>{t("Chuẩn bị gửi")}</button> : <div className="assistant-test-confirm">
        <p>{t("Xác nhận gửi một tin thật tới chat Telegram đã cấu hình? Thao tác này sử dụng API AI.")}</p>
        <button className="btn primary" type="button" disabled={busy} onClick={send}>
          {t(busy ? "Đang phân tích và gửi…" : "Xác nhận gửi")}</button>
        <button className="assistant-test-back" type="button" disabled={busy} onClick={() => setConfirming(false)}>{t("Hủy")}</button>
      </div>}
    </>}
    {error && <p className="assistant-test-error" role="alert">{localizedError(error)}</p>}
    {result && <p className={`assistant-test-result ${result === "accepted" ? "success" : ""}`} role="status">{t(outcomes[result])}</p>}
    <p className="assistant-test-hint">{t("Tối đa một lần/phút. Kiểm tra Telegram trước khi gửi lại nếu mất kết nối.")}</p>
  </div>;
}
