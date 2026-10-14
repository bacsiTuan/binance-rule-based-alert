# Kế hoạch: Cảnh báo Telegram theo lịch đóng nến

**Nhánh**: `feat/telegram-notifications` | **Cập nhật**: 2026-10-14
**Đặc tả**: [spec.md](spec.md)
**Trạng thái**: Đã triển khai; nghiệm thu mock tách biệt nghiệm thu live. Người dùng đã cung cấp ví dụ một tin, chưa chứng minh đầy đủ lịch và bản format mới.
Kết quả thực tế: [tasks.md](tasks.md), [quickstart.md](quickstart.md).
Phần bối cảnh dưới đây ghi nhận hiện trạng tại thời điểm lập kế hoạch.

## Tóm tắt

Bổ sung scheduler trong vòng đời FastAPI, quét rule backend sau đóng nến
1h/1d/1w. Tái sử dụng dữ liệu Binance và SMA/EMA/RSI; chỉ xử lý rule bật,
`gt/gte/lt/lte`, ngưỡng số hữu hạn, `candle_mode=closed`. Redis giữ thế hệ theo dõi,
trạng thái điều kiện và kết quả gửi. Mỗi sự kiện tối đa một lần thử gửi;
không gửi bù hoặc retry Telegram. Không phụ thuộc Refresh hay frontend.

## Bối cảnh kỹ thuật khi lập kế hoạch

- Python >=3.11, FastAPI, httpx, redis, pydantic-settings; React 18/Vite.
- Đã có: CRUD rules Redis, tính chỉ báo Decimal, cache market data,
  TelegramClient cơ bản; chưa có scheduler và đánh giá điều kiện tự động.
- FE đã gọi CRUD backend khi không mock; `VITE_USE_MOCK=true` mới dùng mock.
  Rules trong localStorage không tự chuyển thành rules backend.
- TelegramClient hiện chưa kiểm tra đầy đủ acknowledgment và lỗi có thể giữ
  request chứa token. Live test hiện chỉ kiểm tra credentials, chưa có opt-in.
- Thêm duy nhất `APScheduler>=3.11,<4` để dùng cron UTC/AsyncIOScheduler;
  chốt phiên bản trong lockfile khi triển khai. Không thêm indicator library,
  database, queue, outbox hoặc worker service.
- Một API process, một scheduler; Redis AOF/volume giữ trạng thái.
  Không hỗ trợ nhiều worker/replica có watcher cùng hoạt động.

## Kiểm tra hiến chương trước thiết kế

| Nguyên tắc | Kết luận |
|---|---|
| Hợp đồng API | Giữ routes, schema và mã lỗi market/indicators/rules; không thêm endpoint |
| Thời gian/giá | UTC milliseconds cho nến; fetched_at UTC ISO; Decimal; tách market/host |
| Cache | Giữ nguyên key/TTL/stale API; adapter nến đóng dùng key nội bộ riêng |
| Kiến trúc | Tái sử dụng service và lifecycle; dependency scheduler có lý do tại research |
| Kiểm thử | Mock HTTP/Redis/clock; live phải opt-in, không gửi trong bước plan |

Hiến chương phần hiện trạng còn mô tả CRUD/indicators là tương lai và đường dẫn
service cũ. Code thực tế đã có các phần này. Ghi nhận lệch tài liệu để bảo trì
cập nhật có review; không thay nguyên tắc hoặc suy ra quyền mở rộng SQL.

## Thiết kế lịch và dữ liệu

Gọi B là thời điểm mở nến kế tiếp (UTC); nến mục tiêu kết thúc tại B-1 ms.

| Khung | Mốc B | Thời điểm job đề xuất |
|---|---|---|
| 1h | Đầu mỗi giờ UTC | B + 5 giây |
| 1d | 00:00 UTC mỗi ngày | B + 5 giây |
| 1w | Thứ Hai 00:00 UTC | B + 5 giây |

Đây là độ trễ chờ dữ liệu, không phải SLA gửi tin. Host phải đồng bộ giờ.
Kiểm tra timestamp nến nguồn đúng ranh giới, không mặc định response đã đúng lịch.

