# Binance Rule Based Alert — v1

Kế hoạch tổng thể, checklist đã hoàn thành và việc còn lại đến 11/10/2026:
xem [PROJECT_PLAN.md](PROJECT_PLAN.md).

Quy trình phát triển với GitHub Spec Kit và Codex: xem [SPEC_KIT.md](SPEC_KIT.md).

Người mới clone dự án: đọc [Hướng dẫn chạy](HUONG_DAN_CHAY.md) để khởi động backend
và Redis bằng Docker trên Windows, Linux hoặc macOS.

Phần đầu của dự án Python: gọi Binance REST lấy dữ liệu nến và lưu JSON vào Redis.
Mặc định dùng **Spot** theo kế hoạch `prototype-project-plan.docx`; có thể đổi sang
**USDⓈ-M Futures** bằng biến môi trường. Dữ liệu được lấy khi gọi API hoặc CLI.

Source được tách thành [FE/](FE/README.md) cho frontend và [BE/](BE/README.md)
cho backend. `BE/` có code Python; `FE/` có giao diện React + Vite quản lý rules
và biểu đồ TradingView, lấy symbol/chỉ báo từ API thật; luật lưu trong trình duyệt. `compose.yaml`, `.env` của
backend và tài liệu chạy nằm ở thư mục gốc. Cấu hình frontend nằm tại `FE/.env`.

Chạy giao diện bằng `npm ci` rồi `npm run dev` trong `FE/`; xem [README frontend](FE/README.md).

## Chạy toàn bộ bằng Docker trên máy này hoặc máy khác

Cài và mở Docker Desktop (Linux containers) trên Windows/macOS, hoặc Docker Engine
kèm Compose trên Linux. Copy thư mục source sang máy mới hoặc clone repository;
không cần copy `.venv`, `.tmp`, `.idea` hay cài Python/Redis riêng.

Mở terminal tại thư mục có `compose.yaml`. Trên Windows PowerShell:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up -d --build --wait
docker compose ps
```

Trên Linux/macOS, tạo `.env` từ `.env.example` nếu chưa có rồi chạy cùng lệnh Docker.
Lần đầu Docker tải image và dependency nên cần Internet và mất vài phút.
Lệnh sẽ chạy **hai container: API và Redis**, chờ Redis healthy trước khi chạy API.
Đã kiểm thử cách chạy này với API và Redis healthy, 300 nến BTCUSDT được ghi Redis
và lần gọi tiếp theo đọc cache với TTL 60 giây.

Mở <http://127.0.0.1:8000/docs>, thử `GET /klines`, hoặc:

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/health'
Invoke-RestMethod 'http://127.0.0.1:8000/klines?symbol=BTCUSDT&interval=1h&limit=300'
```

CLI trong Docker, không cần Python trên máy:

```powershell
docker compose exec -T api python -m app.cli --symbol BTCUSDT --interval 1h --limit 300
```

Các lệnh quản lý:

```powershell
docker compose logs -f api      # Xem log; Ctrl+C chỉ thoát xem log
docker compose stop            # Dừng API và Redis
docker compose start           # Chạy lại các container đã tạo
docker compose up -d --build --wait  # Dùng sau khi thay code hoặc .env
```

`-d` chạy nền, nên đóng terminal vẫn chạy. Với `restart: unless-stopped`, container
đã tạo được khởi động lại khi Docker engine chạy lại, trừ khi bạn đã chủ động stop.
Để chạy sau khi bật máy, bật tùy chọn mở Docker Desktop khi đăng nhập (hoặc tự khởi
động Docker Engine trên Linux). Khi máy tắt/ngủ hoặc Docker dừng, ứng dụng cũng dừng.

Nếu port 8000 đang bị dùng, đặt `API_PORT=8001` trong `.env`, chạy lại lệnh `up`,
rồi mở <http://127.0.0.1:8001/docs>. Không chạy đồng thời Uvicorn local và Docker API
trên cùng một port. Redis trong container được API truy cập qua `redis://redis:6379/0`;
giá trị `REDIS_URL` trong `.env` dành cho cách chạy Python local bên dưới.

Máy khác chạy bản riêng sẽ có Redis/cache riêng; dữ liệu cũ không tự chuyển theo
source code. Đóng gói source nên loại `.env` cá nhân và dùng `.env.example` trên máy mới.
Nếu muốn máy khác chỉ truy cập backend đang chạy trên máy này, đó là cấu hình mạng
khác: hiện port chỉ bind localhost, nên `127.0.0.1` trên máy khác không trỏ về máy này.

