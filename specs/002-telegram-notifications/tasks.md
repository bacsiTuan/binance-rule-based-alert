# Tasks: Cảnh báo Telegram theo lịch đóng nến

**Ngày**: 2026-10-14 | **Nhánh**: `feat/telegram-notifications`
**Trạng thái**: Hoàn tất 32/32 task gồm T030-T032; 305 test đạt, 5 bỏ qua. Chỉ kiểm chứng mock ở lượt này; nghiệm thu live toàn luồng chưa hoàn tất.
**Nguồn**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts](contracts/telegram-scheduler.md),
[quickstart.md](quickstart.md), hiến chương tại `.specify/memory/constitution.md`.

Đường dẫn bên dưới tính từ gốc repo chứa BE/ và FE/.
Mỗi task có yêu cầu FR/SC, phụ thuộc và tiêu chí đạt. [P] chỉ cho phép song song
sau khi các phụ thuộc đã xong, trên các file khác nhau.
Viết test trước implementation tương ứng; chỉ chạy test bằng mock.
Không chạy bộ test hiện tại trước khi hoàn thành T001-T002.

## Phase 1: Setup và chặn gửi thật

- [x] T001 Sửa gate trong `BE/tests/test_telegram_client_live.py`: chỉ chạy khi RUN_TELEGRAM_LIVE_TESTS=1 và đủ credentials; kiểm tra flag trước khi đọc .env cho live test. **FR-012, SC-005**. Phụ thuộc: không. Đạt: mặc định skip dù máy có token/chat; không gửi thật để xác minh gate.
- [x] T002 Viết test gate tại `BE/tests/test_telegram_live_gate.py` và fixtures tại `BE/tests/conftest.py`: dùng credentials giả, Settings(_env_file=None), MockTransport/fakeredis/fake clock, chặn transport mạng thật cho test thường; không phá opt-in live riêng. **FR-012, SC-005**. Phụ thuộc: T001. Đạt: flag thiếu/0 với credentials có sẵn tạo 0 request thật; flag1 được kiểm tra bằng transport giả, không gửi thật.
- [x] T003 Thêm APScheduler>=3.11,<4 tại `BE/pyproject.toml`, cập nhật `BE/requirements.lock.txt` theo quy trình lock hiện có. **FR-001, FR-013**. Phụ thuộc: T002. Đạt: cài/import AsyncIOScheduler từ lock thành công; không thêm queue/worker/dependency khác.

## Phase 2: Nền tảng dùng chung

- [x] T004 [P] Thêm test cấu hình tại `BE/tests/test_telegram_config.py`, rồi cập nhật `BE/app/config.py`: TELEGRAM_ENABLED=false, token SecretStr, chat backend-only, timeout mặc định10 với 0 < x <=60. **FR-009, FR-012**. Phụ thuộc: T003. Đạt: Settings cũ vẫn hợp lệ, repr không chứa token; thiếu credentials không bắt buộc API cũ ngừng chạy.
- [x] T005 [P] Khai báo model nội bộ và test serialization tại `BE/app/telegram_state.py`, `BE/tests/test_telegram_state_models.py` theo data-model: schema_version=1; generation UUID; UTC ms; condition “unknown / below / latched”; last_processed_close_ms, last_value và last_event “null lúc mới”; last_value/value/threshold là chuỗi Decimal hữu hạn; delivery_status “attempt_reserved / accepted / failed / unknown / cancelled”; completed_at_ms nullable, message_id chỉ khi xác nhận, error_code an toàn. **FR-005, FR-007, FR-010, FR-015**. Phụ thuộc: T003. Đạt: round-trip không mất Decimal, reject state sai schema/enum/thời gian; không đổi `BE/app/models.py` public Rule.
- [x] T006 Thêm test và tích hợp metadata atomic với CRUD tại `BE/tests/test_rules_telegram_metadata.py`, `BE/app/rules.py`, `BE/app/telegram_state.py`: generation mới khi create, enabled đổi hoặc điều kiện đổi; bootstrap rule cũ; delete dọn metadata/state; lưu provisioned_namespaces. **FR-006, FR-011, FR-015**. Phụ thuộc: T004-T005. Đạt: off/on và A->B->A giữa hai scan vẫn đổi generation; PATCH không đổi giá trị hoặc chỉ message/notifications/trigger_type/expiration không reset; không sửa payload legacy.
- [x] T007 Triển khai primitive Redis WATCH/MULTI trong `BE/app/telegram_state.py` và test `BE/tests/test_telegram_state_storage.py`: hash metadata app:rules:telegram_meta và state telegram:{market}:{origin_hash}:state không TTL; CAS generation/last_processed, tối đa ba lần tranh chấp, không HTTP trong transaction. **FR-005, FR-010, FR-015**. Phụ thuộc: T006. Đạt: atomic read/update/reserve/finalize; kết quả event cũ không ghi đè generation mới; namespace đã provision mà state mất/hỏng thì fail closed; Redis lỗi không cấp quyền gửi.

