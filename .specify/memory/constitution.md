# Hiến chương dự án Binance Rule Based Alert

## Nguyên tắc cốt lõi

### I. Bảo toàn hợp đồng API dữ liệu thị trường

- PHẢI giữ tương thích `GET /klines`, `GET /symbols`, `GET /health`: tham số,
  kiểu dữ liệu, metadata và ý nghĩa mã lỗi đã công bố trong `README.md`.
- `/klines` PHẢI tiếp tục chuẩn hóa symbol thành chữ hoa; hỗ trợ `1h`, `1d`, `1w`;
  limit 1–1000, mặc định 300; mặc định symbol `BTCUSDT`, interval `1h`.
  Nến giữ các trường `open_time`, `close`, `close_time`.
- Response nến PHẢI giữ `market`, `symbol`, `interval`, `source`, `stale`,
  `fetched_at`, `cache_key`, `warning`, `candles`. `/symbols` PHẢI giữ object
  có metadata và danh sách `symbols`, lọc trạng thái `TRADING`, quote asset `USDT`;
  không đổi thành mảng thuần để khớp mock frontend.
- `/health` PHẢI phản ánh Redis và thị trường cấu hình; không được diễn giải thành
  kiểm tra kết nối Binance. API market data public không yêu cầu API key.
- Thay đổi phá vỡ tương thích PHẢI có đặc tả, đánh giá tác động API/CLI/frontend,
  phương án chuyển đổi hoặc phiên bản API mới và test hợp đồng trước khi hợp nhất.

Lý do: API hiện tại là nền tảng tích hợp; tính năng mới không được âm thầm làm sai
cách các bên sử dụng dữ liệu hiện có.

### II. Chính xác về thời gian, giá và thị trường

- `open_time`, `close_time` PHẢI là số nguyên Unix timestamp UTC milliseconds
  xuyên suốt backend, Redis và API. Chuyển sang giây hoặc múi giờ hiển thị chỉ được
  thực hiện tại adapter có quy đổi rõ ràng và test đơn vị thời gian.
- `fetched_at` PHẢI giữ chuỗi UTC ISO 8601 trong JSON theo hợp đồng hiện tại;
  không đổi sang milliseconds do yêu cầu timestamp của nến.
- Giá `close` PHẢI giữ chuỗi thập phân, không qua `float` làm mất độ chính xác
  khi đọc, lưu hoặc trả API. Kiểm tra và tính toán cần độ chính xác PHẢI dùng
  `Decimal` hoặc cơ chế tương đương; không chấp nhận giá âm, NaN hoặc vô cực.
- PHẢI phân biệt Spot và USDⓈ-M Futures trong cấu hình, REST endpoint, cache và
  response. Spot là mặc định; không tự chuyển thị trường hoặc host khi gặp lỗi.
- Nến cuối có thể chưa đóng. Khi bổ sung indicator/rule engine, đặc tả PHẢI xác định
  chính sách nến mở; chế độ chỉ dùng nến đóng PHẢI lọc `close_time < now_utc_ms`.
  Không tự loại nến cuối khỏi API hiện tại.

Lý do: sai đơn vị thời gian, làm tròn giá hoặc trộn thị trường có thể tạo kết quả
phân tích và cảnh báo sai dù dữ liệu vẫn có vẻ hợp lệ.

### III. Cache có thời hạn và dữ liệu cũ minh bạch

- Key nến PHẢI phân biệt market, nguồn API, symbol, interval và limit theo cấu trúc
  `binance:{market}:{origin_hash}:klines:{symbol}:{interval}:{limit}`.
  `origin_hash` giữ quy ước 8 ký tự đầu SHA-256 của base URL đã chuẩn hóa;
  cache symbols cũng PHẢI phân biệt market và nguồn API.
- PHẢI giữ TTL cấu hình được: mặc định nến 60 giây, symbols 3600 giây, bản nến
  dự phòng `{key}:stale` 3600 giây tính từ lần fetch thành công.
  `STALE_TTL_SECONDS` PHẢI lớn hơn `CACHE_TTL_SECONDS`; TTL dự phòng thực tế
  cho từng loại dữ liệu giữ công thức `max(STALE_TTL_SECONDS, ttl_chính + 1)`.
