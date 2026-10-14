# Mô hình dữ liệu Telegram

Mô hình nội bộ đã triển khai, cập nhật amendment 2026-10-14. Không thay schema public Rule.
Tham chiếu [spec.md](spec.md) và [hợp đồng](contracts/telegram-scheduler.md).

## Rule và điều kiện hợp lệ

Tái sử dụng id, enabled, symbol, timeframe, indicator.type/length, operator,
target, candle_mode, expiration, message, notifications, trigger_type.

- enabled=true; timeframe 1h/1d/1w; SMA/EMA/RSI; period nguyên 1..999.
- operator thuộc gt/gte/lt/lte; target số hữu hạn, không boolean hoặc TargetIndicator;
  candle_mode=closed. Indicator/period thiếu hoặc không hỗ trợ: skip có lý do.
- Giá trị so sánh dùng Decimal từ chuỗi output indicator và Decimal(str(target)).
  Target hiện là float/int: không thể lấy lại chữ số đã mất trước khi lưu.
  Không đổi API target sang string trong feature này.
- Expiration null là không hết hạn; giá trị khác phải ISO8601 có timezone.
  Không hợp lệ hoặc đã hết hạn: skip; không suy diễn timezone địa phương.
- Market và origin_hash từ Settings, không tự gắn market tùy ý vào Rule.

## Metadata theo dõi

Hash Redis đề xuất `app:rules:telegram_meta`, field rule_id, JSON:

| Trường | Ý nghĩa |
|---|---|
| schema_version | 1 |
| generation | UUID của lần theo dõi |
| activated_at_ms | UTC ms khi tạo/bật/sửa điều kiện |
| condition_fingerprint | Hash canonical các trường điều kiện |
| provisioned_namespaces | Market/host đã khởi tạo state |

Create và thay enabled/điều kiện tạo generation mới trong cùng transaction
với rule. PATCH không đổi giá trị không reset. Sửa message, notifications,
trigger_type hoặc expiration không reset; expiration được kiểm tra lại mỗi lần.
Tắt/bật hai lần vẫn để lại generation mới dù trạng thái cuối giống ban đầu.
Delete xóa metadata và state liên quan.

Bootstrap rule cũ chưa có metadata trước khi scheduler bắt đầu; lấy thời điểm
bootstrap làm activated_at. Chỉ xử lý mốc B > activated_at_ms.
Thay đổi rule qua ghi Redis ngoài CRUD không được hỗ trợ.

## Trạng thái bền vững

Hash `telegram:{market}:{origin_hash}:state`, field rule_id, không TTL.
Không dùng key cache có TTL cho trạng thái nghiệp vụ.

| Trường | Ý nghĩa |
|---|---|
| schema_version | 1 |
| rule_id, generation | Liên kết đúng lần theo dõi |
| condition | unknown / below / latched |
| last_processed_close_ms | Nến hợp lệ gần nhất; null lúc mới |
| last_value | Chuỗi Decimal, null lúc mới |
| last_event | Sự kiện gần nhất hoặc null |
| updated_at_ms | UTC ms |

Generation mới khởi tạo unknown ở mốc phù hợp; không carry latch cũ.
Namespace mới được provision một lần. Namespace đã provision nhưng state mất/hỏng:
fail closed, log state_unavailable, không tự reset để tránh gửi lại. Người vận hành
khôi phục Redis hoặc chủ động tắt/bật để tạo lần theo dõi mới.
Nếu mất cả metadata lẫn state, không còn khả năng chứng minh lịch sử; đây là
mất dữ liệu, không phải restart thông thường. AOF/volume không bảo đảm mọi write
sống sót trước sự cố máy; không hứa chống trùng tuyệt đối trong tình huống này.

## Observation (không cần lưu riêng)

rule_id/generation, market/origin, symbol/timeframe, indicator/period,
value chuỗi Decimal, threshold chuỗi Decimal, open_time/close_time UTC ms,
fetched_at ISO UTC, provisional=false, stale=false.
Chỉ tạo observation khi snapshot và indicator đủ hợp lệ.

## Chuyển trạng thái

| Trước | Quan sát | Sau | Sự kiện |
|---|---|---|---|
| unknown/below | điều kiện đúng | latched | Một sự kiện mới |
| latched | điều kiện đúng | latched | Không |
| bất kỳ | điều kiện sai, dữ liệu hợp lệ | below | Không |
| bất kỳ | lỗi/thiếu/stale | giữ nguyên | Không |
| bất kỳ | nến <= last_processed | giữ nguyên | Không |

Cùng transaction ghi condition, last_processed, last_value và reservation
nếu có sự kiện. Không đặt last_processed cho dữ liệu sai.
Nến lịch sử dùng tính chỉ báo không phải observation để rearm hoặc gửi bù.

below là tên legacy, nay nghĩa điều kiện sai; không migrate schema/state cũ.
Rearm gt/gte/lt/lte lần lượt khi <= / < / >= / > ngưỡng. Giữ mọi value/threshold
Decimal đầy đủ trong state; làm tròn Value hai chữ số và format thời gian UTC
yyyy-mm-dd HH:MM:SS chỉ tại adapter thông báo, không đổi timestamp milliseconds.

## Sự kiện và kết quả gửi

last_event là object bounded, không tạo event log/outbox vô hạn:

| Trường | Ý nghĩa |
|---|---|
| event_id | Hash market/host/rule_id/generation/close_ms |
| candle_open_ms, candle_close_ms | Nến gây kích hoạt |
| value, threshold | Chuỗi Decimal tại kích hoạt |
| reserved_at_ms | Ghi trước HTTP |
| delivery_status | attempt_reserved / accepted / failed / unknown / cancelled |
| completed_at_ms | UTC ms hoặc null |
| message_id | Chỉ khi Telegram xác nhận |
| error_code | Mã an toàn; không raw URL/token/body |

attempt_reserved không có nghĩa đã thử HTTP hay đã giao tin. Sau crash, coi
reservation chưa hoàn tất là unknown, không gửi lại. cancelled dùng khi rule
không còn được phép gửi tại lần kiểm tra cuối. Trạng thái failed/unknown không
đổi latched thành below. Khi xuất hiện sự kiện mới hợp lệ, thay last_event cũ;
đây không phải dashboard lịch sử.

CAS kiểm tra generation, last_processed và rule còn hợp lệ; retry transaction
tối đa ba lần, không side effect HTTP trong transaction. Kết quả HTTP chỉ cập nhật
nếu generation/event_id còn khớp; không ghi đè state mới sau người dùng sửa rule.
