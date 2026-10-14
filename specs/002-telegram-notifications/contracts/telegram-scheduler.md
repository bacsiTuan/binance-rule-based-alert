# Hợp đồng scheduler và Telegram

## API công khai

Không thêm route. Giữ nguyên /health, /klines, /symbols, /indicators và CRUD /rules.
Không thêm secret hoặc trạng thái Telegram vào Rule response.
Health hiện kiểm tra Redis/market, không được gọi là health Telegram.

Frontend dùng API thật để tạo/bật rule. notifications và trigger_type được giữ
nguyên nhưng không dùng lọc/tần suất Telegram. Không tự sửa include_current,
cross_above/cross_below hoặc target indicator sang điều kiện mới.
Theo amendment 2026-10-14, chấp nhận gt/gte/lt/lte với target số hữu hạn.
Lần đầu đúng gửi một sự kiện; giữ đúng không lặp; sai rồi đúng mới kích hoạt lại.
Với gt/gte/lt/lte, điều kiện sai tương ứng <= / < / >= / > ngưỡng.

## Lượt quét nội bộ

Input: timeframe và boundary_ms B; mục tiêu close=B-1.
Chỉ nhận 1h/1d/1w và boundary đúng UTC. Job trễ quá cửa sổ misfire bị bỏ,
không replay. Lấy rule đang bật, kiểm tra activation/generation/expiration.
Output vận hành: số scanned/skipped/triggered/accepted/failed/unknown,
mã lý do, timeframe, target_close_ms, rule_id/event_id khi cần; không secrets.

Lượt dữ liệu chỉ thành công khi tìm đúng nến mục tiêu, fetched_at>=B,
không stale/provisional, có đủ lịch sử liên tục và kết quả indicator hữu hạn.
Không dùng lần lấy dữ liệu thành công để suy ra gửi thành công.

Skip reasons tối thiểu: disabled, expired, invalid_expiration,
unsupported_condition, insufficient_history, target_not_ready, stale_data,
invalid_candles, duplicate_candle, generation_changed, state_unavailable.
Lỗi một rule/nhóm không làm ngừng các nhóm khác; Redis không ghi được thì
không gửi cho rule đó. Shutdown không tạo gửi mới.

## HTTP Telegram

POST https://api.telegram.org/bot<TOKEN>/sendMessage, JSON có chat_id và text.
Token là secret từ backend, không bao giờ in URL đã thay token.
Không parse_mode; cắt phần message tùy chọn để tổng text <=4096 ký tự,
luôn giữ các trường bắt buộc. Không dùng text người dùng như markup.

Ví dụ nội dung, không phải tin đã gửi:

    Rule #12
    Market: spot | Symbol: BTCUSDT | Timeframe: 1h
    Indicator: RSI(14)
    Value: 71.25 >= 70
    Candle: CLOSED | Timezone: UTC
    Open: 2026-10-13 02:00:00
    Close: 2026-10-13 02:59:59

Thời gian hiển thị UTC; trường nội bộ milliseconds; giữ giá trị Decimal nguyên
nghĩa khi tính/lưu, không làm tròn trước so sánh. Value hiển thị hai chữ số
thập phân (half-even), ký hiệu theo operator; ngưỡng giữ giá trị đã lưu.
Hiển thị bỏ milliseconds, không đổi thời điểm nến nội bộ.

| Phản hồi | Kết quả lưu | Retry |
|---|---|---|
| HTTP2xx, JSON ok=true, result.message_id integer hợp lệ | accepted | Không |
| Telegram JSON ok=false hợp lệ, lỗi từ chối rõ ràng | failed | Không |
| 429 | failed; đọc retry_after hữu hạn nếu hợp lệ | Không |
| Timeout/transport, HTTP5xx, response/JSON/ack bất thường | unknown | Không |
| Rule tắt/xóa/đổi generation trước HTTP | cancelled | Không |

Success là Telegram chấp nhận, không bảo đảm người nhận đã đọc.
Test gửi thủ công chỉ pass với accepted/message_id hợp lệ; tin gắn nhãn kiểm thử.
Mock kiểm tra failed/unknown làm test gửi đó thất bại; không tự bật test live.
5xx/timeout không chứng minh tin chưa được gửi. retry_after chỉ điều tiết
sự kiện mới; không hồi sinh sự kiện đã failed/unknown.
Client dùng một lần http.post, không transport retry hoặc wrapper retry.
Mỗi event giữ reservation Redis trước request; kết quả không xác định giữ nguyên.

## Cấu hình và deployment

| Biến | Giá trị mặc định / quy tắc |
|---|---|
| TELEGRAM_ENABLED | false |
| TELEGRAM_BOT_TOKEN | Không có mặc định; SecretStr, không log |
| TELEGRAM_CHAT_ID | Không có mặc định; một chat mỗi môi trường |
| TELEGRAM_TIMEOUT_SECONDS | 10, lớn hơn 0 và tối đa 60 |
| RUN_TELEGRAM_LIVE_TESTS | Không bật; chỉ gate test thủ công |

Redis/cache/Binance settings cũ không đổi. Compose truyền các biến Telegram
chỉ vào backend. Watcher không khởi động nếu disabled/thiếu credentials;
API cũ vẫn phục vụ. Không hiển thị secrets bằng docker compose config.

Một API process và một replica được bật watcher. --workers >1 và --reload
không thuộc topology hỗ trợ. Không thêm service worker hoặc distributed lock.
Đổi bot/chat không replay event cũ. Logs chỉ chứa mã lỗi đã sanitize.
