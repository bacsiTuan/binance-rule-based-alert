# Hướng dẫn nghiệm thu sau triển khai

Endpoint và bộ test đã được triển khai; kết quả chạy ngày 2026-10-11 ở cuối tài liệu.
Các lệnh bên dưới dùng để lặp lại kiểm tra.
Tham chiếu [hợp đồng](contracts/indicators-api.md), [mô hình](data-model.md).

## Chuẩn bị

Tại gốc repository, dùng Python >=3.11, môi trường ảo riêng và dependency lock hiện có:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e "./BE[dev]" -c BE/requirements.lock.txt
```

Windows thay .venv/bin/python bằng .venv/Scripts/python.exe.
Không cần tạo .env, chạy Docker, Redis thật hoặc kết nối Binance để chạy test.
Fixture phải Settings(_env_file=None), MockTransport và fakeredis, đóng tài nguyên
sau test. Test HTTP inject service giả hoặc service thật dùng transport/Redis giả;
không vô tình dùng kết nối Redis thật do lifespan.

## Kiểm tra tự động

```sh
.venv/bin/python -m pytest BE/tests/test_indicators.py BE/tests/test_indicators_api.py -q
.venv/bin/python -m pytest BE/tests -q
.venv/bin/python -m ruff check --config BE/pyproject.toml BE/app BE/tests
```

Kỳ vọng: tất cả test mới và test market data hiện có pass; Ruff không có lỗi.
Không cố định số lượng test theo README cũ. Không cần build FE vì FE không đổi.

## Bộ dữ liệu đối chiếu

Mỗi fixture dùng giá dạng string, timestamp tăng, fetched_at/evaluated_at cố định
sau close_time của mọi nến trừ ca kiểm tra nến mở. Không lấy expected bằng chính
hàm production; dùng hằng phân số và Fraction làm oracle độc lập khi cần.

| Fixture | Yêu cầu | Giá trị sau warm-up |
| --- | --- | --- |
| 1,2,3,6,5 | SMA(3) | 2, 11/3, 14/3 |
| 1,2,3,6,5 | EMA(3) | 2, 4, 9/2 |
| 1,2,3,2,4,3 | RSI(3) | 200/3, 250/3, 2000/33 |
| 1,2,3,4,5 | RSI(3) | 100, 100 |
| 5,4,3,2,1 | RSI(3) | 0, 0 |
| 2,2,2,2,2 | RSI(3) | 50, 50 |

So sánh theo max(1e-12, abs(expected)*1e-12), không so sánh chuỗi định dạng
cho phân số vô hạn. Kiểm tra thêm N=1, N=999 và chuỗi 1000 nến; giá rất nhỏ,
giá nhiều chữ số với chênh lệch nhỏ và xen kẽ tăng/giảm.
Oracle Fraction ở test cho chuỗi dài; không làm tròn intermediate expected.

## Ma trận nghiệm thu

| Nhóm | Thực hiện | Kết quả |
| --- | --- | --- |
| Công thức | Fixture bảng trên, ít nhất hai bước sau seed | Đúng SMA/EMA/RSI, không lệch nến |
| Warm-up | M=0,N-1,N,N+1 với N=14 | SMA/EMA bắt đầu N; RSI N+1; null trước đó |
| Nhiều cặp | SMA20,SMA50 cùng snapshot 30 nến | Hai kết quả riêng, ok và insufficient_data |
| Trùng cặp | SMA14 và SMA bỏ period | 422, service không được gọi |
| Validation | Tên lạ, bool/float/string period, period=0/1000, [] | 422 trước I/O |
| Snapshot | Sai nhận diện, giá hỏng, trùng/đảo thời gian | 502 chỉ báo, không sort/bỏ nến |
| Cutoff | close_time bằng/trước/sau từng cutoff | Dùng điều kiện nhỏ hơn nghiêm ngặt |
| Nến cache từng mở | fetched_at trước close_time, evaluated_at sau | Mặc định loại; bật include_open thì provisional |
| Provisional | Có nến chưa closed trong phụ thuộc | SMA theo cửa sổ; EMA/RSI theo prefix |
| Snapshot rỗng | Nguồn trả danh sách rỗng hợp lệ | 200, points=[], latest null, insufficient_data |
| Metadata | source binance/cache/stale | Giữ market/source/stale/warning/fetched_at/cache_key |
| Cache hit | Hai lần cùng symbol/interval/limit | Một fetch, không key chỉ báo, TTL không tăng |
| Stale | Làm hết fresh key trong fakeredis rồi mock 5xx | Giữ fetched_at, không refresh TTL stale |
| Nguồn lỗi | Invalid symbol, cooldown, Redis lỗi | Status/body/Retry-After theo contract cũ |
| Phân tách | Spot/Futures, host, limit, interval khác | Không trộn snapshot/key |
| Tính lặp | 100 lần cùng input, thời gian cố định | Cùng output, snapshot không đổi |
| Tương thích | Chạy test_market_data.py nguyên bộ | API cũ, nến cuối và cache không đổi |
| Quy mô | 3x1000 điểm và tối đa 2997 cặp | Ghi thời gian, kích thước, bộ nhớ; không lỗi số học |

Để kiểm tra TTL không tăng, dùng thời gian giả nếu phù hợp với fakeredis hoặc
so sánh TTL trong khoảng giảm cho phép; không đòi hai lần đọc TTL bằng tuyệt đối.
Mô phỏng lỗi bằng transport giả; không dựa mạng hoặc sleep dài.
Đối chiếu bất biến snapshot bằng bản dump trước/sau. Kiểm tra không thêm key Redis.

## Thử thủ công tùy chọn với dịch vụ thật

Chỉ thực hiện khi cần kiểm tra vận hành; không thay thế bộ test mock.
Chuẩn bị .env theo README, chạy Redis và backend như hướng dẫn hiện có.
Chạy từ gốc repository:

```sh
docker compose up -d redis
.venv/bin/python -m uvicorn app.main:app --app-dir BE --host 127.0.0.1 --port 8000
```

Ở terminal khác:

```sh
curl -sS -X POST http://127.0.0.1:8000/indicators \
  -H 'Content-Type: application/json' \
  -d '{"symbol":"BTCUSDT","interval":"1h","limit":300,"indicators":[{"name":"sma","period":20},{"name":"sma","period":50},{"name":"ema","period":14},{"name":"rsi","period":14}]}'
