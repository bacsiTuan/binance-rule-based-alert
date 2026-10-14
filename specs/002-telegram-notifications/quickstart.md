# Kiểm chứng sau triển khai

Đã implement 29 task cơ sở; T030-T032 bổ sung kiểm chứng và đồng bộ amendment.
Snapshot cơ sở ngày 2026-10-14: 285 test passed, 5 skipped với live flags=0.
Sau T030-T032 ngày 2026-10-14: **305 passed, 5 skipped**, cả hai live flags=0.
43 test tập trung dispatch/E2E/live gate đạt; lint các file sửa đạt.
Không gọi Telegram thật. Lint phần mới đạt; lint toàn backend còn 5 lỗi có sẵn
trong BE/app/rules.py (PLR1730, BLE001 hai chỗ, UP017, RUF019).
Đã đối chiếu 5 lỗi lint này với bản HEAD trước thay đổi; không có lỗi lint mới.
`git diff --check` và `docker compose --env-file .env.example config --quiet` đạt.
Không chạy container/backend thật hoặc sửa `.env` cá nhân. Không sửa FE nên không
chạy FE build. Mặc định trong cấu hình mẫu/Compose vẫn là watcher tắt.

## Điều kiện

Chạy từ gốc repo chứa BE/, FE/ và compose.yaml.
Python >=3.11, môi trường dependency backend đã được cập nhật theo manifest/lockfile,
Redis có AOF/volume, Node/npm khi cần kiểm tra FE.
Đồng bộ giờ host; giữ nguyên market/host khi kiểm tra restart.

## 1. Kiểm thử không gửi thật

Gate live test đã được sửa: thiếu RUN_TELEGRAM_LIVE_TESTS=1 luôn skip,
kể cả .env chứa token/chat. OpenAI live cũng cần RUN_OPENAI_LIVE_TESTS=1 riêng.
Mock test không đọc .env cá nhân, dùng fakeredis và MockTransport.

Lệnh đã chạy từ gốc repo (dùng Python trong .venv):

    RUN_TELEGRAM_LIVE_TESTS=0 RUN_OPENAI_LIVE_TESTS=0 python -m pytest BE/tests -q
    python -m ruff check --config BE/pyproject.toml BE/app BE/tests

Bộ test phải có fake clock, không cần chờ một giờ/ngày/tuần và không gọi
Binance/Redis/Telegram thật. Đối chiếu các ca trong [plan.md](plan.md).

## 2. Chuẩn bị môi trường thủ công

Mặc định TELEGRAM_ENABLED=false. Chỉ bật true khi chủ động nghiệm thu gửi thật.
Điền token/chat vào .env backend cá nhân, không vào FE hoặc command line/history.
Compose đã truyền TELEGRAM_ENABLED, TELEGRAM_BOT_TOKEN,
TELEGRAM_CHAT_ID, TELEGRAM_TIMEOUT_SECONDS; không in giá trị đã resolve.

Chỉ chạy một bản backend, không chạy đồng thời local API và Compose API có watcher.
Chỉ khi chủ động cho phép nghiệm thu thật, có thể chạy Compose:

    docker compose up --build -d redis api

Không scale api, không uvicorn --reload hoặc nhiều worker.
Redis persistence cần giữ xuyên restart; không dùng down -v khi nghiệm thu state.
Không cần thêm endpoint/UI gửi thử.

## 3. Tạo rule backend

FE đặt VITE_USE_MOCK=false trong cấu hình frontend và khởi động lại Vite.
Tạo rule SMA/EMA/RSI, period hợp lệ, gt/gte/lt/lte, ngưỡng số, candle_mode=closed,
timeframe 1h/1d/1w và bật. Xác nhận rule tồn tại tại GET /rules.
Rule mock/localStorage không được tự nhập vào backend.

Không cần chọn thêm kênh Telegram. trigger_type trong UI không quyết định
chống lặp Telegram; không đổi nó để mong nhận nhắc lại mỗi nến.

## 4. Kịch bản mock bắt buộc

Bảng chuỗi 70 dưới đây minh họa gte. Với gt/gte/lt/lte, rearm tương ứng khi
<= / < / >= / > ngưỡng. Tất cả chỉ gửi lần đầu điều kiện đúng, không lặp khi còn đúng.
Value hiển thị hai chữ số với ký hiệu rule (ví dụ 51.66 >= 40), không Threshold;
Open/Close yyyy-mm-dd HH:MM:SS UTC. So sánh/lưu vẫn Decimal đầy đủ và UTC ms.

| Kịch bản | Kết quả |
|---|---|
| Ngưỡng70, chuỗi68/70/75/69/71 | Hai sự kiện, hai attempts khi không bị hủy |
| Khởi đầu75/75/80 | Một sự kiện |
| Mất dữ liệu sau latch rồi75 | Không gửi lại |
| Restart sau latch rồi75 | Không gửi lại |
| Tắt/bật hoặc sửa điều kiện rồi75 ở nến sau | Sự kiện của generation mới |
| Sửa message/notifications/trigger_type | Không reset |
| include_current/cross_above/target indicator | Skip, dữ liệu rule giữ nguyên |
| Job lặp cùng nến, cache cũ hoặc nến mở | Không sinh cảnh báo sai |
| Timeout/429/5xx/crash sau reserve | Không retry; giữ đúng failed/unknown |
| Tắt/xóa khi đang chờ gửi | Không bắt đầu HTTP mới |