**Checkpoint:** test thường an toàn, cấu hình và lưu trạng thái sẵn sàng.
Không bật watcher thật ở checkpoint này.

## Phase 3: US1 - Nhận cảnh báo tự động (P1)

**Mục tiêu:** đúng rule, đúng nến đóng, đúng lịch, không cần frontend/Refresh.
**Kiểm tra độc lập:** fake clock + nguồn Binance giả + Telegram giả; rule mới
đạt ngưỡng tại lần scan hợp lệ đầu tiên tạo một tin với đủ trường bắt buộc.

### Test trước

- [x] T008 [P] [US1] Viết test lịch tại `BE/tests/test_telegram_schedule.py`: 1h/1d/1w UTC, tuần bắt đầu Thứ Hai, đổi ngày/tháng/năm, mốc ba khung trùng, bật giữa nến, startup trong grace, misfire và callback lặp. **FR-001, FR-004, FR-013, SC-004**. Phụ thuộc: T007. Đạt: chỉ nhóm đúng timeframe được gọi; mỗi B một lượt có hiệu lực; bật/startup chờ B kế tiếp, không replay.
- [x] T009 [P] [US1] Viết test adapter tại `BE/tests/test_closed_klines.py`: endTime=B-1, Spot/Futures/host, tối đa1000 nến đóng, RSI999, symbol mới, cache trước B, thiếu mục tiêu, gap/trùng/out-of-order/nến mở, stale, retry readiness/deadline/cooldown. **FR-002, FR-008, FR-011, FR-013**. Phụ thuộc: T007. Đạt: chỉ snapshot đúng mục tiêu được dùng; tối đa ba lượt readiness, không thay TTL/key/stale API hiện có.
- [x] T010 [P] [US1] Viết test đánh giá/nội dung tại `BE/tests/test_telegram_evaluation.py`: SMA/EMA/RSI, nhiều symbol/period, equality, Decimal, ngưỡng70 lần đầu75, bootstrap lịch sử không phát sự kiện quá khứ, tin plain text đủ trường. **FR-002, FR-003, FR-004, FR-007, SC-001**. Phụ thuộc: T007. Đạt: dùng đúng indicator hiện có; không làm tròn trước so sánh; một sự kiện đầu tiên, không gửi ngay khi CRUD.

### Triển khai