- Cache hit hoặc stale fallback không được gia hạn tuổi dữ liệu hay đổi
  `fetched_at`. Chỉ fetch thành công mới ghi dữ liệu mới và thiết lập lại TTL.
- Timeout, HTTP 5xx hoặc 429/418 chỉ được fallback khi bản dự phòng còn hợp lệ.
  PHẢI trả `source=stale`, `stale=true`, `warning` có nội dung và `fetched_at`
  gốc. Dữ liệu mới dùng `source=binance`; cache còn hạn dùng `source=cache`.
  Bên tiêu thụ PHẢI giữ và xử lý metadata, không trình bày dữ liệu cũ như mới.
- Invalid symbol PHẢI trả HTTP 400, không fallback. Redis không truy cập được
  PHẢI trả HTTP 503; CLI thoát mã 1. Không che lỗi bằng thành công giả.
- PHẢI giữ retry giới hạn với exponential backoff cho timeout/5xx, mặc định tối đa
  3 lần thử; 429/418 không retry ngay, tuân thủ `Retry-After`, mặc định cooldown
  60 giây khi thiếu header.
- PHẢI kiểm tra cache lại trong lock khi refresh đồng thời. Hiện tại chạy một worker
  vì lock/cooldown nằm trong process; nhiều worker PHẢI có cơ chế phối hợp dùng
  chung được kiểm thử trước khi triển khai.

Lý do: TTL và metadata là một phần ngữ nghĩa dữ liệu. Redis có AOF không biến cache
thành kho lịch sử; hết TTL không tự kích hoạt fetch.

### IV. Tái sử dụng kiến trúc hiện tại

- PHẢI giữ ranh giới `BE/` và `FE/`, tận dụng các lớp hiện có: `main.py` quản lý
  FastAPI và vòng đời kết nối, `config.py` quản lý cấu hình, `models.py` định nghĩa
  schema, `binance/client.py` gọi REST, `cache/redis_cache.py` quản lý cache,
  `service.py` điều phối và `cli.py` cung cấp giao diện dòng lệnh.
- Backend PHẢI phát triển từ Python 3.11+, FastAPI, httpx, redis và pydantic-settings
  trong `BE/pyproject.toml`; frontend từ React 18, React DOM và Vite trong
  `FE/package.json`. Thay stack hoặc thêm dependency PHẢI có nhu cầu cụ thể,
  đánh giá tác động và lý do công cụ hiện có không đáp ứng trong kế hoạch.
- API và CLI PHẢI tái sử dụng service; không sao chép logic fetch/cache vào route
  hay component. Chỉ thêm abstraction khi giải quyết nhu cầu đã xác định.
- Khi thay dependency, PHẢI cập nhật manifest và lockfile tương ứng. Giữ cấu hình
  backend ở gốc, frontend ở `FE/`; không đưa bí mật `.env` cá nhân vào source.

Lý do: mở rộng theo ranh giới sẵn có giúp kiểm thử độc lập và tránh nhiều cách
xử lý khác nhau cho cùng một hợp đồng dữ liệu.

### V. Kiểm thử backend độc lập bằng mock

- Test backend tự động PHẢI dùng pytest/pytest-asyncio, HTTP mock như
  `httpx.MockTransport` và fakeredis; không gọi Binance thật, không phụ thuộc hoặc
  xóa Redis thật, không cần API key hay `.env` cá nhân.
- Thay đổi hành vi PHẢI có test liên quan cho đường thành công và lỗi. PHẢI bảo vệ
  schema/validation, độ chính xác giá, UTC milliseconds, phân biệt market/host/
  limit/interval, cache hit/miss và TTL, refresh đồng thời, retry/cooldown,
  stale metadata và tuổi dữ liệu, invalid symbol, lỗi Redis, dữ liệu hỏng,
  và bộ lọc symbols.
- Thay đổi backend PHẢI chạy tại gốc dự án, trong môi trường đã cài dependency:
  `python -m pytest BE/tests -q` và
  `python -m ruff check --config BE/pyproject.toml BE/app BE/tests`.