- AsyncIOScheduler dùng MemoryJobStore, timezone UTC, ba cron job có ID cố định,
  max_instances=1, coalesce=true, misfire_grace_time=30 giây.
- Khi startup chỉ đăng ký mốc B nằm sau thời điểm startup. Không chạy ngay,
  không chạy bù job cũ; callback trễ quá 30 giây so với B+5 bị bỏ.
- Trong callback xác định duy nhất B, không dùng vòng lặp replay các mốc đã qua.
  Gom rule theo market/host/symbol/timeframe, tính nhiều period từ cùng snapshot.
- Mở rộng BinanceClient.klines bằng keyword tùy chọn end_time; lời gọi cũ không đổi.
  Adapter closed_klines truyền endTime=B-1, limit=1000, giữ endpoint theo market.
  Lấy tối đa 1000 nến đóng để RSI period=999 vẫn có đủ period+1 mẫu.
  Symbol mới có ít lịch sử thì xét đủ mẫu từng indicator, không bắt buộc đủ 1000.
- Tái sử dụng calculate_indicators, dùng cửa sổ tối đa 1000 nến kết thúc tại
  mục tiêu, nhất quán giữa các lượt. EMA/RSI có seed theo cửa sổ của hàm hiện tại;
  không cam kết giống indicator của dịch vụ ngoài dùng lịch sử vô hạn.
- Cache nội bộ thêm target_close_ms vào key. Snapshot phải có fetched_at >= B,
  không stale, đúng market/symbol/interval, thứ tự tăng và không trùng,
  lịch sử cần dùng liên tục, nến cuối đúng B-1 và toàn bộ là nến đóng.
- Cache cũ thiếu mục tiêu hoặc response chưa sẵn sàng không được đánh dấu processed.
  Tối đa ba lần thử lấy dữ liệu, sớm nhất B+5/B+15/B+30, deadline B+120 giây
  cho nhóm. Mỗi lần gọi vẫn dùng timeout/retry Binance hiện có và bị chặn bởi
  deadline chung. Lỗi mạng/rate limit kết thúc nhóm, không lặp vô hạn; cooldown
  Binance được giữ. Chờ lại chỉ dành cho nến chưa sẵn sàng.
- Dùng lại cơ chế lock/recheck cache; không thay đổi stale fallback của API cũ.
  Adapter scheduler không dùng stale để đánh giá. Không WebSocket hoặc polling
  giữa các lần đóng nến.

## Trạng thái và gửi

Chi tiết ở [data-model.md](data-model.md) và
[contracts/telegram-scheduler.md](contracts/telegram-scheduler.md).

1. CRUD lưu revision/thế hệ theo dõi trong metadata Redis nội bộ, cùng transaction
   với thay đổi rule. Tắt/bật hoặc sửa điều kiện tăng generation ngay cả nếu
   người dùng đổi đi rồi đổi lại giữa hai lượt quét.
2. Khi quét, kiểm tra rule bật, chưa hết hạn, đúng phạm vi, và B sau mốc kích hoạt.
   Chỉ quan sát hợp lệ mới cập nhật last_processed và trạng thái điều kiện.
3. Nếu kích hoạt, ghi latch, event_id và attempt_reserved trong Redis trước HTTP.
   Đây là giữ quyền thử một lần, không phải báo đã gửi. Redis lỗi thì không gửi.
4. Đọc lại rule/generation/expiration ngay trước HTTP. Nếu không còn hợp lệ thì
   đánh dấu cancelled, không gửi. Không thể thu hồi request đã ra ngoài.
5. Gửi bằng HTTP client riêng dùng trong lifespan, timeout hữu hạn, TLS bật,
   không retry transport. Chỉ acknowledgment hợp lệ mới ghi accepted.
6. Nếu crash sau reservation, restart không thử lại. Có thể mất tin nếu crash
   trước HTTP; nếu crash sau HTTP thì kết quả có thể unknown. Đây là đánh đổi
   phù hợp chính sách không retry, không phải exactly-once.