- [x] T011 [US1] Mở rộng keyword end_time của `BE/app/service/binance_client.py` và thêm closed_klines trong `BE/app/service/market_data.py`; tái sử dụng lock/recheck/cache, key nội bộ có target_close, fetch1000, không stale cho scheduler. **FR-002, FR-008, FR-011, FR-013**. Phụ thuộc: T009. Đạt: T009 pass; fetched_at>=B, nến cuối=B-1, lịch sử cần dùng liên tục; readiness sớm nhất B+5/+15/+30, deadline B+120, không polling giữa nến; retry Binance cũ vẫn hữu hạn.
- [x] T012 [US1] Tạo lịch và lọc rule trong `BE/app/service/telegram_scheduler.py`: ba cron UTC B+5, MemoryJobStore, ID cố định, max_instances=1, coalesce=true, misfire_grace_time=30; B>activated_at_ms. **FR-001, FR-004, FR-006, FR-013, FR-014**. Phụ thuộc: T008, T011. Đạt: T008 pass; chỉ enabled, SMA/EMA/RSI, “period nguyên 1..999”, gte, “target số hữu hạn, không boolean hoặc TargetIndicator”, closed; expiration null hoặc ISO8601 có timezone, lỗi thì skip; không dùng notifications/trigger_type làm bộ lọc.
- [x] T013 [US1] Nối grouped snapshot với `BE/app/indicators.py` từ `BE/app/service/telegram_scheduler.py`: gom market/host/symbol/timeframe, tính selections theo period, kiểm tra latest hợp lệ, so sánh Decimal >=; dùng CAS/reservation từ T007, không gửi nếu reserve lỗi. **FR-002, FR-003, FR-004, FR-007, FR-008, FR-010**. Phụ thuộc: T010, T012. Đạt: cửa sổ tối đa1000 nến đóng, đủ period/period+1; không tự triển khai công thức khác; nội dung có rule/market/symbol/timeframe/indicator/period/value/threshold/UTC/CLOSED, <=4096 ký tự, cắt phần tùy chọn trước.
- [x] T014 [US1] Nối lifecycle trong `BE/app/main.py` với `BE/app/service/telegram_scheduler.py`: một scheduler, HTTP client Telegram riêng, injected clock/client cho test, chỉ khởi động khi enabled và đủ cấu hình. **FR-001, FR-009, FR-011, FR-012**. Phụ thuộc: T013. Đạt: đóng browser không ảnh hưởng; không tạo scheduler ở route/Refresh; disabled không latch; dùng mock sender cho checkpoint US1, đường gửi thật chưa được coi sẵn sàng trước US3.

**Checkpoint US1:** test lịch/dữ liệu/đánh giá pass độc lập với Telegram giả.
Chưa nghiệm thu production: phải hoàn thiện US2 và US3.

## Phase 4: US2 - Không gửi lặp khi điều kiện còn đúng (P1)

**Mục tiêu:** một sự kiện cho mỗi giai đoạn >=; giữ qua restart/reconnect.
**Kiểm tra độc lập:** state machine + fakeredis + sender giả đếm sự kiện/attempt.

- [x] T015 [P] [US2] Viết test tại `BE/tests/test_telegram_deduplication.py`: ngưỡng70, 68->70->75->69->71 có hai sự kiện; 75->75->80 có một; equality, nến mới vẫn >= không gửi; lỗi/stale/thiếu dữ liệu giữa hai giá trị >= không reset; job trùng/out-of-order không gửi thêm. **FR-003, FR-005, FR-008, FR-013, SC-002, SC-003**. Phụ thuộc: T014. Đạt: count chính xác và last_processed không đổi do dữ liệu lỗi.
- [x] T016 [P] [US2] Viết test khôi phục tại `BE/tests/test_telegram_recovery.py`: restart cùng Redis, reconnect bỏ nến mất, off/on, sửa ngưỡng/period/timeframe, A->B->A, sửa message không reset, crash trước/sau reservation và sau HTTP, mất/hỏng state. **FR-005, FR-010, FR-015, SC-007**. Phụ thuộc: T014. Đạt: không backfill/retry; generation mới chờ B kế tiếp; không reset state chỉ vì lỗi.
- [x] T017 [US2] Hoàn thiện chuyển trạng thái và reservation trong `BE/app/telegram_state.py`, nối tại `BE/app/service/telegram_scheduler.py`: unknown/below + >= -> latched và event; < hợp lệ -> below; latched + >= giữ nguyên; nến<=last_processed hoặc invalid không tác động. **FR-004, FR-005, FR-008, FR-010, FR-013**. Phụ thuộc: T015. Đạt: T015 pass; ghi condition/last_processed/last_value/event atomic trước HTTP; event_id gắn namespace/rule/generation/nến, không đánh dấu accepted khi reserve.
- [x] T018 [US2] Hoàn thiện bootstrap/recovery trong `BE/app/telegram_state.py`, `BE/app/service/telegram_scheduler.py`: giữ latch khi restart, reservation dở là unknown không replay, chỉ nến mới đúng lịch; state mới theo generation, namespace đã provision mất state thì fail closed. **FR-010, FR-015**. Phụ thuộc: T016-T017. Đạt: T016 pass; chỉ giữ last_event gần nhất, không thêm history/outbox; lịch sử indicator không được dùng rearm các nến đã bỏ lỡ.

**Checkpoint US2:** SC-002 và restart/reconnect pass, không retry sự kiện cũ.

