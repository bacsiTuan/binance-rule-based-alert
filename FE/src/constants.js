// Các lựa chọn của form. Giá trị `value` phải khớp schema backend (mục 5.3 của plan).

export const TIMEFRAMES = [
  { value: "1h", label: "1 giờ (1h)" },
  { value: "1d", label: "1 ngày (1D)" },
  { value: "1w", label: "1 tuần (1W)" },
];

// Vế trái được thêm "close" để tạo luật như "Giá cắt lên SMA(20)".
export const LEFT_INDICATORS = [
  { value: "close", label: "Giá đóng cửa (Close)", hasLength: false },
  { value: "sma", label: "SMA – Trung bình động đơn giản", hasLength: true, defaultLength: 50 },
  { value: "ema", label: "EMA – Trung bình động mũ", hasLength: true, defaultLength: 12 },
  { value: "rsi", label: "RSI – Sức mạnh tương đối", hasLength: true, defaultLength: 14 },
];

export const TARGET_INDICATORS = LEFT_INDICATORS.filter((i) => i.value !== "close");

export const OPERATORS = [
  { value: "gt", label: "Lớn hơn (above)", hint: "Đúng ở MỌI nến mà A > B (trạng thái)" },
  { value: "lt", label: "Nhỏ hơn (below)", hint: "Đúng ở MỌI nến mà A < B (trạng thái)" },
  { value: "cross_above", label: "Cắt lên (cross above)", hint: "Chỉ đúng ở nến A vừa vượt lên B (sự kiện)" },
  { value: "cross_below", label: "Cắt xuống (cross below)", hint: "Chỉ đúng ở nến A vừa rơi xuống dưới B (sự kiện)" },
];

export const CANDLE_MODES = [
  { value: "closed", label: "Chỉ nến đã đóng", hint: "Ổn định, tín hiệu không biến mất" },
  { value: "include_current", label: "Gồm nến hiện tại", hint: "Nhanh hơn nhưng tín hiệu có thể xuất hiện rồi mất" },
];

// Giới hạn length: backend cache ~300 nến mỗi key, cần length + 1 nến trở lên.
export const MAX_LENGTH = 250;

// 10 luật mẫu ở mục 5.4 của plan. Điền sẵn vào form để người dùng chọn nhanh.
export const TEMPLATES = [
  { id: "t1", name: "RSI(14) cắt lên 30 – Hồi phục quá bán", left: { type: "rsi", length: 14 }, operator: "cross_above", target: { mode: "value", value: 30 } },
  { id: "t2", name: "RSI(14) cắt xuống 70 – Đảo chiều quá mua", left: { type: "rsi", length: 14 }, operator: "cross_below", target: { mode: "value", value: 70 } },
  { id: "t3", name: "RSI(14) cắt lên 50 – Động lượng tăng", left: { type: "rsi", length: 14 }, operator: "cross_above", target: { mode: "value", value: 50 } },
  { id: "t4", name: "RSI(14) cắt xuống 50 – Động lượng giảm", left: { type: "rsi", length: 14 }, operator: "cross_below", target: { mode: "value", value: 50 } },
  { id: "t5", name: "Giá cắt lên SMA(200) – Vào xu hướng tăng", left: { type: "close", length: "" }, operator: "cross_above", target: { mode: "indicator", type: "sma", length: 200 } },
  { id: "t6", name: "Giá cắt xuống SMA(200) – Vào xu hướng giảm", left: { type: "close", length: "" }, operator: "cross_below", target: { mode: "indicator", type: "sma", length: 200 } },
  { id: "t7", name: "SMA(50) cắt lên SMA(200) – Golden cross", left: { type: "sma", length: 50 }, operator: "cross_above", target: { mode: "indicator", type: "sma", length: 200 } },
  { id: "t8", name: "SMA(50) cắt xuống SMA(200) – Death cross", left: { type: "sma", length: 50 }, operator: "cross_below", target: { mode: "indicator", type: "sma", length: 200 } },
  { id: "t9", name: "EMA(12) cắt lên EMA(26) – Xu hướng đổi lên", left: { type: "ema", length: 12 }, operator: "cross_above", target: { mode: "indicator", type: "ema", length: 26 } },
  { id: "t10", name: "Giá cắt lên SMA(20) – Xu hướng ngắn hạn", left: { type: "close", length: "" }, operator: "cross_above", target: { mode: "indicator", type: "sma", length: 20 } },
];
