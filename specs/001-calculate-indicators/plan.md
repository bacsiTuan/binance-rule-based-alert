# Kế hoạch triển khai: SMA, EMA và RSI Wilder

**Nhánh Git thực tế**: main | **Ngày**: 2026-10-11 | **Đặc tả**: [spec.md](spec.md)
**Mã tính năng Spec Kit**: 001-calculate-indicators. setup-plan trả mã này trong BRANCH;
git branch --show-current xác nhận main. Không tạo/chuyển nhánh trong bước lập kế hoạch.
**Đầu vào**: specs/001-calculate-indicators/spec.md và hai quyết định clarify đã chốt.

## Tóm tắt

Thêm POST /indicators để tính nhiều cặp chỉ báo–chu kỳ trên một snapshot KlinesResult.
Route tái sử dụng MarketDataService.klines; tính thuần với Decimal, không thêm cache
chỉ báo. SMA/EMA cần N nến, RSI Wilder cần N+1; trả null/insufficient_data khi thiếu.
Mặc định lọc nến đóng theo cả thời điểm đánh giá và fetched_at. Kết quả giữ metadata
nguồn và cờ provisional riêng. Không sửa FE, CLI, rule engine hoặc gửi cảnh báo.

## Bối cảnh kỹ thuật

**Ngôn ngữ**: Python >=3.11; frontend React 18/Vite 5 hiện có, không thay đổi.
**Dependency**: FastAPI, Pydantic qua stack hiện tại, httpx, redis, pydantic-settings;
Decimal thư viện chuẩn. Không thêm dependency hoặc đổi lockfile.
**Lưu trữ**: Redis cache market data hiện có; không migration, SQL hoặc lưu chỉ báo.
**Kiểm thử**: pytest, pytest-asyncio, MockTransport, fakeredis; Ruff theo BE/pyproject.toml.
**Nền tảng**: API Python local hoặc container Linux, một worker như hiện tại.
**Loại dự án**: Web backend trong BE/, frontend trong FE/.
**Hiệu năng**: O(K*M) thời gian và output; M<=1000, K<=2997 cặp duy nhất.
Đo trường hợp 3 x 1000 và biên lớn; không đưa SLA chưa đo vào tiêu chí nghiệm thu.
**Ràng buộc**: Giữ API/schema/cache cũ, không thêm fetch bù, Decimal không qua float,
UTC milliseconds cho nến, fetched_at ISO 8601. Mock hoàn toàn khi test backend.
**Phạm vi**: Một endpoint mới, hai module chỉ báo, bộ test mới và tài liệu sử dụng.
Không còn quyết định kỹ thuật chặn lập tác vụ.

## Kiểm tra hiến chương

| Nguyên tắc | Trước nghiên cứu | Sau thiết kế |
| --- | --- | --- |
| I. Tương thích API | Đạt: endpoint riêng | Đạt: /klines, /symbols, /health, CLI và schema cũ giữ nguyên |
| II. Chính xác dữ liệu | Đạt: Decimal, UTC, market nguồn | Đạt: seed, cutoff, sai số và metadata có hợp đồng/test |
| III. TTL và stale | Đạt: tái sử dụng service | Đạt: không cache chỉ báo, không sửa TTL/payload; giữ retry/fallback |
| IV. Kiến trúc | Đạt: BE/FE hiện có | Đạt: route mỏng + bộ tính thuần, không hạ tầng/dependency mới |
| V. Mock test | Đạt: công cụ có sẵn | Đạt: fixture và ma trận hồi quy trong quickstart |

Không có vi phạm cần miễn trừ. Hiện trạng được đối chiếu README.md,
BE/pyproject.toml, FE/package.json và BE/app cùng BE/tests.
Giới hạn fetched_at được ghi rõ trong research.md, không thay đổi hợp đồng nguồn.

## Cấu trúc dự án

### Tài liệu tính năng

- spec.md: yêu cầu và quyết định đã chốt.
- plan.md: kế hoạch này.
- research.md: quyết định, lý do, phương án đã xem xét.
- data-model.md: schema và bất biến.
- contracts/indicators-api.md: HTTP contract.
- quickstart.md: hướng dẫn nghiệm thu sau triển khai.
- tasks.md: do bước speckit-tasks tạo sau, chưa tạo trong lần này.

### Mã nguồn dự kiến