**Tự khởi động ứng dụng và tự lấy dữ liệu là hai việc khác nhau.** Cách Docker trên
chạy API + Redis nền; bản hiện tại vẫn fetch khi gọi `/klines` hoặc CLI. Muốn tự lấy
Binance mỗi N giây dù không ai gọi API thì cần thêm worker/scheduler theo sơ đồ.

## Chạy Python local trên Windows PowerShell

Cần Python 3.11+ và Docker Desktop đang chạy Linux containers.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e "./BE[dev]" -c BE/requirements.lock.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up -d redis
docker compose exec -T redis redis-cli ping
```

Redis trả về `PONG`. Redis dùng volume `redis_data`, bật AOF để giữ dữ liệu sau khi
container restart; key vẫn hết hạn theo TTL. Port 6379 chỉ bind vào localhost.
`BE/requirements.lock.txt` cố định các phiên bản dependency đã dùng khi kiểm thử.
Chạy Python local tại thư mục gốc để ứng dụng đọc đúng `.env`. Nếu đã cài v1 trước
khi tách thư mục, cài lại editable bằng lệnh `pip install` trên để cập nhật source path.

Lấy 300 nến BTCUSDT khung 1 giờ và lưu Redis ngay, không cần chạy web server:

```powershell
.\.venv\Scripts\python.exe -m app.cli --symbol BTCUSDT --interval 1h --limit 300
```

Chạy backend để frontend hoặc Swagger gọi:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir BE --reload --host 127.0.0.1 --port 8000
```