## Phase 5: US3 - Kiểm soát phạm vi và nhận biết lỗi (P2)

**Mục tiêu:** không gửi sai rule/dữ liệu; ghi đúng kết quả; không lộ token.
**Kiểm tra độc lập:** MockTransport + rule mutations + fake clock, kiểm tra
request count, state và captured logs, không cần dịch vụ thật.

- [x] T019 [P] [US3] Viết test hợp đồng tại `BE/tests/test_telegram_client.py`: 2xx/ok=true/message_id hợp lệ, ok=false, 429/retry_after, timeout/transport/5xx, JSON/ack hỏng, redirect và timeout hữu hạn. **FR-009, FR-010, SC-007**. Phụ thuộc: T018. Đạt: mỗi event tối đa một request; accepted/failed/unknown đúng contract, không tự transport retry, TLS không bị tắt.
- [x] T020 [P] [US3] Viết test an toàn tại `BE/tests/test_telegram_security.py`: sentinel token trong URL, HTTP logs DEBUG, raw description/body và exception chain; credentials có nhưng watcher disabled. **FR-009, FR-012, SC-005**. Phụ thuộc: T018. Đạt: token/chat không xuất hiện trong logs/exception/public output; không gọi thật.
- [x] T021 [P] [US3] Viết test vận hành tại `BE/tests/test_telegram_lifecycle.py`: rule tắt từ đầu không event; xóa/tắt/đổi generation/hết hạn khi chờ gửi; rule legacy skip giữ nguyên; thiếu credentials; Redis lỗi; shutdown khi chờ cooldown hoặc đang HTTP. **FR-006, FR-008, FR-009, FR-011, FR-014, FR-015, SC-003**. Phụ thuộc: T018. Đạt: không bắt đầu HTTP cho rule không còn hợp lệ, lỗi nhóm này không chặn nhóm khác; API cũ vẫn hoạt động khi thiếu Telegram.
- [x] T022 [US3] Hoàn thiện `BE/app/service/telegram_client.py`, `BE/app/errors.py`: lấy SecretStr chỉ khi tạo request, HTTP client không retry/redirect, validate acknowledgment, lỗi typed theo contract, không raw error/exception chain; TLS bật. **FR-009, FR-010**. Phụ thuộc: T019. Đạt: T019 pass; success không suy từ status2xx đơn thuần; 5xx/timeout/ack bất thường là unknown.
- [x] T023 [US3] Cài redaction/filter httpx/httpcore trước khi dùng client trong `BE/app/main.py`, sanitize lỗi/log tại `BE/app/service/telegram_client.py`; không log token/chat/body, chỉ allowlist mã an toàn. **FR-009, FR-012**. Phụ thuộc: T020, T022. Đạt: T020 pass kể cả DEBUG và lỗi; không dựa riêng vào SecretStr.
- [x] T024 [US3] Hoàn thiện đường gửi trong `BE/app/service/telegram_scheduler.py`: asyncio send lock chung, re-read rule/generation/expiration ngay trước HTTP, cancelled khi không hợp lệ, finalize theo event_id; 429 chỉ trì hoãn sự kiện mới bằng retry_after hữu hạn, không retry event cũ. **FR-006, FR-010, FR-014, FR-015**. Phụ thuộc: T021, T023. Đạt: failed/unknown vẫn latched, event mới chỉ sau < rồi >=; không gọi HTTP trong CAS, không queue/outbox.
- [x] T025 [US3] Hoàn thiện shutdown và lỗi độc lập nhóm tại `BE/app/main.py`, `BE/app/service/telegram_scheduler.py`: ngừng job mới, chờ/cancel coroutine tối đa15 giây, reservation dở giữ unknown, đóng HTTP rồi Redis, counters và skip reasons an toàn. **FR-001, FR-006, FR-008, FR-009, FR-010**. Phụ thuộc: T024. Đạt: T021 pass, không task nền rò sau teardown; reconnect tiếp tục mốc kế tiếp; max_instances/misfire bỏ lượt có log, không tự backfill.

**Checkpoint US3:** toàn bộ ba story có thể tích hợp; gửi thật vẫn là opt-in thủ công.

## Phase 6: Tích hợp, hồi quy và vận hành

