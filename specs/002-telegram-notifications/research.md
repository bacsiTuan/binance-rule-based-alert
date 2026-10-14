# Nghiên cứu thiết kế Telegram

Cập nhật ngày 2026-10-14. Phân biệt quyết định kỹ thuật dưới đây với nghiệp vụ đã chốt
trong [spec.md](spec.md). Không thay các câu trả lời clarification.

## 1. Lập lịch

**Quyết định:** AsyncIOScheduler của APScheduler 3.x, cron UTC, MemoryJobStore,
ba job 1h/1d/1w trong một FastAPI process. Thêm dependency >=3.11,<4 và lockfile
khi implement, không cài trong bước tài liệu.

**Lý do:** thư viện hỗ trợ asyncio, cron, misfire, coalesce và giới hạn instance.
Lịch tuyệt đối tránh drift từ thời điểm startup; không cần lưu job vì không backfill.
[User guide](https://apscheduler.readthedocs.io/en/3.x/userguide.html) và
[CronTrigger](https://apscheduler.readthedocs.io/en/3.x/modules/triggers/cron.html).

**Cân nhắc:** vòng sleep tự tính lịch ít dependency nhưng phải tự xử lý lịch,
misfire và shutdown; Celery/external scheduler thêm hạ tầng không cần thiết.
APScheduler không thay thế persisted condition state hoặc chống trùng đa replica.

## 2. Nến đóng và cache

**Quyết định:** thêm adapter nội bộ lấy tối đa 1000 nến kết thúc tại endTime=B-1,
key có target_close; kiểm tra lại exact target và fetched_at. Không dùng cache
latest hoặc stale như bằng chứng nến đã đóng.

**Lý do:** API hiện tại có thể cache nến đang chạy trong 60 giây; RSI999 cần
1000 nến đóng. Spot hỗ trợ endTime UTC; USD-M cũng có endTime.
[Binance Spot REST](https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md)
và [USD-M connector chính thức](https://github.com/binance/binance-futures-connector-python/blob/main/binance/um_futures/market.py).

**Cân nhắc:** xóa cache API ảnh hưởng client khác; chỉ bỏ nến cuối làm thiếu
mẫu và có thể chọn sai nến; WebSocket trái phạm vi. Grace 5 giây và readiness
retry có deadline là lựa chọn kỹ thuật, không lời hứa Binance luôn sẵn sàng.
Tuần căn Thứ Hai UTC; kiểm tra timestamp nguồn và test fixture, không chấp nhận
snapshot lệch ranh giới. Clock host phải được đồng bộ.

## 3. Trạng thái và thay đổi rule

**Quyết định:** metadata/generation nội bộ, atomic cùng CRUD, không đổi schema Rule.
Điều kiện và last processed giữ trong Redis không TTL, tách namespace market/host.
WATCH/MULTI bảo vệ cập nhật có điều kiện.
[Redis transactions](https://redis.io/docs/latest/develop/using-commands/transactions/).

**Lý do:** fingerprint ở thời điểm scan không nhận biết off/on hoặc A->B->A
xảy ra giữa các lượt. Redis hiện có đáp ứng lưu trạng thái qua restart.

**Cân nhắc:** state trong RAM mất khi restart; thêm SQL/Redis job queue không cần.
Giữ tối đa kết quả sự kiện gần nhất mỗi rule thay vì tạo kho lịch sử vô hạn.
Topology một process vẫn cần CAS với CRUD; CAS không phải distributed lock.

## 4. Một lần thử gửi

**Quyết định:** ghi latch và attempt_reserved trước HTTP, sau đó lưu accepted,
failed hoặc unknown. Không retry bất kỳ sự kiện nào.

**Lý do:** nếu ghi sau HTTP, crash giữa gửi và ghi có thể gửi lại sau restart.
Reservation trước HTTP có thể làm mất tin nhưng phù hợp lựa chọn ưu tiên không
thử lại. Redis mất write hoặc bị reset nằm ngoài bảo đảm; không claim exactly-once.

**Cân nhắc:** outbox/retry tăng độ giao tin nhưng trái Q3; gọi HTTP trong Redis
transaction có thể lặp side effect khi CAS retry và không được phép.

## 5. Telegram client và bí mật

**Quyết định:** HTTP client riêng, plain text, không parse_mode, timeout10s,
TLS mặc định. Thành công cần HTTP2xx, JSON ok=true và result có message_id
hợp lệ. Không log raw description hoặc exception giữ token.

Telegram trả kết quả dưới dạng ok/result; sendMessage nhận text tối đa 4096
ký tự. retry_after dùng để chờ trước sự kiện mới, không gửi lại sự kiện cũ.
[Telegram Bot API](https://core.telegram.org/bots/api#sendmessage).

**Cân nhắc:** dùng chung client Binance gắn timeout/lifecycle khác nhau;
SecretStr đơn độc không che token trong request URL của log HTTP.
Chọn error code allowlist và redaction httpx/httpcore thay vì tin raw lỗi an toàn.

## 6. FE và test

**Quyết định:** không thay FE trong kế hoạch cơ sở. App.jsx gọi createRulesApi,
toggle qua updateRule; rulesClient chọn backend khi không mock; gte đã có.
Nghiệm thu phải dùng VITE_USE_MOCK=false và kiểm tra /rules.

**Lý do:** không cần UI Telegram riêng. notifications/trigger_type không chi phối
Telegram nhưng vẫn giữ cho luồng cũ. Test live phải có RUN_TELEGRAM_LIVE_TESTS=1
ngoài credentials; test thường không phụ thuộc .env.

**Cân nhắc:** tự migrate localStorage hoặc thêm trang gửi thử vượt phạm vi.
Không chạy bộ test hiện tại trước khi sửa gate live vì có nguy cơ gửi thật.

## Kết luận nghiên cứu

Amendment 2026-10-14 theo yêu cầu người dùng: mở rộng gte thành gt/gte/lt/lte
bằng phép so sánh Decimal chuẩn, không thêm framework. Điều kiện sai rearm,
below giữ làm tên state legacy; không cần migration. Display Value hai chữ số,
Open/Close yyyy-mm-dd HH:MM:SS UTC, giữ Decimal/UTC ms trong tính toán/lưu trữ.

Convergence T030 dùng cron/executor đang cài với đồng hồ giả và wakeup chủ động,
thay vì suy ra lịch từ gọi scan trực tiếp. Không thêm thư viện test thời gian.
T032 kiểm tra DeliveryResult của test live bằng mock cả thành công/lỗi;
tin thử có nhãn riêng và accepted không có nghĩa người nhận đã đọc.
Lịch sử gte-only và định dạng đầy đủ trước amendment được giữ trong spec.

Không còn unknown kỹ thuật chặn lập tasks. Một bot/chat mỗi môi trường là
giả định đã ghi trong spec. Các giới hạn về Redis durability, throughput,
clock host và float legacy phải được giữ trong tài liệu vận hành.