7. Lỗi dữ liệu/gửi không rearm. Chỉ quan sát làm điều kiện sai mới rearm:
   gt: <=; gte: <; lt: >=; lte: > ngưỡng. Tên state legacy below có nghĩa sai.
   Restart/reconnect giữ trạng thái và chờ mốc đóng kế tiếp, không gửi bù.

WATCH/MULTI bảo vệ so sánh generation và cập nhật trạng thái với CRUD trong
Redis; không gọi mạng trong transaction. Thử CAS tối đa ba lần rồi bỏ lượt
an toàn khi tranh chấp; không dùng distributed lock. Metadata rule và trạng
thái không có TTL; xóa khi xóa rule, thay trạng thái cũ khi đổi generation.

Dùng một asyncio lock cho gửi Telegram để ba nhóm không gửi đồng thời.
Không thêm queue bền vững; xử lý danh sách trong job. 429 kết thúc lần thử đó,
lưu retry_after để trì hoãn lần gửi sự kiện mới, không retry sự kiện cũ.
Trong lúc đợi phải kiểm tra lại rule và khả năng shutdown. Không hứa throughput
hoặc SLA; job quá lâu khiến lịch tiếp theo bị bỏ bởi max_instances, cần log.
Thiết kế dành cho số lượng rule nhỏ của prototype.

## Cấu hình, lifecycle và an toàn

- Bổ sung TELEGRAM_ENABLED=false, TELEGRAM_TIMEOUT_SECONDS=10 (0 < x <=60).
  Giữ TELEGRAM_BOT_TOKEN và TELEGRAM_CHAT_ID; token dùng SecretStr.
- Enabled nhưng thiếu token/chat: vô hiệu watcher và log mã lý do an toàn,
  API cũ vẫn chạy. Không đánh giá/latch khi chưa có cấu hình gửi.
- Thêm biến vào .env.example và compose; không commit .env hoặc in cấu hình đã
  resolve. Mỗi môi trường một bot/chat là giả định triển khai, không per-user.
- HTTP client Telegram riêng để timeout và lifecycle không ảnh hưởng Binance.
  SecretStr không đủ bảo vệ URL: filter httpx/httpcore trước khi dùng client,
  sanitize URL/token trong log; lỗi public chỉ dùng mã/description allowlist,
  không log raw response/request/exception chain.
- Không follow redirect sang host khác, không tắt verify TLS, không log token
  hoặc chat ID. Không cho frontend truy cập secrets.
- Shutdown: ngừng nhận job mới, dừng/chờ task đang chạy có giới hạn 15 giây,
  cancellation giữ reservation là unknown, đóng clients rồi Redis.
  Không coi scheduler.shutdown(wait=True) là đủ để chờ coroutine hoàn tất.
- Chạy một uvicorn worker, một replica; không --reload khi watcher bật.
  Không thể bảo đảm chống trùng nếu vận hành trái topology hoặc làm mất Redis.

## Ranh giới thay đổi dự kiến

| File/module | Trách nhiệm / yêu cầu |
|---|---|
| BE/app/service/telegram_scheduler.py (mới) | Cron/lifecycle, lấy dữ liệu, đánh giá, điều phối gửi; FR-001/013 |
| BE/app/telegram_state.py (mới) | Model nội bộ, Redis CAS/generation/attempt; FR-005/010/015 |
| BE/app/rules.py | Metadata atomic với CRUD; không đổi public Rule |
| BE/app/service/market_data.py, binance_client.py | Adapter nến mục tiêu và endTime; FR-008/013 |
| BE/app/indicators.py | Tái sử dụng, dự kiến không sửa thuật toán |
| BE/app/service/telegram_client.py, errors.py | Ack và lỗi typed an toàn; FR-009/010 |
| BE/app/config.py, main.py | Cấu hình, logger filter, startup/shutdown |
| BE/tests/ | Test mock và sửa gate live test; FR-012 |
| BE/pyproject.toml và BE/requirements.lock.txt | Dependency scheduler |
| .env.example, compose.yaml, README.md | Vận hành một watcher và giới hạn |
| FE | Chưa cần sửa; API toggle và gte đã có |