```

Kỳ vọng HTTP 200 khi nguồn sẵn sàng, bốn mục results đúng thứ tự.
Không so sánh giá Binance thật với fixture. Lần gọi lại trong TTL giữ fetched_at,
source chuyển cache nếu lần trước fetch thành công. GET /klines vẫn có nến cuối
và không có trường chỉ báo. Thử limit=1, SMA14 cho insufficient_data khi nguồn
trả đủ tối đa một nến; thêm include_open=true vẫn không đủ 14.

Khi ghi báo cáo nghiệm thu, tách kết quả test mock và thử thủ công; ghi rõ lỗi nguồn
nếu có. Chỉ cập nhật README rằng tính năng đã có sau khi kiểm tra triển khai đạt.

## Kết quả triển khai 2026-10-11

- Python 3.14.7, macOS arm64; dependency cài theo BE/requirements.lock.txt,
  không sửa manifest/lockfile. Baseline: 17 test market data pass, Ruff sạch.
- US1: 8 test ban đầu pass sau khi xác nhận bộ tính chưa tồn tại làm test đỏ.
- US2: thêm ca thiếu nến/body/snapshot; 14 ca lỗi trước xử lý validation,
  sau triển khai 80 test chỉ báo pass.
- US3: 14 ca cutoff/nến mở thất bại trước khi lọc, sau triển khai toàn bộ 126 test pass.
- Hoàn thiện: 134 test pass (17 cũ + 117 mới); Ruff sạch. Có một cảnh báo deprecation
  Starlette/httpx từ test market data cũ, không phải lỗi và không đổi dependency.
- Oracle Fraction dạng trọng số độc lập đã đối chiếu chuỗi 1000 nến có giá rất nhỏ
  và giá nhiều chữ số; kiểm tra 100 lần tính lặp và context Decimal độc lập đã đạt.
- Ma trận trên được kiểm tra bằng fixture/mock, kể cả lỗi 400/418/422/429/502/503,
  thứ tự cache hỏng, đồng hồ một lần, metadata, counter, latest và OpenAPI.
- Không chạy Binance/Redis thật, Docker hoặc build FE vì không thay FE/deployment.
  Checklist yêu cầu không bị sửa. Chỉ bổ sung ignore biến thể .env, log và .DS_Store
  ở bước xác minh môi trường; không thay template, hiến chương hoặc API cũ.

### Benchmark HTTP trong process

ASGITransport với snapshot giả 1000 nến, giá close=(i*17)%97+1, thời gian cố định;
không chạy lifespan Redis thật. Mỗi lần đo ở process riêng, từ trước HTTP request
đến khi nhận đủ response; đo peak RSS toàn process bằng resource.getrusage
(đơn vị byte trên macOS). Chọn ba loại chu kỳ 14 hoặc toàn bộ chu kỳ 1–999.

| Cặp chỉ báo | Nến | Thời gian | Response byte | Peak RSS byte | HTTP |
| --- | --- | --- | --- | --- | --- |
| 3 | 1000 | 0,00994 giây | 400756 | 75399168 | 200 |
| 2997 | 1000 | 11,52414 giây | 357572646 | 2961768448 | 200 |

Kết luận nghiệm thu: miền tối đa đã hoàn tất trên máy kiểm tra, không lỗi số học;
đây chỉ là đo một request, không chứng nhận tải đồng thời/production. Giữ giới hạn
đã chốt, không tự giảm 2997 cặp. Với deployment ít RAM hoặc yêu cầu độ trễ thấp,
cần chốt giới hạn request và ngân sách tài nguyên ở công việc riêng trước khi mở
tải lớn; không xem benchmark này là bảo đảm vận hành. Route hiện tính đồng bộ,
nên request lớn chiếm worker trong lúc tính/serialize. README ghi rõ giới hạn.

Test test_fetch_completion_metadata_is_not_exchange_finality_proof minh họa:
metadata fetch sau close_time được chấp nhận theo cutoff, nhưng không thể chứng minh
Binance đã lấy giá cuối nếu HTTP vượt ranh giới đóng nến. Không sửa fetched_at nguồn.
