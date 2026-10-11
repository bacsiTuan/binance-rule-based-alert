# Tác vụ: SMA, EMA và RSI Wilder

**Đầu vào**: specs/001-calculate-indicators/ gồm [spec](spec.md), [plan](plan.md),
[research](research.md), [data-model](data-model.md), [contract](contracts/indicators-api.md),
[quickstart](quickstart.md) và hiến chương dự án.
**Kiểm thử**: Bắt buộc theo FR-014; viết test trước phần triển khai tương ứng và xác nhận
test phát hiện hành vi chưa có. Không cần làm lại phần đã đúng chỉ để tạo test đỏ.
**Tổ chức**: Ba câu chuyện theo spec: US1 (P1), US2 (P1), US3 (P2).
Mọi checkbox ban đầu chưa hoàn thành; tài liệu này không xác nhận mã đã được triển khai.

## Định dạng và đường dẫn

Mỗi tác vụ có ID tuần tự, [P] nếu có thể làm song song tại điểm phụ thuộc đã nêu,
[US1]/[US2]/[US3] cho tác vụ câu chuyện. Đường dẫn tính từ gốc repository.
Không sửa FE/, CLI, dependency, deployment, client/cache/schema market data chung.
Chỉ thêm BE/app/indicator_models.py, BE/app/indicators.py, hai file test chỉ báo,
sửa route trong BE/app/main.py và tài liệu cần thiết.

## Giai đoạn 1: Chuẩn bị

**Mục tiêu**: Kiểm tra nền hiện có, không khởi tạo lại ứng dụng.

- [X] T001 Đối chiếu BE/pyproject.toml, BE/requirements.lock.txt và BE/tests/test_market_data.py; chuẩn bị môi trường Python >=3.11 với dependency khóa hiện có nếu cần, chạy bộ test market data và Ruff để ghi baseline vào specs/001-calculate-indicators/quickstart.md; không đổi manifest hoặc lockfile.

## Giai đoạn 2: Nền tảng dùng chung

**Mục tiêu**: Hoàn thiện schema chung trước các câu chuyện; giữ model market data cũ.
Test theo từng câu chuyện bên dưới phải kiểm tra các schema này trước khi đánh dấu câu chuyện đạt.

- [X] T002 Tạo IndicatorSelection/IndicatorRequest trong BE/app/indicator_models.py, import Interval hiện có; giữ symbol mặc định BTCUSDT với “ASCII chữ/số, 2–30 ký tự; chuẩn hóa uppercase; không trim ngầm”, interval mặc định 1h với “Tái sử dụng 1h/1d/1w”, limit mặc định 300 với “Strict, 1–1000; bool/string/float không hợp lệ”, include_open mặc định false kiểu “Strict”, indicators bắt buộc “Không rỗng, tối đa 2997 cặp duy nhất”; áp dụng “name là enum chữ thường sma/ema/rsi; period là integer strict 1–999, default 14.” và “Cấm trường lạ. Không nhận market, host, candles, evaluated_at từ client.”
- [X] T003 Thêm IndicatorPoint/IndicatorSeries/IndicatorsResult trong BE/app/indicator_models.py đúng data-model.md: “value (chuỗi thập phân hoặc null)”, “status (ok/insufficient_data), provisional (boolean)”, “Trong points, timestamp luôn là integer, chỉ sentinel latest rỗng mới cho null.”; series có name, period, required_candles (N hoặc N+1), available_candles “bằng eligible_candles”, points và latest; envelope giữ market/symbol/interval kiểu KlinesResult, source “binance/cache/stale”, stale boolean, fetched_at “UTC ISO 8601”, cache_key string, warning “string hoặc null”, evaluated_at integer UTC ms, include_open boolean, input_candles/eligible_candles/excluded_candles integer, series_start_time “integer hoặc null”, results “Một mục mỗi cặp, đúng thứ tự request”; không sửa BE/app/models.py.

**Điểm kiểm tra**: T001 → T002 → T003 hoàn tất trước khi bắt đầu US1.

## Giai đoạn 3: US1 - Nhận giá trị chỉ báo có thể đối chiếu (P1)

**Mục tiêu**: API riêng trả ba loại chỉ báo, nhiều chu kỳ trên snapshot nến đóng.
**Kiểm thử độc lập**: Fixture giá đóng cố định cho SMA/EMA/RSI, ít nhất hai bước sau seed;
HTTP mock xác nhận thứ tự cặp, metadata và service được gọi một lần.

