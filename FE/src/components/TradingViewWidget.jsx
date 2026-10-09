import React, { useEffect, useRef } from "react";

export default function TradingViewWidget({ symbol = "BTCUSDT", interval = "1d" }) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current) return;

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
    script.innerHTML = JSON.stringify({
      autosize: true,
      symbol: formattedSymbol,
      interval: tvInterval,
      timezone: "Asia/Ho_Chi_Minh",
      theme: "dark",
      style: "1",
      locale: "vi_VN",
      enable_publishing: false,
      allow_symbol_change: true,
      calendar: false,
      hide_side_toolbar: false,
      studies: [
        "STD;RSI",
        "STD;SMA"
      ],
      support_host: "https://www.tradingview.com",
    });

    containerRef.current.appendChild(script);
  }, [symbol, interval]);

  return (
    <div className="chart-wrapper">
      <div
        className="tradingview-widget-container"
        ref={containerRef}
        style={{ height: "100%", width: "100%" }}
      />
    </div>
  );
}