| Đường dẫn | Thay đổi cần thiết |
| --- | --- |
| BE/app/indicator_models.py | Thêm request/result/point models riêng; import Interval từ models.py |
| BE/app/indicators.py | Thêm validation snapshot, lọc nến, Decimal và bộ tính thuần |
| BE/app/main.py | Thêm route POST /indicators và ánh xạ lỗi chỉ báo cục bộ |
| BE/tests/test_indicators.py | Fixture cố định, test công thức, seed, null, precision, thời gian |
| BE/tests/test_indicators_api.py | HTTP contract, validation, metadata và cache với mock |
| BE/tests/test_market_data.py | Chạy hồi quy nguyên bộ; chỉ bổ sung nếu thiếu chứng minh tương thích |
| README.md, BE/README.md | Ghi API chỉ báo và giới hạn sau khi triển khai thành công |

BE/app/models.py, service.py, binance/client.py, cache/redis_cache.py, config.py
được tái sử dụng, không cần đổi hành vi. FE/, cli.py, manifest, lockfile và
compose.yaml không thuộc phạm vi sửa. Không thêm repository/service abstraction.

## Giai đoạn 0: Nghiên cứu

Đã hoàn tất [research.md](research.md): điểm tích hợp, Decimal, snapshot, lỗi và test.
Nghiên cứu độc lập đã đối chiếu service/client/models/tests; quyết định hợp nhất
không yêu cầu thay stack hoặc xin thay đổi phạm vi.

## Giai đoạn 1: Thiết kế

1. Validate body và cặp trùng trước I/O, không cho client chọn market/host hoặc
   thời điểm đánh giá. Thị trường lấy từ Settings hiện có.
2. Gọi service.klines một lần với symbol/interval/limit yêu cầu. Chỉ luồng service
   hiện có được fetch và ghi cache theo quy tắc hiện hành.
3. Cố định evaluated_at_ms sau khi nhận snapshot. Bộ tính nhận snapshot, các cặp,
   include_open, thời điểm và nhận diện mong đợi; validate trước khi lọc.
4. Chuyển giá từ chuỗi sang Decimal, xác định cutoff, tạo tập nến dùng chung.
   Tính từng cặp trong thứ tự yêu cầu; seed lại từ đầu snapshot cho mỗi lần gọi.
5. Tạo chuỗi points cùng chiều dài tập nến, warm-up null, summary mới nhất theo
   điểm cuối; gắn source/stale/warning/fetched_at/cache_key nguyên nghĩa.
6. Trả 200 kể cả thiếu nến; 422 đầu vào sai, 502 snapshot sai; lỗi nguồn giữ nguyên.
   Không bắt Exception chung rồi chuyển thành thiếu dữ liệu.

Chi tiết tại [mô hình](data-model.md) và [hợp đồng](contracts/indicators-api.md).

### Cách tính và biên dữ liệu

- SMA: tổng trượt N close / N; N-1 null đầu.
- EMA: seed SMA của N close đầu, alpha=2/(N+1); N-1 null đầu.
- RSI: N gain/loss đầu từ N+1 close; Wilder avg=(avg*(N-1)+next)/N.
  N null đầu; loss=0/gain>0 cho 100; gain=0/loss>0 cho 0; cả hai 0 cho 50.
- Chuỗi rỗng trả points=[], latest có timestamp/value null, insufficient_data.
- Các cặp độc lập về warm-up; không tăng limit hoặc fetch bù khi thiếu nến.
- Tập mặc định: close_time < min(evaluated_at_ms, fetched_at_ms).
  include_open=true giữ cả nến mở, đánh dấu các kết quả phụ thuộc là provisional.
- Khoảng trống giữ số quan sát thực tế; không lấp, sort hoặc tự loại dữ liệu hỏng.

### Chiến lược nghiệm thu

Unit: giá cố định, oracle phân số độc lập, warm-up N=1/14/999, biên 0/N-1/N/N+1,
1000 điểm, đồng hồ cố định, snapshot bất biến. HTTP: gọi qua app với service dùng
MockTransport/fakeredis, không dùng mạng. Regression: toàn bộ test market data cũ.
Tiêu chí và lệnh chi tiết trong [quickstart](quickstart.md).

## Theo dõi độ phức tạp

Không có ngoại lệ hiến chương. Rủi ro còn lại: output tăng theo K*M, độ chính xác
cần được kiểm chứng trên fixture nhiều chữ số, fetched_at không phải timestamp
chụp dữ liệu của Binance. Không mở rộng phạm vi để giải quyết hạ tầng chưa được yêu cầu.

Kết thúc ở thiết kế giai đoạn 1. Bước tiếp theo là speckit-tasks, chưa triển khai ứng dụng.