- [x] T026 Thêm E2E mock tại `BE/tests/test_telegram_notifications_e2e.py`: FastAPI lifespan, CRUD backend, fake clock, Binance/Telegram MockTransport và fakeredis; chạy lịch 1h/1d/1w trùng mốc, các chuỗi ngưỡng, tắt/bật, lỗi gửi và restart; không gọi Refresh/indicators để kích hoạt. **FR-001 đến FR-015, SC-001 đến SC-007**. Phụ thuộc: T025. Đạt: kiểm tra đồng thời số sự kiện, HTTP attempts, ack, state và nội dung; không mạng thật hoặc chờ giờ thật.
- [x] T027 Cập nhật `.env.example`, `compose.yaml`: truyền cấu hình Telegram chỉ backend, disabled mặc định, giữ AOF/volume và một API worker/replica; không đụng secrets cá nhân. **FR-009, FR-011, FR-015**. Phụ thuộc: T026. Đạt: compose hợp lệ, không thêm worker service, không in config đã resolve chứa secret; không khởi động watcher thật để kiểm tra.
- [x] T028 Cập nhật `README.md`, `specs/002-telegram-notifications/quickstart.md`: hướng dẫn UTC/Vietnam, rule backend và VITE_USE_MOCK=false, gte/closed, notifications/trigger_type không chi phối Telegram, một worker không reload; không retry/backfill, Redis durability/float legacy/throughput, opt-in live, giới hạn credential. **FR-001, FR-009, FR-010, FR-011, FR-014, FR-015**. Phụ thuộc: T027. Đạt: lệnh khớp compose.yaml/lock thực tế, phân biệt đã triển khai và giới hạn; FE API toggle tại `FE/src/App.jsx`, `FE/src/api/rulesClient.js` được xác nhận mà không redesign.
- [x] T029 Chạy hồi quy và ghi bằng chứng vào `specs/002-telegram-notifications/quickstart.md`: RUN_TELEGRAM_LIVE_TESTS=0 python -m pytest BE/tests -q; python -m ruff check --config BE/pyproject.toml BE/app BE/tests; kiểm tra contract market/indicators/CRUD, cache TTL/stale, Decimal/UTC/Spot-Futures. **FR-011, FR-012, SC-005, SC-006**. Phụ thuộc: T028 và T001-T002 đã pass. Đạt: test mock/lint đạt hoặc ghi rõ lỗi tồn tại trước; không tuyên bố pass khi chưa chạy. Chỉ nếu FE thật sự phải sửa mới chạy npm test/npm run build trong FE; không đưa gửi live vào tiêu chí bắt buộc.

## Phụ thuộc và song song

Thứ tự chính:

    T001 -> T002 -> T003 -> (T004 || T005) -> T006 -> T007
    -> US1 (T008-T014) -> US2 (T015-T018) -> US3 (T019-T025)
    -> T026 -> T027 -> T028 -> T029

Trong US1: T008/T009/T010 song song; T009->T011;
T008+T011->T012; T010+T012->T013->T014.
Trong US2: T015/T016 song song; T015->T017; T016+T017->T018.
Trong US3: T019/T020/T021 song song; T019->T022;
T020+T022->T023; T021+T023->T024->T025.

Các test story có thể kiểm chứng riêng bằng fixtures sau nền tảng; triển khai
tích hợp vẫn tuần tự vì dùng chung scheduler/state/main. Không giao song song
các task sửa cùng file. [P] không có nghĩa bỏ qua gate của phase trước.

## Chiến lược giao từng phần

1. Setup/nền tảng trước, đặc biệt gate live.
2. US1 là MVP mô phỏng lịch -> nến -> chỉ báo -> sender giả; chưa bật gửi thật.
3. US2 hoàn thiện chống lặp/restart. US3 hoàn thiện transport/security/lifecycle.
4. T026-T029 nghiệm thu feature đầy đủ. Chỉ sau đó mới cân nhắc nghiệm thu thật
   do người vận hành chủ động cho phép; không tự chạy live.

## Ngoài phạm vi và tương lai

Chỉ ghi nhận, không tạo task triển khai: nhiều worker/distributed coordination,
outbox/retry giao tin, dashboard lịch sử, multi-chat/per-user, toán tử/chỉ báo mới,
WebSocket nội nến, backfill và migration độ chính xác target public.
Các việc này cần spec riêng, không phải điều kiện hoàn tất feature hiện tại.
Không thêm UI/API/CLI gửi thử, framework rule engine hay migrate localStorage.

