import { useEffect, useRef, useState } from "react";
import Icon from "./Icon.jsx";

export default function TradingViewWidget({ symbol = "BTCUSDT", interval = "1d", theme = "dark" }) {
  const containerRef = useRef(null);
  const [status, setStatus] = useState("loading");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!containerRef.current) return;
    const container = containerRef.current;
    let active = true;
    setStatus("loading");
    const timer = setTimeout(() => { if (active) setStatus("error"); }, 12000);
    const observedFrames = new Set();
    const onReady = () => {
      if (active) { clearTimeout(timer); setStatus("ready"); }
    };
    const observer = new MutationObserver(() => {
      for (const frame of container.querySelectorAll("iframe")) {
        if (!observedFrames.has(frame)) {
          observedFrames.add(frame);
          frame.addEventListener("load", onReady);
        }
      }
    });
    observer.observe(container, { childList: true, subtree: true });

    // Làm sạch widget cũ trước khi tạo widget mới
    containerRef.current.innerHTML = "";

    const widgetContainer = document.createElement("div");
    widgetContainer.className = "tradingview-widget-container__widget";
    widgetContainer.style.height = "100%";
    widgetContainer.style.width = "100%";
    containerRef.current.appendChild(widgetContainer);

    // Chuyển đổi timeframe sang định dạng chuẩn của TradingView
    // "1h" -> "60", "1d" -> "D", "1w" -> "W"
    const tvInterval =
      interval === "1h" ? "60" : interval === "1w" ? "W" : "D";

    // Chuẩn hóa symbol về định dạng sàn Binance
    const cleanSymbol = (symbol || "BTCUSDT").toUpperCase().trim();
    const formattedSymbol = cleanSymbol.includes(":")
      ? cleanSymbol
      : `BINANCE:${cleanSymbol}`;

    const script = document.createElement("script");
    script.src =
      "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
    script.type = "text/javascript";
    script.async = true;
    script.onerror = () => { if (active) { clearTimeout(timer); setStatus("error"); } };
    script.innerHTML = JSON.stringify({
      autosize: true,
      symbol: formattedSymbol,
      interval: tvInterval,
      timezone: "Asia/Ho_Chi_Minh",
      theme,
      style: "1",
      locale: "vi_VN",
      enable_publishing: false,
      allow_symbol_change: false,
      calendar: false,
      hide_side_toolbar: false,
      studies: [
        "STD;RSI",
        "STD;SMA"
      ],
      support_host: "https://www.tradingview.com",
    });

    containerRef.current.appendChild(script);
    return () => {
      active = false;
      clearTimeout(timer);
      observer.disconnect();
      for (const frame of observedFrames) frame.removeEventListener("load", onReady);
      container.replaceChildren();
    };
  }, [symbol, interval, theme, attempt]);

  return (
    <div className="chart-wrapper">
      <div
        className="tradingview-widget-container"
        ref={containerRef}
        style={{ height: "100%", width: "100%" }}
      />
      {status !== "ready" && <div className="chart-placeholder" role="status">
        <span className="chart-placeholder-icon"><Icon name="chart" size={30} /></span>
        <strong>{status === "loading" ? "Đang tải biểu đồ…" : "Chưa tải được biểu đồ"}</strong>
        <p>{status === "loading" ? "Biểu đồ giá được cung cấp bởi TradingView." : "Kiểm tra kết nối mạng hoặc mở TradingView để xem biểu đồ."}</p>
        {status === "error" && <div className="chart-placeholder-actions"><button className="tv-link-btn" type="button" onClick={() => setAttempt(value => value + 1)}><Icon name="refresh" size={16} />Thử lại</button>
          <a className="tv-link-btn" href={`https://www.tradingview.com/chart/?symbol=BINANCE%3A${encodeURIComponent(symbol)}`} target="_blank" rel="noopener noreferrer">Mở TradingView <Icon name="arrow" size={16} /></a></div>}
      </div>}
    </div>
  );
}