- Kiểm thử dịch vụ thật PHẢI tách khỏi bộ test tự động và ghi rõ là thủ công;
  không thay thế kiểm thử mock có thể lặp lại bằng kết quả mạng thật.

## Phạm vi hiện tại và hướng phát triển

- **Đã có:** backend lấy dữ liệu Binance theo yêu cầu API/CLI, cache JSON Redis,
  stale fallback, symbols USDT và health Redis. Docker Compose chạy API và Redis.
- **Đã có ở giao diện:** React + Vite với form/danh sách rules và biểu đồ TradingView;
  mặc định dùng mock, rules lưu localStorage. Đây không phải backend rule engine
  hoặc cơ chế lưu rules/alerts dùng chung.
- **Chưa hoàn thiện tích hợp:** toàn bộ frontend với API thật; backend chưa có
  CRUD `/rules`, còn response `/symbols` có metadata cần adapter tích hợp phù hợp.
- **Dự kiến:** indicator SMA/EMA/RSI, rule engine, SQL lưu rules/alerts, kho lịch sử
  dài hạn và worker/scheduler lấy dữ liệu định kỳ. PHẢI có đặc tả, triển khai và
  kiểm thử trước khi công bố đã hoàn thành; không suy ra chức năng từ tên dự án,
  mock UI, dependency hoặc sơ đồ kế hoạch.
- Tài liệu PHẢI viết bằng tiếng Việt, giữ nguyên định danh API/mã và lệnh khi cần;
  PHẢI phân biệt rõ hiện trạng, hạn chế và kế hoạch.

## Quy trình và kiểm tra tuân thủ

1. Trước khi lập đặc tả/kế hoạch, PHẢI đối chiếu `README.md`, `BE/pyproject.toml`,
   `FE/package.json` và mã nguồn liên quan; xác định phần tái sử dụng và phần mới.
2. Đặc tả/kế hoạch PHẢI đánh giá tác động tới API, thời gian/giá, thị trường,
   TTL/stale metadata, kiến trúc và chiến lược kiểm thử mock.
3. PR PHẢI nêu thay đổi hành vi, bằng chứng kiểm thử và hạn chế còn lại.
   Thay đổi frontend PHẢI chạy `npm run build` trong `FE/` và kiểm tra luồng UI
   bị ảnh hưởng. Thay đổi chỉ tài liệu PHẢI kiểm tra tính nhất quán, liên kết,
   phiên bản và placeholder; không bắt buộc chạy test ứng dụng.
4. Người review PHẢI kiểm tra tuân thủ trước khi hợp nhất. Sai lệch PHẢI được sửa
   hoặc đi qua quy trình sửa hiến chương; không được bỏ qua âm thầm.

## Quản trị

Hiến chương là căn cứ ưu tiên cho đặc tả, kế hoạch, tác vụ và review. README và
manifest cung cấp hiện trạng; mâu thuẫn với hiến chương PHẢI được ghi nhận và giải
quyết trước khi hợp nhất thay đổi liên quan.

Đề xuất sửa PHẢI nêu lý do, nguyên tắc ảnh hưởng, tác động tương thích, phương án
chuyển đổi nếu có và bằng chứng kiểm tra. Người bảo trì PHẢI phê duyệt qua review.
Tài liệu phụ thuộc được rà soát trong công việc tiếp theo có liên quan; sửa hiến
chương không tự cho phép triển khai tính năng.

Phiên bản dùng Semantic Versioning: MAJOR khi loại bỏ hoặc định nghĩa lại nguyên
tắc không tương thích; MINOR khi thêm nguyên tắc/mục hoặc mở rộng đáng kể nghĩa vụ;
PATCH khi làm rõ câu chữ mà không đổi nghĩa. Mỗi lần sửa PHẢI cập nhật phiên bản,
ngày sửa và báo cáo tác động; giữ ngày thông qua đầu tiên. Báo cáo tác động ở đầu
file là ghi chú review tạm thời, PHẢI xóa trước khi commit bản đã duyệt.

**Phiên bản**: 1.0.0 | **Ngày thông qua**: 2026-10-11 | **Sửa đổi gần nhất**: 2026-10-11
