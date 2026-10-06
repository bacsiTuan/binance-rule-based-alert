# Binance Rule Based Alert — v1

Người mới clone dự án: đọc [Hướng dẫn chạy](HUONG_DAN_CHAY.md) để khởi động backend
và Redis bằng Docker trên Windows, Linux hoặc macOS.

Phần đầu của dự án Python: gọi Binance REST lấy dữ liệu nến và lưu JSON vào Redis.
Mặc định dùng **Spot** theo kế hoạch `prototype-project-plan.docx`; có thể đổi sang
**USDⓈ-M Futures** bằng biến môi trường. Dữ liệu được lấy khi gọi API hoặc CLI.

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
.\.venv\Scripts\python.exe -m pip install -e ".[dev]" -c requirements.lock.txt
Copy-Item .env.example .env
docker compose up -d redis
docker compose exec -T redis redis-cli ping
```

Redis trả về `PONG`. Redis dùng volume `redis_data`, bật AOF để giữ dữ liệu sau khi
container restart; key vẫn hết hạn theo TTL. Port 6379 chỉ bind vào localhost.
`requirements.lock.txt` cố định các phiên bản dependency đã dùng khi kiểm thử.

Lấy 300 nến BTCUSDT khung 1 giờ và lưu Redis ngay, không cần chạy web server:

```powershell
.\.venv\Scripts\python.exe -m app.cli --symbol BTCUSDT --interval 1h --limit 300
```

Chạy backend để frontend hoặc Swagger gọi:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
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

Nến cuối có thể chưa đóng. Khi thêm indicator/rule engine, lọc nến theo
`close_time < thời gian hiện tại UTC` nếu muốn chỉ dùng nến đã đóng.

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
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check app tests
```

Test tự động dùng mock HTTP và fakeredis, không gọi Binance, không xóa Redis thật.
Bao gồm cache hit/miss, TTL, phân biệt key, refresh đồng thời, timeout, rate limit,
stale fallback, invalid symbol, dữ liệu lỗi, USDT filter và HTTP validation.
Kiểm thử thủ công với Redis thật dùng CLI hoặc các request ở trên.

Đã kiểm thử thực tế Binance Spot với 300 nến BTCUSDT cho từng khung `1h`, `1d`,
`1w`, xác nhận Redis TTL 60 giây và request lần hai trả cache. CLI Futures cũng
đã được kiểm thử với endpoint public thật. Bộ test tự động có 17 trường hợp pass.

## Cấu trúc

```text
app/
  main.py                 FastAPI và vòng đời HTTP/Redis connections
  config.py               Cấu hình .env
  models.py               Candle và response schema
  errors.py               Lỗi Binance/Redis
  cli.py                  Fetch một lần và lưu Redis
  binance/client.py       Binance REST, retry và cooldown
  cache/redis_cache.py    Redis JSON và TTL
  service.py              Cache hit/miss và stale fallback
tests/test_market_data.py
compose.yaml              Redis Docker
Dockerfile                Python backend trong Docker
```

V1 này hoàn thiện bước Binance → Redis. Indicator SMA/EMA/RSI, rule engine,
SQL lưu rules/alerts và frontend sẽ được thêm ở các bước tiếp theo.

Tài liệu tham khảo:

- [Binance Spot market endpoints](https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/rest-api/market)
- [Binance Spot REST và rate limits](https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md)
- [USDⓈ-M Futures quick start](https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/quick-start)
- [SDK Spot chính thức](https://pypi.org/project/binance-sdk-spot/)
- [Docker Compose startup và healthcheck](https://docs.docker.com/compose/how-tos/startup-order/)