Mỗi module mới gắn yêu cầu cụ thể; không tạo framework rule engine tổng quát.
Không sửa metadata trường notifications/trigger_type để phục vụ Telegram.

## Kế hoạch kiểm chứng

- Fake clock: giờ/ngày/tuần UTC, Chủ nhật -> Thứ Hai, đổi tháng/năm,
  startup giữa nến và trong 5 giây grace, misfire, mốc nhiều khung cùng đóng.
- Mock Binance: endTime cho Spot/Futures, RSI999, thiếu lịch sử, cache trước B,
  nến mở/thiếu mục tiêu/trùng/sai thứ tự/gap/stale; deadline và cooldown.
- Chuỗi ngưỡng của SC-002, equality/Decimal; nhiều symbol/period; skip legacy.
- Fakeredis: duplicate job, restart, mutation A->B->A, off->on, xóa trước gửi,
  Redis lỗi/CAS conflict, crash trước/sau reservation và sau HTTP.
- MockTransport: accepted, ok=false, HTTP error, invalid JSON/result,
  timeout/5xx/429; mỗi event tối đa một HTTP attempt.
- Sentinel token không xuất hiện trong logs, exception hoặc response công khai;
  kiểm tra cả httpx/httpcore với logging chi tiết.
- Live test bị skip mặc định dù credentials có trong .env; mock tests dùng
  Settings(_env_file=None) và credentials giả, không mạng thật.
- Hồi quy API/CLI/TTL và CRUD; FE build chỉ bắt buộc nếu thực tế phải sửa FE.

## Kiểm tra hiến chương sau thiết kế

Các gate trước thiết kế đạt ở mức thiết kế. Bằng chứng triển khai sau đó được
ghi tại tasks.md và quickstart.md; lint có ngoại lệ lỗi cũ được đối chiếu HEAD.
Giới hạn phải công khai: Redis giữ dữ liệu là điều kiện chống lặp qua restart;
AOF không bảo đảm không mất mọi write khi máy hỏng; ngưỡng cũ đã qua float không
khôi phục được độ chính xác gốc; không hỗ trợ scale watcher ngang.
Không có ngoại lệ kiến trúc cần xin thêm; không bổ sung queue/outbox/SQL.

## Tài liệu và bước tiếp theo

- [research.md](research.md): quyết định và phương án đã cân nhắc.
- [data-model.md](data-model.md): trạng thái và tính nhất quán.
- [contracts/telegram-scheduler.md](contracts/telegram-scheduler.md): hợp đồng.
- [quickstart.md](quickstart.md): hướng dẫn kiểm chứng sau triển khai.

Phase 1 ban đầu chỉ tạo thiết kế. Sau đó đã hoàn tất tasks và implementation;
Kết quả mới nhất ghi ở quickstart/tasks; số 285 ở bằng chứng cũ là snapshot trước mở rộng.
Nghiệm thu live cần người vận hành chủ động bật.

## Amendment 2026-10-14 và convergence

Theo yêu cầu người dùng, gt/gte/lt/lte được hỗ trợ, không thêm cross operators.
Giữ lịch sử quyết định gte-only tại spec Clarifications. Decimal dùng đầy đủ khi
so sánh/lưu; message chỉ định dạng Value hai chữ số với ký hiệu operator, không
Threshold. Open/Close yyyy-mm-dd HH:MM:SS và nhãn Timezone: UTC; nội bộ vẫn UTC ms.
Không đổi schema/generation, không migrate below vì đây là nhãn điều kiện sai.

T030 kiểm tra dispatch qua cron/job store/AsyncIOExecutor thật với đồng hồ giả
ở scheduler và executor; chỉ thay timer wakeup, không gọi scan trực tiếp trong
E2E lifespan. Kiểm tra giờ/ngày/tuần/năm, startup, misfire và max_instances.
T032 giữ opt-in live, tin có nhãn kiểm thử, chỉ pass khi accepted/message_id hợp lệ;
mock rejected/timeout/ack thiếu phải làm test đó thất bại, không dùng test live
đơn lẻ làm bằng chứng scheduler. Không thay dependency hoặc runtime cho các task này.
