// Các lựa chọn của form. Giá trị `value` phải khớp schema backend (mục 5.3 của plan).

export const TIMEFRAMES = [
  { value: "1h", label: "1 giờ (1h)" },
  { value: "1d", label: "1 ngày (1D)" },
  { value: "1w", label: "1 tuần (1W)" },
];

// Chỉ báo vế trái: chỉ gồm RSI, EMA, SMA
export const LEFT_INDICATORS = [
  { value: "rsi", label: "RSI – Sức mạnh tương đối", hasLength: true, defaultLength: 14 },
  { value: "ema", label: "EMA – Trung bình động mũ", hasLength: true, defaultLength: 12 },
  { value: "sma", label: "SMA – Trung bình động đơn giản", hasLength: true, defaultLength: 50 },
];

export const TARGET_INDICATORS = LEFT_INDICATORS;

// Vế giữa: giữ lại 4 toán tử so sánh đầu tiên, 2 cái cắt ở cuối vô hiệu hóa (disable)
export const OPERATORS = [
  { value: "gt", label: "Lớn hơn (more than / >)", hint: "Đúng ở MỌI nến mà A > B (trạng thái)" },
  { value: "gte", label: "Lớn hơn hoặc bằng (more than or equal / >=)", hint: "Đúng ở MỌI nến mà A >= B (trạng thái)" },
  { value: "lt", label: "Nhỏ hơn (less than / <)", hint: "Đúng ở MỌI nến mà A < B (trạng thái)" },
  { value: "lte", label: "Nhỏ hơn hoặc bằng (less than or equal / <=)", hint: "Đúng ở MỌI nến mà A <= B (trạng thái)" },
  { value: "cross_above", label: "Cắt lên (crossup / crossing up)", hint: "Chỉ đúng ở nến A vừa vượt lên B (sự kiện)", disabled: true },
  { value: "cross_below", label: "Cắt xuống (crossdown / crossing down)", hint: "Chỉ đúng ở nến A vừa rơi xuống dưới B (sự kiện)", disabled: true },
];

export const TRIGGER_TYPES = [
  { value: "once_per_bar_close", label: "Mỗi khi đóng nến (Once per bar close)", hint: "Kích hoạt khi nến đóng thỏa điều kiện" },
  { value: "once", label: "Chỉ một lần (Once only)", hint: "Kích hoạt một lần duy nhất rồi tắt" },
  { value: "every_time", label: "Mọi lúc (Every time)", hint: "Kích hoạt mỗi khi thỏa điều kiện" },
];

export const CANDLE_MODES = [
  { value: "closed", label: "Chỉ nến đã đóng", hint: "Ổn định, tín hiệu không biến mất" },
  { value: "include_current", label: "Gồm nến hiện tại", hint: "Nhanh hơn nhưng tín hiệu có thể xuất hiện rồi mất" },
];

// Giới hạn length: backend cache ~300 nến mỗi key, cần length + 1 nến trở lên.
export const MAX_LENGTH = 250;

// Các mẫu cảnh báo theo chuẩn Indicator - operator - value với RSI, EMA, SMA
export const TEMPLATES = [
  { id: "t1", name: "RSI(14) nhỏ hơn 30 – Hồi phục quá bán", left: { type: "rsi", length: 14 }, operator: "lt", target: { mode: "value", value: 30 } },
  { id: "t2", name: "RSI(14) lớn hơn 70 – Đảo chiều quá mua", left: { type: "rsi", length: 14 }, operator: "gt", target: { mode: "value", value: 70 } },
  { id: "t3", name: "RSI(14) lớn hơn 50 – Động lượng tăng", left: { type: "rsi", length: 14 }, operator: "gt", target: { mode: "value", value: 50 } },
  { id: "t4", name: "RSI(14) nhỏ hơn 50 – Động lượng giảm", left: { type: "rsi", length: 14 }, operator: "lt", target: { mode: "value", value: 50 } },
  { id: "t5", name: "EMA(12) lớn hơn 60000 – Ngưỡng xu hướng tăng", left: { type: "ema", length: 12 }, operator: "gt", target: { mode: "value", value: 60000 } },
  { id: "t6", name: "EMA(12) nhỏ hơn 50000 – Ngưỡng xu hướng giảm", left: { type: "ema", length: 12 }, operator: "lt", target: { mode: "value", value: 50000 } },
  { id: "t7", name: "SMA(50) lớn hơn 60000 – Ngưỡng hỗ trợ SMA", left: { type: "sma", length: 50 }, operator: "gt", target: { mode: "value", value: 60000 } },
  { id: "t8", name: "SMA(50) nhỏ hơn 50000 – Ngưỡng kháng cự SMA", left: { type: "sma", length: 50 }, operator: "lt", target: { mode: "value", value: 50000 } },
  { id: "t9", name: "SMA(200) lớn hơn 55000 – Xu hướng dài hạn tăng", left: { type: "sma", length: 200 }, operator: "gt", target: { mode: "value", value: 55000 } },
  { id: "t10", name: "EMA(26) nhỏ hơn 55000 – Xu hướng trung hạn giảm", left: { type: "ema", length: 26 }, operator: "lt", target: { mode: "value", value: 55000 } },
];