### Kiểm thử US1

- [X] T004 [P] [US1] Tạo BE/tests/test_indicators.py với fixture Candle/KlinesResult và đồng hồ cố định; kiểm tra SMA3 trên 1,2,3,6,5 cho 2,11/3,14/3; EMA3 cho 2,4,9/2; RSI3 trên 1,2,3,2,4,3 cho 200/3,250/3,2000/33; thêm tăng/giảm/đi ngang, so sánh Fraction độc lập theo max(1e-12,abs(expected)*1e-12), xác nhận timestamp không lệch.
- [X] T005 [P] [US1] Tạo BE/tests/test_indicators_api.py với app HTTP và service mock không kết nối thật; kiểm tra POST /indicators nhận SMA20/SMA50/EMA14/RSI14, defaults, symbol uppercase, response string thay vì number, thứ tự cặp và đầy đủ metadata; xác nhận một lần gọi klines với symbol/interval/limit và không thêm chỉ báo vào GET /klines.

### Triển khai US1

- [X] T006 [US1] Tạo bộ tính thuần trong BE/app/indicators.py nhận KlinesResult, lựa chọn, include_open, evaluated_at_ms và nhận diện mong đợi; dùng Decimal từ close string với localcontext ROUND_HALF_EVEN, precision max(50,A-E+1+32) theo research.md, chuỗi toàn 0 dùng 50, không float/quantize/context toàn cục; chuẩn bị envelope theo T003, không I/O hoặc sửa snapshot.
- [X] T007 [US1] Triển khai SMA tổng trượt và EMA seed SMA(N), alpha=2/(N+1) trong BE/app/indicators.py; giữ N-1 điểm null đầu, N=1 bằng close, xuất fixed-point string và chuẩn hóa zero thành “0”; tính riêng từng cặp và seed lại mỗi lần gọi.
- [X] T008 [US1] Triển khai RSI Wilder trong BE/app/indicators.py: N biến động từ N+1 nến, seed trung bình gain/loss, cập nhật (avg*(N-1)+next)/N, RSI=100-100/(1+gain/loss), các trường hợp 100/0/50 và N điểm null đầu; không NaN/vô cực.
- [X] T009 [US1] Thêm POST /indicators trong BE/app/main.py dùng schema T002/T003; gọi app.state.service.klines đúng một lần, lấy evaluated_at sau snapshot bằng UTC ms số học nguyên rồi gọi bộ tính; truyền market cấu hình và nhận diện mong đợi, giữ nguyên lifecycle, handlers nguồn, route cũ và CLI.
- [X] T010 [US1] Chạy các ca US1 trong BE/tests/test_indicators.py và BE/tests/test_indicators_api.py; bổ sung đối chiếu Spot/Futures, snapshot bất biến và nhiều chu kỳ cùng tên nếu thiếu; xác nhận toàn bộ fixture đủ dữ liệu đạt và lưu kết quả vào specs/001-calculate-indicators/quickstart.md.

**Điểm kiểm tra**: US1 là bản thử nghiệm nhỏ trên fixture nến đóng; chưa phát hành trước
khi hoàn tất thiếu dữ liệu và chính sách nến mở của US2/US3.

## Giai đoạn 4: US2 - Thiếu nến và dữ liệu không hợp lệ (P1)

**Mục tiêu**: Tách thiếu dữ liệu hợp lệ với lỗi body/snapshot/nguồn.
**Kiểm thử độc lập**: 0,N-1,N,N+1 nến; N=1/14/999; rỗng và cặp đủ/thiếu trong một response;
body sai trả 422 trước I/O, snapshot sai trả 502.

### Kiểm thử US2

- [X] T011 [P] [US2] Mở rộng BE/tests/test_indicators.py với biên số nến, chuỗi rỗng, giá rất nhỏ/nhiều chữ số, NaN/âm/vô cực, timestamp không nguyên/trùng/đảo, open_time>close_time, fetched_at thiếu timezone và nhận diện sai; kiểm tra khoảng trống vẫn dùng quan sát thực tế, không sort/lấp/bỏ nến.
- [X] T012 [P] [US2] Mở rộng BE/tests/test_indicators_api.py với bool/string/float cho period/limit, tên lạ, trường lạ, include_open sai kiểu, [] và cặp trùng kể cả SMA bỏ period trùng SMA14; kỳ vọng 422 và không gọi service; kiểm tra 200 insufficient_data riêng từng cặp và 502 invalid_indicator_data cho snapshot cuối sai.