## Tổng kết

29 task: Setup3, Nền tảng4, US1=7, US2=4, US3=7, Tích hợp4.
Đã đánh dấu 29 task dựa trên code, test mock và kết quả kiểm tra bên dưới.

## Bằng chứng hoàn tất 2026-10-14

| Task | Bằng chứng |
|---|---|
| T001-T004 | Live gate, socket guard, fake-clock fixtures; test_telegram_live_gate.py, test_telegram_config.py; APScheduler3.11.3/tzlocal5.4.4 trong lock |
| T005-T007 | telegram_state.py/rules.py; test_telegram_state_models.py, test_rules_telegram_metadata.py, test_telegram_state_storage.py: schema, generation, CAS, lỗi Redis |
| T008-T014 | test_telegram_schedule.py, test_closed_klines.py, test_telegram_evaluation.py và E2E lifespan: lịch, readiness/deadline, gộp selection, RSI999, API tương thích |
| T015-T018 | test_telegram_deduplication.py, test_telegram_recovery.py: chuỗi ngưỡng, restart, metadata, mất dữ liệu, không replay |
| T019-T025 | test_telegram_client.py, test_telegram_security.py, test_telegram_lifecycle.py: ack, no retry, token, mutation, cooldown, shutdown, counters |
| T026 | test_telegram_notifications_e2e.py: HTTP CRUD/FastAPI lifespan + mock Binance/Telegram, cả Spot/Futures; event/attempt/accepted riêng |
| T027-T028 | compose.yaml/.env.example mặc định tắt; Compose config quiet đạt; README/quickstart cập nhật; FE API toggle/gte xác nhận, không cần sửa FE |
| T029 | 285 passed, 5 skipped; lint phần mới đạt; diff whitespace đạt; 5 lỗi lint rules.py đã có ở HEAD được ghi rõ |

Lệnh kiểm tra từ gốc repo:

    RUN_TELEGRAM_LIVE_TESTS=0 RUN_OPENAI_LIVE_TESTS=0 .venv/bin/python -m pytest BE/tests -q
    .venv/bin/python -m ruff check --config BE/pyproject.toml BE/app BE/tests
    .venv/bin/python -m ruff check --config BE/pyproject.toml BE/app BE/tests --exclude BE/app/rules.py
    docker compose --env-file .env.example config --quiet
    git diff --check

Lệnh lint toàn backend còn PLR1730, BLE001 (2), UP017, RUF019 ở rules.py.
Đã kiểm tra bản HEAD bằng ruff stdin để xác nhận đây là lỗi cũ; không dùng
exclude để tuyên bố toàn repo sạch. Các dòng mới sửa trong rules.py không có lỗi mới.

Chi tiết triển khai so với cách chia file dự kiến:
- DeliveryResult typed ở telegram_client.py; tái sử dụng TelegramError hiện có,
  không cần sửa errors.py chỉ để tạo thêm lớp lỗi.
- Filter HTTP được cài ngay trong TelegramClient, không phụ thuộc main.py,
  để live test/direct client cũng được bảo vệ. ContextVar không làm mất log Binance.
- Một số test lịch/model/recovery ban đầu vẫn được giữ tại file test tổng hợp;
  đã bổ sung các file chuyên biệt và E2E HTTP theo task.
- Reservation bị cancel lúc shutdown vẫn bền vững; được diễn giải unknown khi
  phục hồi, không ghi success hoặc retry. Callback lặp cùng mốc bị chặn trong process.
- Ngưỡng 70 và 70.0 có cùng fingerprint để PATCH không đổi giá trị không reset.

Chưa nghiệm thu live; không gọi Telegram/Binance thật, không bật watcher thật,
không ghi credentials được chia sẻ vào source/.env, không commit/push.
Giới hạn một worker/replica, không backfill/retry và phụ thuộc Redis durability
vẫn giữ nguyên. Không có hooks mở rộng (.specify/extensions.yml không tồn tại).

## Phase 7: Convergence

