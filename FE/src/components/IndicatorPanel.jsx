import { useEffect, useState } from "react";
import { api, isMock } from "../api/client.js";
import { displayValue } from "../indicatorUtils.js";
import Icon from "./Icon.jsx";

const sources = { binance: "Binance", cache: "Dữ liệu đã lưu", stale: "Dữ liệu cũ" };
const dateText = (value) => value == null ? "—" : new Date(value).toLocaleString("vi-VN");

export default function IndicatorPanel({ request }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const requestKey = JSON.stringify(request);

  useEffect(() => {
    setData(null);
    setError("");
    if (isMock || !request) {
      setLoading(false);
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    // Debounce edits and cancel old requests so another symbol's result cannot overwrite this one.
    const timer = setTimeout(async () => {
      try {
        const result = await api.getIndicators(JSON.parse(requestKey), { signal: controller.signal });
        if (!controller.signal.aborted) setData(result);
      } catch (err) {
        if (!controller.signal.aborted) setError(err.message);
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }, 350);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [requestKey, refresh]);

  return (
    <section className="card" aria-labelledby="indicators-title">
      <div className="indicator-heading">
        <div className="section-heading"><span className="section-icon"><Icon name="layers" size={19} /></span>
          <div><h2 id="indicators-title" className="card-title">Chỉ báo hiện tại</h2>
            <p className="section-description">Tính theo cặp giao dịch và điều kiện đang chọn.</p></div></div>
        <button className="tv-link-btn" type="button" disabled={isMock || !request || loading}
          onClick={() => setRefresh((value) => value + 1)}><Icon name="refresh" size={16} /> Làm mới</button>
      </div>
      {isMock ? <p className="muted">Chế độ dữ liệu mẫu chưa cung cấp kết quả chỉ báo.</p>
        : !request ? <p className="muted">Hoàn tất các trường hợp lệ trong form để tính chỉ báo.</p>
        : <>
          <div className="indicator-context"><span className="badge-ticker">{request.symbol}</span><span>{request.interval.toUpperCase()} · {request.include_open ? "Gồm nến hiện tại" : "Nến đã đóng"}</span></div>
          {loading && <p className="muted" role="status">Đang tính chỉ báo…</p>}
          {error && <p className="banner error" role="alert">{error}</p>}
          {data && <div aria-live="polite">
            {(data.stale || data.warning) && <p className="banner warning" role="status">Dữ liệu cache cũ. {data.warning}</p>}
            <ul className="indicator-values">
              {data.results.map((item) => <li key={`${item.name}:${item.period}`}>
                <span>{item.name.toUpperCase()}({item.period})</span>
                <strong title={item.latest.value ?? undefined}>{displayValue(item.latest.value)}</strong>
                <small>{item.latest.status === "insufficient_data"
                  ? `Chưa đủ nến (${item.available_candles}/${item.required_candles})`
                  : `Nến kết thúc: ${dateText(item.latest.close_time)}`}
                  {item.latest.provisional && " · Tạm thời, nến chưa đóng"}</small>
              </li>)}
            </ul>
            <p className="data-caption">{data.market.toUpperCase()} · {sources[data.source]} · {data.eligible_candles}/{data.input_candles} nến <span>Cập nhật: {dateText(data.fetched_at)}</span></p>
          </div>}
        </>}
      <p className="field-hint indicator-note">Nếu chỉ so sánh giá với một số, hiển thị SMA(20), EMA(14) và RSI(14).</p>
    </section>
  );
}