### Triển khai US2

- [X] T013 [US2] Hoàn thiện validation cặp trong BE/app/indicator_models.py theo “Khóa duy nhất là (name, period) sau default; trùng từ chối toàn request, không gộp.” và “Một phần tử sai làm toàn body không hợp lệ.”; hoàn thiện strict/defaults/extra-forbid theo T002 để mọi ca T012 bị từ chối trước I/O.
- [X] T014 [US2] Thêm validation toàn snapshot trước lọc trong BE/app/indicators.py: “giá hữu hạn không âm; timestamp nguyên”, “open_time và close_time tăng nghiêm ngặt”, “open_time<=close_time”, “interval khớp yêu cầu và cấu hình. fetched_at phải có timezone.” cùng kiểm tra market/symbol; tạo lỗi chỉ báo riêng, không sửa Candle/KlinesResult hoặc hành vi cache chung.
- [X] T015 [US2] Hoàn thiện kết quả thiếu dữ liệu trong BE/app/indicators.py: required_candles=N cho SMA/EMA, N+1 cho RSI; available_candles bằng eligible_candles, “Points không rỗng thì latest bằng điểm cuối, không phải giá trị hợp lệ gần nhất.”; áp dụng “Points rỗng thì latest có open_time, close_time,value đều null, status=insufficient_data, provisional=false.”, series_start_time null khi rỗng; không tăng limit/fetch bù hoặc dùng zero thay null.
- [X] T016 [US2] Ánh xạ lỗi bộ tính cục bộ tại BE/app/main.py thành 502 với detail.code=invalid_indicator_data và detail.message theo contracts/indicators-api.md; giữ lỗi BinanceError/CacheError, không bắt Exception chung và không trả kết quả từng phần khi lỗi.
- [X] T017 [US2] Chạy và hoàn thiện kiểm thử US2 trong BE/tests/test_indicators.py và BE/tests/test_indicators_api.py; xác nhận SMA20/SMA50 trên 30 nến lần lượt ok/insufficient_data, chuỗi rỗng 200 và snapshot sai 502; ghi kết quả vào specs/001-calculate-indicators/quickstart.md.

## Giai đoạn 5: US3 - Nến mở và metadata dữ liệu cũ (P2)

**Mục tiêu**: Lọc chính xác nến đóng, hỗ trợ provisional, giữ nguồn/cache hiện có.
**Kiểm thử độc lập**: Đồng hồ cố định cho cutoff, snapshot từng chứa nến mở và stale;
mock I/O chứng minh không gia hạn TTL, fetch bù hoặc trộn thị trường.

### Kiểm thử US3

- [X] T018 [P] [US3] Mở rộng BE/tests/test_indicators.py với close_time trước/bằng/sau evaluated_at và fetched_at, snapshot được fetch trước giờ đóng nhưng đánh giá sau giờ đóng, lọc hết nến; kiểm tra provisional cho SMA theo cửa sổ và EMA/RSI theo prefix kể cả warm-up, độc lập stale.
- [X] T019 [P] [US3] Mở rộng BE/tests/test_indicators_api.py bằng service hiện có với MockTransport/fakeredis, Settings(_env_file=None), đóng tài nguyên sau test; kiểm tra hit/miss/stale và metadata, TTL giảm không tăng, không key chỉ báo, không fetch bù, retry/cooldown/Retry-After, Redis lỗi, phân biệt market/host/interval/limit và refresh đồng thời chia sẻ lock với market data.

### Triển khai US3