Rà soát ngày 2026-10-14 ban đầu: tasks_appended; T030-T032 sau đó đã implement
và kiểm chứng mock. Bằng chứng hoàn tất nằm cuối phase này.
Các tuyên bố hoàn tất phía trên là bằng chứng của lần implement trước,
không bao gồm khoảng trống kiểm chứng và thay đổi yêu cầu bên dưới.
Không sửa application code, spec/plan hoặc task cũ trong lần converge này.

### Công việc còn lại

- [x] T030 [HIGH] Bổ sung kiểm thử dispatch scheduler bằng đồng hồ giả tại BE/tests/test_telegram_schedule.py và BE/tests/test_telegram_notifications_e2e.py theo **FR-001, FR-013, SC-004, T008, T026** (partial, F1). Test trước đó gọi trực tiếp watcher.scan(); kiểm tra ba job/max_instances chưa chứng minh cron tự phát đúng callback. Phụ thuộc: không. Đạt: đưa đồng hồ scheduler qua mốc giờ/ngày/tuần và năm mới, quan sát executor gọi callback đúng timeframe mà không trực tiếp gọi scan; giờ thường không chạy 1d/1w, Thứ Hai 00:00 UTC chạy mỗi khung đúng một lần; startup giữa nến/trong grace chờ mốc tiếp; misfire/max_instances không replay; phân biệt triggered/attempted/accepted. Dùng HTTP mock, fakeredis, không Refresh, không chờ giờ thật và không gọi dịch vụ thật. Đây là thiếu bằng chứng đã bổ sung, không phải lỗi lịch đã tái hiện.
- [x] T031 [MEDIUM] Đồng bộ specs/002-telegram-notifications/spec.md, plan.md, research.md, data-model.md, contracts/telegram-scheduler.md, quickstart.md và hướng dẫn liên quan trong SPEC_KIT.md với thay đổi người dùng yêu cầu ngày 2026-10-14 theo **FR-003, FR-005, FR-007, FR-014, T028** (contradicts, F2). Phụ thuộc: không. Ghi amendment và giữ lịch sử quyết định; định nghĩa đúng/sai và rearm gt/gte/lt/lte, cross_above/cross_below vẫn ngoài phạm vi; below là tên lưu trữ legacy của điều kiện sai; Decimal đầy đủ khi so sánh/lưu, Value hai chữ số với ký hiệu đúng, bỏ Threshold, Open/Close yyyy-mm-dd HH:MM:SS có nhãn UTC. Giữ test biên/equality/lần đầu/chống lặp đang đạt. Không hoàn tác ba toán tử hoặc format đã được người dùng yêu cầu. Phân biệt mock, ví dụ tin thật người dùng cung cấp và nghiệm thu live còn thiếu.
- [x] T032 [MEDIUM] Sửa tiêu chí đạt của BE/tests/test_telegram_client_live.py::test_send_real_message và kiểm chứng bằng mock tại BE/tests/test_telegram_live_gate.py theo **FR-010, FR-012, SC-005, SC-007, T001, T019, T028** (partial, F3). Phụ thuộc: không. Chỉ pass khi status=accepted và message_id hợp lệ; tin thử có nhãn kiểm thử. Mock chứng minh accepted pass, rejected/timeout/ack thiếu không pass; assertion không in token/chat/request. Giữ gate opt-in trước đọc .env; không gọi mạng thật để nghiệm thu task. Test gửi riêng không thay thế bằng chứng scheduler.

### Bằng chứng rà soát