Thử cả 1h/1d/1w, nến đóng đồng thời, UTC/Vietnam, period999,
mất Redis, token sentinel và credentials tồn tại nhưng live flag tắt.

## 5. Nghiệm thu thật tùy chọn

Chỉ thực hiện khi người vận hành chủ động cho phép gửi vào chat đã cấu hình.
Chờ lần đóng nến tiếp theo: ngày/tuần lúc 07:00 giờ Việt Nam
(ngày tương ứng/Thứ Hai), giờ tại đầu giờ; job chờ thêm khoảng 5 giây.
Nếu dữ liệu chưa có, adapter chờ lại có giới hạn; không bảo đảm Telegram đến
sau đúng 5 giây. Không sửa giờ hệ thống để ép job trong môi trường thật.

Quan sát log rule_id/event_id/candle và accepted. Kiểm tra tin có đủ market,
symbol, timeframe, indicator/period, giá trị/ngưỡng, thời gian UTC và CLOSED.
Không dùng live test đơn lẻ làm bằng chứng scheduler hoạt động.

Chỉ khi chủ động muốn chạy test live riêng sau triển khai:

    RUN_TELEGRAM_LIVE_TESTS=1 python -m pytest BE/tests/test_telegram_client_live.py -q

Lệnh này có thể gửi tin thật; không chạy trong CI/bộ test thường.
Tin có nhãn [KIỂM THỬ]; test chỉ pass khi accepted và message_id hợp lệ.
Mock rejected/timeout/ack thiếu kiểm chứng test không báo thành công giả.
Giữ secrets trong môi trường, không thêm token vào lệnh.
Nếu token từng được chia sẻ trong chat/log, thu hồi và tạo token mới trước khi
cấu hình. Bộ test dùng token giả; không sử dụng credentials người dùng cung cấp.

## Bằng chứng nghiệm thu mock

- test_telegram_schedule.py: lịch giờ/ngày/tuần, đồng thời, activation, misfire,
  ba readiness attempts và deadline hủy fetch bị treo.
- test_closed_klines.py: Spot/Futures, endTime, 1000 nến, cache lỗi/stale/thiếu nến,
  thứ tự/gap/nến mở, cooldown và không stale fallback cho scheduler.
- test_telegram_state_models.py, test_rules_telegram_metadata.py,
  test_telegram_state_storage.py: schema/Decimal, generation, CRUD atomic,
  CAS bounded/concurrent, không có TTL nghiệp vụ, lỗi Redis chặn gửi.
- test_telegram_evaluation.py, test_telegram_deduplication.py,
  test_telegram_recovery.py: >=, RSI999, period/symbol, hai chuỗi ngưỡng,
  lỗi dữ liệu không rearm, restart và state mất/hỏng không gửi lại.
- test_telegram_client.py, test_telegram_security.py, test_telegram_live_gate.py:
  acknowledgment, không retry, timeout/429/5xx/JSON lỗi, redaction DEBUG và opt-in.
- test_telegram_lifecycle.py: shutdown đang HTTP/cooldown, mutate trước gửi,
  lỗi nhóm/rule độc lập, cấu hình thiếu, Redis lỗi sau acknowledgment không retry.
- test_telegram_notifications_e2e.py: HTTP CRUD qua FastAPI lifespan với fakeredis
  và MockTransport, ba khung đóng đồng thời, Spot/Futures, restart/timeout,
  số event/attempt/accepted riêng biệt; không gọi Refresh để kích hoạt.

## Giới hạn vận hành

### Trạng thái nghiệm thu sau amendment 2026-10-14

Người dùng đã cung cấp ví dụ tin Rule #6 của bản format cũ. Đây là bằng chứng
một tin được quan sát, không phải nghiệm thu toàn bộ lịch hoặc bản code mới.
Không tự gửi tin, build/restart container trong T030-T032. Container đang chạy
có thể còn bản cũ; kiểm tra deployment thực tế cần sự cho phép riêng.

Test dispatch mới sử dụng cron/job store/AsyncIOExecutor thật, thay đồng hồ
scheduler/executor và timer wakeup bằng test fixture. E2E HTTP CRUD/lifespan
được đánh thức qua scheduler, không gọi scan trực tiếp; đếm riêng event,
attempt và accepted. Có mốc giờ/ngày/tuần/năm, startup grace, misfire và max_instances.
Đây vẫn là mock, không chứng minh đồng hồ host, mạng thật hoặc Redis durability thực tế.

Không replay nến bị bỏ lỡ, không retry Telegram và không cam kết exactly-once.
Một bot/chat, một watcher; số lượng rule lớn có thể chậm hoặc bỏ mốc job.
Giữ Redis metadata/state không TTL; mất state cần khôi phục hoặc chủ động
tắt/bật rule, không lặng lẽ coi là lần quan sát đầu.
Ngưỡng đã lưu float không khôi phục được chữ số gốc. Không có dashboard lịch sử.