- [X] T020 [US3] Hoàn thiện lọc/counter trong BE/app/indicators.py theo “Closed khi close_time < min(evaluated_at, fetched_at_ms); bằng cutoff là chưa đóng.” và “include_open=false loại mọi nến không closed, mọi point provisional=false.”; chuyển datetime UTC sang ms bằng số học nguyên, input_candles là số nguồn, eligible_candles là số sau lọc, excluded_candles=input_candles-eligible_candles, series_start_time là open_time đầu sau lọc.
- [X] T021 [US3] Triển khai include_open=true trong BE/app/indicators.py: giữ toàn snapshot hợp lệ, SMA provisional theo cửa sổ N, EMA/RSI theo bất kỳ nến chưa closed trong prefix; “Trong warm-up, áp dụng cùng nguyên tắc trên prefix đang có.”; giữ “stale không thay đổi theo việc tính lại, độc lập status và provisional.” và không sửa fetched_at nguồn.
- [X] T022 [US3] Hoàn thiện tích hợp đồng hồ/metadata tại BE/app/main.py và BE/app/indicators.py: evaluated_at cố định đúng một lần sau snapshot; mọi cặp dùng chung tập nến; giữ nguyên market/symbol/interval/source/stale/warning/fetched_at/cache_key; không thêm retry, ghi cache hoặc đổi service/client.
- [X] T023 [US3] Chạy US3 trong BE/tests/test_indicators.py, BE/tests/test_indicators_api.py và hồi quy BE/tests/test_market_data.py; xác nhận source stale vẫn có thể status ok, provisional độc lập và GET /klines giữ nến cuối; ghi bằng chứng vào specs/001-calculate-indicators/quickstart.md.

## Giai đoạn 6: Hoàn thiện và nghiệm thu chung

**Mục tiêu**: Chứng minh toàn bộ phạm vi trước khi công bố đã triển khai.

- [X] T024 [P] Bổ sung/chạy kiểm tra 100 lần tính cùng đầu vào và oracle Fraction cho chuỗi 1000 nến trong BE/tests/test_indicators.py; kiểm tra precision/context không rò rỉ, seed độc lập từng request, sai số FR-009 và snapshot bất biến.
- [X] T025 [P] Bổ sung kiểm thử hợp đồng đầy đủ trong BE/tests/test_indicators_api.py cho response nullable/enum/counters/latest và tất cả mã 200/400/418/422/429/502/503 theo specs/001-calculate-indicators/contracts/indicators-api.md; chứng minh request hợp lệ dùng một lần service và request sai không I/O.
- [X] T026 Đo thời gian, kích thước response và bộ nhớ cho 3x1000 điểm và 2997 cặp với tối đa 1000 nến theo specs/001-calculate-indicators/quickstart.md, ghi kết quả vào chính tài liệu đó; dùng fixture/mock, không đặt SLA CI tùy tiện hoặc đổi giới hạn sản phẩm.
- [X] T027 Chạy python -m pytest BE/tests -q và python -m ruff check --config BE/pyproject.toml BE/app BE/tests; đối chiếu mọi mục ma trận trong specs/001-calculate-indicators/quickstart.md, ghi kết quả thật và các kiểm tra chưa chạy, không yêu cầu mạng thật hoặc build FE.
- [X] T028 [P] Sau T027 đạt, cập nhật README.md bằng tiếng Việt với POST /indicators, defaults, nhiều chu kỳ, null khi thiếu nến, provisional/stale, giới hạn fetched_at; giữ thay đổi sẵn có của người dùng và phân biệt indicator đã có với rule engine/cảnh báo còn dự kiến.
- [X] T029 [P] Sau T027 đạt, cập nhật BE/README.md bằng tiếng Việt với cách gọi API mới, test mock và tham chiếu contract/quickstart; giữ lệnh CLI và market data hiện có, không tuyên bố thêm UI/SQL/scheduler.
- [X] T030 Rà soát diff và liên kết trong README.md, BE/README.md, specs/001-calculate-indicators/quickstart.md; xác nhận thay đổi ứng dụng chỉ nằm ở BE/app/indicator_models.py, BE/app/indicators.py, BE/app/main.py và test cần thiết; đánh dấu tác vụ hoàn thành trong specs/001-calculate-indicators/tasks.md chỉ khi có bằng chứng tương ứng.

## Phụ thuộc và thứ tự thực hiện

Luồng giai đoạn: Chuẩn bị → Nền tảng → US1 → US2 → US3 → Nghiệm thu chung.
Các câu chuyện kiểm thử riêng được nhưng dùng chung module/route, vì vậy không
triển khai song song cả câu chuyện. Đây là thứ tự tích hợp, không thay thứ tự ưu tiên.

| Nhóm | Phụ thuộc |
| --- | --- |
| T001–T003 | Tuần tự theo ID |
| T004, T005 | Sau T003; có thể viết test song song |
| T006–T010 | Sau T004/T005; tuần tự, test US1 phải đạt ở T010 |
| T011, T012 | Sau T010; có thể viết test song song |
| T013–T017 | Sau T011/T012; tuần tự |
| T018, T019 | Sau T017; có thể viết test song song |
| T020–T023 | Sau T018/T019; tuần tự |
| T024, T025 | Sau T023; hai file test độc lập |
| T026, T027 | Sau T024/T025; tuần tự |
| T028, T029 | Sau T027; hai file tài liệu độc lập |
| T030 | Sau T028/T029 |