Mở Swagger tại <http://127.0.0.1:8000/docs>.

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/health'
$data = Invoke-RestMethod 'http://127.0.0.1:8000/klines?symbol=BTCUSDT&interval=1h&limit=300'
$data.source
$data.candles | Select-Object -Last 3
Invoke-RestMethod 'http://127.0.0.1:8000/symbols'
```

Gọi lại cùng symbol, interval và limit trong 60 giây sẽ trả `source=cache`, không
gọi Binance. `/health` kiểm tra Redis; endpoint này không kiểm tra kết nối Binance.

## API và dữ liệu

| Endpoint | Chức năng |
| --- | --- |
| `GET /klines?symbol=BTCUSDT&interval=1h&limit=300` | Lấy nến, cache miss gọi Binance và lưu Redis |
| `GET /symbols` | Các symbol đang TRADING và có quote asset USDT, cache 1 giờ |
| `GET /health` | Kiểm tra Redis và thị trường đã cấu hình |
| `POST /indicators` | Tính SMA, EMA, RSI Wilder trên một snapshot nến, giữ metadata nguồn |

Interval được hỗ trợ: `1h`, `1d`, `1w` (chữ thường). Limit: 1–1000, mặc định 300.
Symbol được chuyển thành chữ hoa. Các endpoint market data này không cần API key.

Binance trả nến dạng mảng: phần tử `[0]` là open time, `[4]` là close price,
`[6]` là close time. Backend lưu ba trường cần cho indicator, giữ giá dưới dạng
chuỗi để không mất độ chính xác, timestamp UTC dưới dạng milliseconds.

Ví dụ cấu trúc response (giá và timestamp minh họa):

```json
{
  "market": "spot",
  "symbol": "BTCUSDT",
  "interval": "1h",
  "source": "binance",
  "stale": false,
  "fetched_at": "2026-10-06T00:00:00Z",
  "cache_key": "binance:spot:<origin_hash>:klines:BTCUSDT:1h:300",
  "warning": null,
  "candles": [
    {"open_time": 1000, "close": "62000.12345678", "close_time": 3599999}
  ]
}
```

Nến cuối trong `/klines` có thể chưa đóng và vẫn được giữ nguyên trong response.

## Tính SMA, EMA và RSI Wilder

`POST /indicators` dùng chung luồng Binance/Redis hiện có, không tạo cache chỉ báo,
không tự lấy thêm nến khi thiếu lịch sử. Ví dụ PowerShell:

```powershell
$body = '{"symbol":"BTCUSDT","interval":"1h","limit":300,"indicators":[{"name":"sma","period":20},{"name":"sma","period":50},{"name":"ema","period":14},{"name":"rsi","period":14}]}'
Invoke-RestMethod -Method Post 'http://127.0.0.1:8000/indicators' -ContentType 'application/json' -Body $body
```

Mặc định symbol `BTCUSDT`, interval `1h`, limit 300, period 14, `include_open=false`.
Tên chỉ báo dùng chữ thường `sma`, `ema`, `rsi`; chu kỳ là số nguyên 1–999.
Cho phép nhiều chu kỳ cùng loại, từ chối toàn bộ yêu cầu nếu trùng cặp tên–chu kỳ,
kể cả trùng sau khi áp dụng mặc định. Body sai trả 422 trước khi gọi nguồn.

- SMA là trung bình N giá; EMA khởi tạo bằng SMA(N), hệ số `2/(N+1)`.
- RSI dùng N biến động từ N+1 nến và làm mượt Wilder. Không tăng/giảm cho RSI 50;
  chỉ tăng cho 100, chỉ giảm cho 0.
- SMA/EMA cần N nến, RSI cần N+1. Các điểm chưa đủ dữ liệu có `value=null`,
  `status=insufficient_data`; yêu cầu vẫn trả HTTP 200. Mỗi cặp trả `points`,
  `latest`, `required_candles` và `available_candles`; giá trị là chuỗi thập phân.
- Mặc định chỉ dùng `close_time < min(evaluated_at, fetched_at_UTC_ms)`.
  `include_open=true` cho phép nến mở, gắn `provisional=true` vào điểm phụ thuộc.
  Timestamp nến/evaluated_at là UTC milliseconds; fetched_at vẫn là UTC ISO 8601.
- `source`, `stale`, `warning`, `fetched_at`, `cache_key` giữ từ snapshot nguồn.
  `stale` và `provisional` độc lập; tính lại không làm dữ liệu cũ trở thành mới.
- Snapshot sai trả 502 `invalid_indicator_data`; lỗi Binance/Redis giữ hành vi cũ.
  EMA/RSI khởi tạo lại từ đầu snapshot, nên đổi limit có thể làm kết quả khác.

`fetched_at` là thời điểm backend nhận dữ liệu, không phải thời điểm Binance chụp
giá. Quy tắc lọc không bảo đảm tuyệt đối giá cuối cùng khi HTTP đi qua giờ đóng nến
hoặc đồng hồ lệch. API không tự fetch lại để xác minh trong trường hợp này.

Chỉ yêu cầu các cặp cần dùng: tối đa 2997 cặp × 1000 nến tạo gần 3 triệu điểm.
Benchmark mock trên máy phát triển ghi nhận khoảng 11,52 giây, 357,6 MB response
và 2,96 GB peak RSS; đây không phải SLA hoặc kiểm thử tải production.
Phép tính đồng bộ có thể chiếm worker trong thời gian này.

Xem [hợp đồng API](specs/001-calculate-indicators/contracts/indicators-api.md) và
[kết quả nghiệm thu](specs/001-calculate-indicators/quickstart.md).
Chưa có rule engine, gửi cảnh báo, CLI chỉ báo hoặc tích hợp frontend chỉ báo.

## Redis và xử lý lỗi

Key: `binance:{market}:{origin_hash}:klines:{symbol}:{interval}:{limit}`.
`origin_hash` là 8 ký tự đầu SHA-256 của base URL, tách dữ liệu giữa các API host.
Thêm market và limit vào key để tránh lấy nhầm Futures/Spot hoặc số lượng nến.
Giá trị JSON chứa `candles`, `fetched_at` và metadata như response trên.

- Key chính TTL 60 giây; bản dự phòng `{key}:stale` sống tổng cộng 3600 giây kể từ lần fetch thành công.
- Binance timeout, HTTP 5xx, 429/418: dùng bản dự phòng nếu còn; trả `source=stale`, `stale=true`, `warning` và thời điểm fetch gốc.
- HTTP 429/418: không retry ngay; chặn request Binance trong process theo `Retry-After` (mặc định 60 giây nếu header thiếu).
- Timeout/5xx: tối đa 3 lần thử với exponential backoff. Invalid symbol: trả HTTP 400, không dùng bản dự phòng.
- Redis không truy cập được: trả HTTP 503, CLI thoát với mã 1.
- Refresh đồng thời trong một process: kiểm tra cache lần nữa trong lock để tránh nhiều lần fetch cùng dữ liệu.

Chạy v1 với một worker. Cooldown và lock hiện ở trong process; khi triển khai nhiều
worker cần lock/cooldown dùng chung trong Redis. Không có scheduler: cache hết hạn
không tự gọi API, lần request tiếp theo sẽ fetch lại. Đây là cache tạm, chưa phải kho
lịch sử dài hạn.

Kiểm tra dữ liệu bằng key lấy từ response:

```powershell
docker compose exec -T redis redis-cli --scan --pattern '*:klines:*'
docker compose exec -T redis redis-cli GET $data.cache_key
docker compose exec -T redis redis-cli TTL $data.cache_key
```

Nếu dùng CLI, copy `cache_key` trong JSON output để thay cho `$data.cache_key`.

## Đổi sang Futures hoặc API host khác

Trong `.env`, đổi rồi restart backend/CLI:

```dotenv
BINANCE_MARKET=futures
BINANCE_BASE_URL=
```

Spot dùng `https://api.binance.com/api/v3/klines`; Futures dùng
`https://fapi.binance.com/fapi/v1/klines`. Không dùng SDK Spot cho Futures.
V1 dùng `httpx` gọi REST trực tiếp, thuận tiện kiểm thử lỗi HTTP và quản lý cache.

