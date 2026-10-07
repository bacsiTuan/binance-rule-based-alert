// Dữ liệu giả dùng khi VITE_USE_MOCK=true (chưa cần backend).

export const MOCK_SYMBOLS = [
  "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT",
  "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "TRXUSDT", "MATICUSDT",
  "LTCUSDT", "ATOMUSDT", "NEARUSDT", "UNIUSDT",
];

export const MOCK_RULES = [
  {
    id: 1,
    symbol: "BTCUSDT",
    timeframe: "1d",
    indicator: { type: "rsi", length: 14 },
    operator: "cross_above",
    target: 30,
    candle_mode: "closed",
    enabled: true,
    created_at: "2026-10-01T08:00:00Z",
  },
  {
    id: 2,
    symbol: "ETHUSDT",
    timeframe: "1d",
    indicator: { type: "sma", length: 50 },
    operator: "cross_above",
    target: { type: "sma", length: 200 },
    candle_mode: "closed",
    enabled: false,
    created_at: "2026-10-02T09:30:00Z",
  },
];