- Đối chiếu 15 FR, 7 SC, 17 acceptance scenarios, 29 task cũ, năm nguyên tắc hiến chương; sáu nhóm quyết định plan: lịch, dữ liệu, state/CRUD, transport, lifecycle/cấu hình, API/kiểm thử.
- Ba finding: partial=2, contradicts=1, missing=0, unrequested=0; HIGH=1, MEDIUM=2. Toán tử/format mới có yêu cầu trực tiếp từ người dùng. Chưa phát hiện lỗi runtime chặn luồng gte trong các đường đi đã mock kiểm chứng; không suy ra không còn lỗi.
- Chạy RUN_TELEGRAM_LIVE_TESTS=0 RUN_OPENAI_LIVE_TESTS=0 .venv/bin/python -m pytest BE/tests -q: **294 passed, 5 skipped**. Fixture chặn socket thật; HTTP/Redis/clock giả.
- Lịch/callback, nến mục tiêu, Spot/Futures, stale/thiếu/gap/nến mở: test_telegram_schedule.py, test_closed_klines.py, test_telegram_recovery.py. Giới hạn dispatch ghi tại T030.
- Gte 68->70->75->69->71, lần đầu đã đạt, lỗi không rearm, bốn toán tử và format: test_telegram_deduplication.py, test_telegram_evaluation.py.
- Restart/state, reconnect sau Redis lỗi lúc startup, reservation dở, tắt/xóa/sửa rule, missing config/shutdown: test_telegram_recovery.py, test_telegram_state_storage.py, test_rules_telegram_metadata.py, test_telegram_lifecycle.py. Không coi các ca này bao phủ mọi kiểu mất kết nối.
- Ack/timeout/429/no-retry/token sentinel/live gate: test_telegram_client.py, test_telegram_security.py, test_telegram_live_gate.py.
- E2E lifespan, HTTP CRUD, mock Binance/Telegram và Redis giả qua restart; đếm riêng triggered/attempted/accepted/unknown, không frontend/Refresh: test_telegram_notifications_e2e.py.
- Hồi quy market/indicator API, TTL/stale, Decimal/UTC và CRUD đạt trong test_market_data.py, test_indicators_api.py và E2E. Đọc routes/schema/service hiện tại không thấy endpoint Telegram mới hoặc contract public ngoài plan. Đây là đối chiếu contract và test hiện tại, không phải so sánh lịch sử toàn API.
- Ruff đầy đủ còn 5 finding tại BE/app/rules.py:81,99,115,121,170 (PLR1730, BLE001 x2, UP017, RUF019). Trùng danh sách đã ghi ở lần kiểm chứng trước; không tuyên bố lint toàn repo đạt. T029 cho phép ghi lỗi tồn tại nên không mở task refactor ngoài phạm vi.

### Nghiệm thu thực tế riêng

Không gọi Telegram/Binance thật, không đọc/sửa .env bằng thao tác kiểm tra,
không restart/build container hoặc can thiệp watcher trong lần converge này.
Watcher đã bật từ phiên trước có thể hoạt động độc lập; không suy ra nó dừng
vì test mock. Người dùng đã cung cấp ví dụ tin Rule #6: đó là một tin quan sát
được, không chứng minh toàn bộ lịch 1h/1d/1w, restart, chống lặp hoặc format mới
đã deploy.

Khi được người vận hành cho phép riêng: xác nhận bản build đúng code, một
worker/replica, Redis bền vững và đồng hồ UTC; ghi rule_id/event_id/nến,
attempt, acknowledgment và tin nhận tại đúng lịch; kiểm tra không lặp qua nến
và restart. Không ép ngưỡng/giờ hoặc gửi thật trong converge để đạt tiêu chí.
Không hứa exactly-once, không backfill và không retry sự kiện lỗi.

### Hoàn tất T030-T032 ngày 2026-10-14

- T030: fixture scheduler_clock tại conftest.py thay đồng hồ scheduler/executor,
  tắt timer thật, gọi wakeup để real cron/job store/executor tự dispatch.
  Tám ca mới kiểm tra calendar/startup/misfire/max_instances; E2E Spot/Futures
  dùng đường dispatch này cả trước/sau restart, không gọi scan trực tiếp.
- T031: amendment trong spec và cập nhật plan/research/model/contract/quickstart,
  SPEC_KIT.md. Lịch sử quyết định cũ giữ rõ nhãn; không sửa checklist reviewer-owned.
- T032: ba ca mock rejected/timeout/ack thiếu tái hiện thất bại trước sửa,
  đạt sau sửa; accepted vẫn pass; payload có nhãn [KIỂM THỬ].
- Test tập trung: 43 passed. Toàn backend: 305 passed, 5 skipped,
  RUN_TELEGRAM_LIVE_TESTS=0 và RUN_OPENAI_LIVE_TESTS=0.
- Ruff file sửa đạt; full Ruff vẫn có 5 lỗi rules.py đã ghi ở trên.
- Không đổi runtime/API/FE/dependency; không gửi thật, không restart/container,
  không commit/push. Không có .specify/extensions.yml nên không có hook mở rộng.
