import { useEffect, useRef, useState } from "react";
import { useLanguage } from "../LanguageContext.jsx";
import { createAssistantApi } from "../api/assistantClient.js";
import { isMock } from "../api/client.js";
import Icon from "./Icon.jsx";
import TelegramTestPanel from "./TelegramTestPanel.jsx";

const assistant = createAssistantApi();
const suggestions = ["Phân tích cặp đang chọn", "Giải thích RSI và đường trung bình", "Rule nào đang được Telegram hỗ trợ?"];

export default function MarketAssistant({ symbol, interval }) {
  const { t, localizedError } = useLanguage();
  const [open, setOpen] = useState(false);
  const [available, setAvailable] = useState(null);
  const [testAvailable, setTestAvailable] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testBusy, setTestBusy] = useState(false);
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [failedQuestion, setFailedQuestion] = useState("");
  const controller = useRef(null);
  const input = useRef(null);
  const end = useRef(null);
  const launcher = useRef(null);
  const inFlight = useRef(false);

  useEffect(() => () => controller.current?.abort(), []);
  useEffect(() => {
    if (!open) return;
    input.current?.focus();
    const statusController = new AbortController();
    if (isMock) { setAvailable(false); return; }
    assistant.status({ signal: statusController.signal }).then(data => {
      setAvailable(data.available); setTestAvailable(data.telegram_test_available === true);
    })
      .catch(err => { if (!statusController.signal.aborted) { setError(err); setAvailable(null); } });
    return () => statusController.abort();
  }, [open]);
  useEffect(() => { if (open) end.current?.scrollIntoView({ block: "nearest" }); }, [messages, busy, open]);

  const close = () => { if (testBusy) return; setOpen(false); setTesting(false); launcher.current?.focus(); };
  const send = async (question = draft) => {
    question = question.trim();
    if (!question || question.length > 2000 || inFlight.current || available === false) return;
    inFlight.current = true;
    const history = messages.filter(m => m.role === "user" || m.role === "assistant")
      .slice(-8).map(m => ({ role: m.role, content: m.content.slice(0, 2000) }));
    controller.current = new AbortController();
    setMessages(prev => [...prev, { role: "user", content: question }]);
    setDraft(""); setBusy(true); setError(null); setFailedQuestion("");
    try {
      const result = await assistant.chat({ message: question, history, symbol, interval, language: "en" },
        { signal: controller.current.signal });
      setMessages(prev => [...prev, { role: "assistant", content: result.answer,
        context: result.context, warnings: result.warnings || [] }]);
      setAvailable(true);
    } catch (err) {
      if (err.name !== "AbortError") {
        setError(err); setFailedQuestion(question);
        setMessages(prev => prev.slice(0, -1));
        setDraft(question);
      }
    } finally { inFlight.current = false; setBusy(false); }
  };

  return <div className="market-assistant">
    {open && <section className="assistant-panel" role="dialog" aria-label={t("Trợ lý thị trường")}
      onKeyDown={event => { if (event.key === "Escape") { event.stopPropagation(); close(); } }}>
      <header className="assistant-header">
        <span className="assistant-avatar"><Icon name="sparkles" size={22} /></span>
        <div><h2>{t("Trợ lý thị trường")}</h2><p>{t("Phân tích có dữ liệu, quyết định có cơ sở")}</p></div>
        <button className="icon-btn" type="button" disabled={testBusy} aria-label={t("Đóng trợ lý")} onClick={close}><Icon name="close" size={19} /></button>
      </header>
      <div className="assistant-context"><span className="status-dot" />{symbol} <span>· {interval.toUpperCase()}</span><small>{t("Dữ liệu nến đóng")}</small></div>
      {testing ? <div className="assistant-messages"><TelegramTestPanel api={assistant} symbol={symbol} interval={interval}
        onBack={() => setTesting(false)} onBusyChange={setTestBusy} /></div> : <>
      <div className="assistant-messages" role="log" aria-label={t("Cuộc trò chuyện")} aria-live="polite" aria-busy={busy}>
        {!messages.length && <div className="assistant-welcome">
          <span className="assistant-welcome-icon"><Icon name="sparkles" size={28} /></span>
          <h3>{t("Cùng đọc hiểu thị trường")}</h3>
          <p>{t("Hỏi về cặp đang xem, ý nghĩa tín hiệu hoặc cách hoạt động của cảnh báo. Tôi sẽ dùng dữ liệu chỉ báo từ hệ thống.")}</p>
          <div className="assistant-suggestions">{suggestions.map(text => <button key={text} type="button"
            disabled={busy || available === false} onClick={() => send(t(text))}>{t(text)}<Icon name="arrow" size={15} /></button>)}</div>
        </div>}
        {messages.map((message, index) => <article key={index} className={`assistant-message ${message.role}`}>
          <span className="assistant-speaker">{message.role === "user" ? t("Bạn") : t("Trợ lý AI")}</span>
          <div className="assistant-message-text" lang={message.role === "assistant" ? "en" : undefined}>{message.content}</div>
          {message.context && <small className="assistant-source" lang="en">{message.context.symbol} · {message.context.interval.toUpperCase()} · Closed candle
            {message.context.last_close_time != null && <> · {new Date(message.context.last_close_time).toLocaleString("en-GB")}</>}
            {message.warnings.includes("stale_data") && <> · Stale data</>}
            {message.warnings.includes("insufficient_data") && <> · Some indicators need more candles</>}
          </small>}
        </article>)}
        {busy && <p className="assistant-thinking" role="status"><span className="assistant-pulse" />{t("Đang đọc dữ liệu và phân tích…")}</p>}
        <div ref={end} />
      </div>
      {available === false && <p className="assistant-notice" role="status">{t("Trợ lý AI chưa sẵn sàng. Vui lòng thử lại sau.")}</p>}
      {error && <div className="assistant-error" role="alert">{localizedError(error)}
        {failedQuestion && <button type="button" disabled={busy} onClick={() => send(failedQuestion)}>{t("Thử lại")}</button>}</div>}
      <form className="assistant-compose" onSubmit={event => { event.preventDefault(); send(); }}>
        <label className="sr-only" htmlFor="assistant-question">{t("Câu hỏi của bạn")}</label>
        <textarea ref={input} id="assistant-question" rows={2} maxLength={2000} value={draft}
          disabled={available === false} placeholder={t("Hỏi về tín hiệu, chỉ báo, cảnh báo…")}
          onChange={event => setDraft(event.target.value)}
          onKeyDown={event => { if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); send(); } }} />
        <button type="submit" className="assistant-send" disabled={busy || available === false || !draft.trim()} aria-label={t("Gửi câu hỏi")}><Icon name="send" size={19} /></button>
      </form>
      <p className="assistant-footnote">{t("Nhận định AI có thể sai. Đối chiếu dữ liệu và quản lý rủi ro trước khi quyết định.")}</p>
      {testAvailable && <button className="assistant-diagnostics-link" type="button" disabled={busy}
        onClick={() => setTesting(true)}>{t("Kiểm tra kết nối")}</button>}
      </>}
    </section>}
    <button ref={launcher} className={`assistant-launcher ${open ? "is-open" : ""}`} type="button"
      disabled={testBusy} aria-expanded={open} aria-label={t(open ? "Đóng trợ lý" : "Mở trợ lý thị trường")}
      onClick={() => open ? close() : setOpen(true)}><Icon name={open ? "close" : "sparkles"} size={22} /><span>{t("Trợ lý AI")}</span></button>
  </div>;
}