Các test viết trước phần triển khai story có thể ban đầu fail vì hành vi chưa có;
schema cơ bản đã tồn tại thì test validation tương ứng được phép pass.
Không ghi [P] cho các phép tính SMA/EMA/RSI vì cùng sửa BE/app/indicators.py.

## Ví dụ thực hiện song song

- US1: T004 viết test công thức ở BE/tests/test_indicators.py cùng T005 viết test HTTP
  ở BE/tests/test_indicators_api.py, sau T003.
- US2: T011 test biên snapshot cùng T012 test body/HTTP, sau T010.
- US3: T018 test cutoff/provisional cùng T019 test cache/metadata, sau T017.
- Hoàn thiện: T024/T025; sau kiểm tra đạt, T028/T029.
Các ví dụ là cơ hội tổ chức công việc, không yêu cầu tự động khởi tạo agent.

## Ánh xạ yêu cầu

| Yêu cầu | Tác vụ chính |
| --- | --- |
| FR-001 | T002, T005, T009, T012, T013 |
| FR-002 | T011, T014, T016 |
| FR-003/004/005 | T004, T006, T007, T008 |
| FR-006 | T003, T011, T015, T017 |
| FR-007/008 | T018, T020, T021, T022 |
| FR-009 | T006, T024 |
| FR-010 | T003, T005, T019, T022 |
| FR-011/012 | T009, T015, T019, T023, T027 |
| FR-013 | T007, T008, T024 |
| FR-014 | T004, T005, T011, T012, T018, T019, T024–T027 |
| FR-015 | T009, T028–T030 |
| SC-001/002 | T004, T011, T017, T024 |
| SC-003/004 | T018, T019, T023, T027 |
| SC-005/006 | T003, T015, T022, T024, T025 |

## Chiến lược triển khai

1. Hoàn thành nền tảng rồi US1 để có bản thử nghiệm nhỏ trên nến đóng cố định.
2. Thêm US2, xác nhận riêng thiếu dữ liệu và lỗi; không dùng null che lỗi nguồn.
3. Thêm US3, xác nhận cutoff, metadata và cache; đây là điều kiện trước phát hành.
4. Hoàn tất kiểm thử chung và tài liệu; chỉ công bố toàn tính năng sau T030.
MVP kỹ thuật là US1 với fixture hợp lệ, không phải thay thế phạm vi đầy đủ đã chốt.
Không thêm rule engine, cảnh báo, frontend, CLI mới, dependency hoặc hạ tầng.

## Ghi chú

- Sửa file theo phạm vi, không revert thay đổi người dùng.
- Không sửa hiến chương hoặc template trong khi thực hiện danh sách này.
- Test tự động chỉ dùng fixture/mock; thử mạng thật trong quickstart là tùy chọn,
  không phải điều kiện đánh dấu tác vụ hoàn thành.
- fetched_at chỉ là metadata backend hiện có; không tuyên bố chứng minh tuyệt đối
  giá đóng cuối tại ranh giới thời gian.

## Phase 7: Convergence

- [ ] T031 HIGH (F1) Cô lập đầy đủ context Decimal của bộ tính trong BE/app/indicators.py để cùng snapshot/tham số không phụ thuộc traps hoặc cấu hình số học của bên gọi; hiện SMA(3) trên giá 1,2,4 trả 2.333… với context mặc định nhưng ném IndicatorDataError khi context bên ngoài bật trap Inexact. Thiết lập context tính toán xác định, giữ precision/ROUND_HALF_EVEN đã chốt và không sửa context bên ngoài; bổ sung test hồi quy trong BE/tests/test_indicators.py cho SMA/EMA/RSI với traps và giới hạn exponent bên ngoài khác nhau, xác nhận kết quả như baseline, snapshot/context bên gọi bất biến và lỗi dữ liệu hỏng vẫn được xử lý đúng. Chạy lại toàn bộ test backend/Ruff và cập nhật bằng chứng nghiệm thu liên quan trong specs/001-calculate-indicators/quickstart.md theo FR-013, US1/AC3, T006, T024 (partial).