Với Spot, có thể chọn host chỉ phục vụ dữ liệu public:

```dotenv
BINANCE_MARKET=spot
BINANCE_BASE_URL=https://data-api.binance.vision
```

Không tự chuyển host hoặc thị trường khi có lỗi; response luôn ghi rõ `market`.

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m pytest BE/tests -q
.\.venv\Scripts\python.exe -m ruff check --config BE/pyproject.toml BE/app BE/tests
```

Test tự động dùng mock HTTP và fakeredis, không gọi Binance, không xóa Redis thật.
Bao gồm cache hit/miss, TTL, phân biệt key, refresh đồng thời, timeout, rate limit,
stale fallback, invalid symbol, dữ liệu lỗi, USDT filter và HTTP validation.
Kiểm thử thủ công với Redis thật dùng CLI hoặc các request ở trên.

Đã kiểm thử thực tế Binance Spot với 300 nến BTCUSDT cho từng khung `1h`, `1d`,
`1w`, xác nhận Redis TTL 60 giây và request lần hai trả cache. CLI Futures cũng
đã được kiểm thử với endpoint public thật trong giai đoạn market data trước đây.
Bộ test hiện có 134 trường hợp pass, gồm 17 trường hợp market data cũ và 117
trường hợp chỉ báo/API mới; lần bổ sung chỉ báo dùng mock hoàn toàn.

## Cấu trúc

```text
FE/
  src/                    Giao diện React và API client
  package.json            Dependency và lệnh chạy frontend
  package-lock.json       Phiên bản dependency frontend
  vite.config.js          Cấu hình Vite và proxy API
  .env.example            Cấu hình frontend mẫu
  README.md               Hướng dẫn chạy frontend
BE/
  app/
    main.py               FastAPI và vòng đời HTTP/Redis connections
    config.py             Cấu hình .env
    models.py             Candle và response schema
    indicator_models.py   Schema yêu cầu và kết quả chỉ báo
    indicators.py         Bộ tính Decimal, validation và chính sách nến
    errors.py             Lỗi Binance/Redis
    cli.py                Fetch một lần và lưu Redis
    binance/client.py     Binance REST, retry và cooldown
    cache/redis_cache.py  Redis JSON và TTL
    service.py            Cache hit/miss và stale fallback
  tests/test_market_data.py
  tests/test_indicators.py
  tests/test_indicators_api.py
  pyproject.toml          Dependency và cấu hình Python
  requirements.lock.txt   Phiên bản dependency
  Dockerfile              Build backend trong Docker
  .dockerignore           Cấu hình Docker build context
compose.yaml              Khởi động backend và Redis
.env.example              Cấu hình mẫu cho cả dự án
HUONG_DAN_CHAY.md          Hướng dẫn chạy và cấu hình .env
```

Đã có luồng Binance → Redis và API tính SMA/EMA/RSI Wilder theo yêu cầu.
FE đã kết nối `/symbols` và `/indicators`, hiển thị metadata nguồn và chính sách nến.
Rule engine, gửi cảnh báo và lưu rules/alerts tại backend vẫn thuộc các bước tiếp theo.

Tài liệu tham khảo:

- [Binance Spot market endpoints](https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/rest-api/market)
- [Binance Spot REST và rate limits](https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md)
- [USDⓈ-M Futures quick start](https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/quick-start)
- [SDK Spot chính thức](https://pypi.org/project/binance-sdk-spot/)
- [Docker Compose startup và healthcheck](https://docs.docker.com/compose/how-tos/startup-order/)
