# Hướng dẫn chạy Binance Rule Based Alert v1

Tài liệu này dành cho người vừa clone hoặc tải dự án về máy. Cách chạy chính dùng
Docker để khởi động **FastAPI backend và Redis**, không cần cài Python hay Redis riêng.

V1 lấy dữ liệu nến từ Binance khi gọi API hoặc CLI, lưu vào Redis và dùng lại cache
trong 60 giây. Backend hiện chưa có indicator, rule engine hoặc worker tự fetch theo lịch.
Source backend nằm trong `BE/`; `FE/` có giao diện React + Vite với dữ liệu rule mock.
Docker Compose chạy backend và Redis. Để chạy giao diện, xem [README frontend](FE/README.md).

## 1. Chuẩn bị

- Windows/macOS: cài và mở Docker Desktop. Trên Windows, chọn Linux containers.
- Linux: cài Docker Engine và Docker Compose plugin.
- Có Internet để tải image/dependency lần đầu và gọi Binance.
- Có Git nếu muốn clone; cũng có thể tải ZIP source rồi giải nén.

Kiểm tra trong terminal:

```text
docker --version
docker compose version
docker info
```

`docker info` phải hiển thị thông tin Server. Nếu báo không kết nối được Docker
daemon/engine, mở Docker Desktop và chờ engine chạy rồi thử lại.

## 2. Lấy source và tạo cấu hình

Lấy URL clone từ repository, thay `URL_REPOSITORY` trong lệnh dưới bằng URL đó:

```text
git clone URL_REPOSITORY binance-rule-based-alert
cd binance-rule-based-alert
```

Nếu tải ZIP, giải nén và mở terminal trong thư mục gốc có `compose.yaml`, `BE/`,
`FE/` và `.env.example`. Các lệnh bên dưới đều chạy tại thư mục này.

Tạo `.env` lần đầu trên **Windows PowerShell**:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Trên **Linux/macOS**:

```bash
if [ ! -f .env ]; then cp .env.example .env; fi
```

Cấu hình mặc định dùng Binance Spot, API ở port 8000. Có thể giữ nguyên `.env`
để chạy thử. Không cần Binance API key cho các endpoint dữ liệu thị trường này.
`.env` là cấu hình riêng từng máy, đã được loại khỏi Git; repository giữ `.env.example`.

## 3. Khởi động bằng một lệnh

Lệnh giống nhau trên Windows, Linux và macOS:

```text
docker compose up -d --build --wait
```

Lần đầu có thể mất vài phút. Docker build môi trường Python, chạy Redis, đợi Redis
healthy rồi chạy backend. `-d` chạy nền, nên đóng terminal vẫn giữ ứng dụng chạy.

Kiểm tra:

```text
docker compose ps
```

Kết quả cần có hai service `api` và `redis`, trạng thái `Up` và `healthy`.

## 4. Thử lấy dữ liệu

Mở Swagger trong trình duyệt: <http://127.0.0.1:8000/docs>.

1. Chọn `GET /health` → **Try it out** → **Execute**. Kết quả có `status: "ok"` và `redis: "ok"`.
2. Chọn `GET /klines` → **Try it out**.
3. Nhập `symbol=BTCUSDT`, `interval=1h`, `limit=300`, rồi **Execute**.
4. Gọi lại cùng tham số trong 60 giây: `source` sẽ là `cache`.

Cũng có thể mở trực tiếp:

- [Kiểm tra ứng dụng](http://127.0.0.1:8000/health)
- [Lấy 300 nến BTCUSDT](http://127.0.0.1:8000/klines?symbol=BTCUSDT&interval=1h&limit=300)
- [Danh sách cặp USDT đang giao dịch](http://127.0.0.1:8000/symbols)

Interval hỗ trợ: `1h`, `1d`, `1w` (chữ thường). Limit: 1–1000, mặc định 300.
Mỗi nến có `open_time`, `close`, `close_time`. Timestamp là UTC milliseconds,
giá `close` là chuỗi để giữ độ chính xác. Nến cuối có thể chưa đóng.

`source=binance` nghĩa là dữ liệu vừa được fetch; `source=cache` là dữ liệu từ Redis.
Khi Binance gặp lỗi tạm thời và Redis còn bản dự phòng, response có `source=stale`,
`stale=true`, `warning` và `fetched_at` gốc để nhận biết dữ liệu cũ.

Lấy dữ liệu bằng CLI trong container:

```text
docker compose exec -T api python -m app.cli --symbol BTCUSDT --interval 1h --limit 300
```

## 5. Dừng, chạy lại và cập nhật

| Việc cần làm | Lệnh |
| --- | --- |
| Xem trạng thái | `docker compose ps` |
| Xem log backend | `docker compose logs -f api` |
| Xem log Redis | `docker compose logs -f redis` |
| Dừng ứng dụng | `docker compose stop` |
| Chạy lại container đã tạo | `docker compose start` |
| Áp dụng code hoặc `.env` mới | `docker compose up -d --build --wait` |

Khi xem log, `Ctrl+C` chỉ thoát xem log. `stop` giữ container và volume Redis.
Redis có AOF và volume riêng để giữ dữ liệu sau restart; các key vẫn hết hạn theo TTL.

Sau khi lấy code mới bằng `git pull`, chạy lại lệnh `up -d --build --wait` để build
và cập nhật backend. `docker compose start` chỉ chạy lại container cũ, không build code mới.

Compose có `restart: unless-stopped`. Các container đã tạo sẽ chạy lại khi Docker
engine chạy lại, trừ khi đã chủ động stop. Nếu muốn khởi động sau khi bật máy,
cấu hình Docker Desktop mở khi đăng nhập, hoặc Docker Engine tự khởi động trên Linux.
Ứng dụng chỉ hoạt động khi máy và Docker đang chạy.

## 6. Hướng dẫn cấu hình file .env

### Tạo và mở file

`.env.example` là file mẫu được push lên repository. Sau khi clone, tạo `.env`
theo mục 2 và đặt ngay tại thư mục gốc, cùng cấp với `compose.yaml`:

```text
binance-rule-based-alert/
  .env
  .env.example
  compose.yaml
  BE/
    Dockerfile
    app/
    tests/
    pyproject.toml
    requirements.lock.txt
  FE/
    src/
    package.json
    .env.example
    README.md
```

Mở `.env` bằng VS Code, trình soạn thảo của IDE hoặc Notepad. Trên Windows:

```powershell
notepad .env
```

Lưu dưới dạng văn bản UTF-8, tên chính xác là `.env`, không phải `.env.txt`.
Mỗi dòng có dạng `TEN_BIEN=gia_tri`; dòng bắt đầu bằng `#` là chú thích.
Chỉ cần dùng cấu hình mẫu dưới đây để chạy thử Spot với Docker:

```dotenv
BINANCE_MARKET=spot
BINANCE_BASE_URL=
BINANCE_TIMEOUT_SECONDS=10
BINANCE_MAX_ATTEMPTS=3
REDIS_URL=redis://localhost:6379/0
CACHE_TTL_SECONDS=60
STALE_TTL_SECONDS=3600
SYMBOLS_TTL_SECONDS=3600
LOG_LEVEL=INFO
API_PORT=8000
```

V1 chỉ lấy dữ liệu public, nên không cần thêm `BINANCE_API_KEY` hay `BINANCE_API_SECRET`.
Giữ `.env` riêng trên từng máy; khi chia sẻ/push dự án, dùng `.env.example` làm mẫu.

### Ý nghĩa từng biến

| Biến | Mặc định | Ý nghĩa và giá trị hợp lệ |
| --- | --- | --- |
| `BINANCE_MARKET` | `spot` | `spot` hoặc `futures` (USDⓈ-M Futures) |
| `BINANCE_BASE_URL` | Để trống | Tự chọn `https://api.binance.com` cho Spot hoặc `https://fapi.binance.com` cho Futures; nếu tự đặt, chỉ ghi host, không thêm `/api/v3` hoặc `/fapi/v1` |
| `BINANCE_TIMEOUT_SECONDS` | `10` | Timeout mỗi request Binance, đơn vị giây, phải lớn hơn 0 |
| `BINANCE_MAX_ATTEMPTS` | `3` | Tổng số lần thử tối đa, gồm lần đầu, từ 1 đến 5; retry cho lỗi mạng/HTTP 5xx, không retry ngay HTTP 429/418 |
| `REDIS_URL` | `redis://localhost:6379/0` | Địa chỉ Redis khi chạy Python local; `/0` là database số 0; Compose đặt riêng `redis://redis:6379/0` cho backend trong container |
| `CACHE_TTL_SECONDS` | `60` | Thời gian giữ cache nến mới, đơn vị giây, số nguyên ít nhất 1 |
| `STALE_TTL_SECONDS` | `3600` | Tổng thời gian giữ bản nến dự phòng kể từ lần fetch thành công, đơn vị giây; phải lớn hơn `CACHE_TTL_SECONDS` |
| `SYMBOLS_TTL_SECONDS` | `3600` | Thời gian cache danh sách symbol USDT, đơn vị giây, số nguyên ít nhất 1 |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING` hoặc `ERROR`, viết hoa; dùng `DEBUG` khi cần xem log chi tiết |
| `API_PORT` | `8000` | Port backend trên máy host khi dùng Docker, chọn port trống từ 1 đến 65535; không thay đổi port Redis |

TTL chỉ quy định lúc cache hết hạn. Đặt `CACHE_TTL_SECONDS=60` không có nghĩa
ứng dụng tự gọi Binance mỗi 60 giây; lần gọi API/CLI tiếp theo sau khi hết hạn
mới fetch dữ liệu mới.

### Ví dụ thay đổi cấu hình

**Chuyển sang Futures:** sửa hai dòng sau, giữ các dòng khác:

```dotenv
BINANCE_MARKET=futures
BINANCE_BASE_URL=
```

Khi đổi market, để trống `BINANCE_BASE_URL` để chương trình chọn đúng host.
Dữ liệu Spot và Futures được lưu bằng các key Redis khác nhau.

**Dùng host dữ liệu public khác cho Spot:**

```dotenv
BINANCE_MARKET=spot
BINANCE_BASE_URL=https://data-api.binance.vision
```

Host này dành cho Spot; không dùng cấu hình đó với `BINANCE_MARKET=futures`.

**Port API 8000 đang bận:**

```dotenv
API_PORT=8001
```

Sau khi áp dụng, mở <http://127.0.0.1:8001/docs>. Redis vẫn dùng port 6379.

**Tăng thời gian cache nến lên 120 giây:**

```dotenv
CACHE_TTL_SECONDS=120
STALE_TTL_SECONDS=3600
```

Các key đang có vẫn giữ TTL đã được đặt trước đó; cấu hình mới áp dụng khi ghi
cache mới sau lần fetch tiếp theo.

### Phân biệt Docker và Python local

Khi dùng **Docker Compose**, giữ `REDIS_URL=redis://localhost:6379/0` trong `.env`
cũng được: `compose.yaml` đặt backend trong container dùng `redis://redis:6379/0`.
Tên `redis` được phân giải trong mạng Docker; `localhost` bên trong container là
chính container đó.

Khi chạy **Python local**, cài backend bằng `pip install -e "./BE[dev]" -c BE/requirements.lock.txt`
từ thư mục gốc theo [README backend](BE/README.md). Luôn chạy Uvicorn hoặc CLI tại
thư mục gốc để ứng dụng đọc đúng `.env`. Nếu đã cài bản cũ trước khi tách `FE/BE/`,
chạy lại lệnh cài editable để cập nhật đường dẫn source.

Khi chạy **Python local** bằng Uvicorn hoặc CLI trên máy host, ứng dụng đọc
`REDIS_URL` từ `.env`. Nếu Redis Docker được publish ở port 6379 thì dùng:

```dotenv
REDIS_URL=redis://localhost:6379/0
```

Nếu đã đổi port Redis trên host thành 6380 như mục 7, Python local cần:

```dotenv
REDIS_URL=redis://localhost:6380/0
```

`API_PORT` chỉ được Docker Compose sử dụng. Khi chạy Python local, chọn port
trong lệnh Uvicorn, ví dụ `--port 8001`; CLI không mở HTTP port.

### Áp dụng sau khi sửa

Lưu `.env`, rồi chạy lại trên Docker:

```text
docker compose config --quiet
docker compose up -d --build --wait
docker compose ps
```

`docker compose config --quiet` kiểm tra cấu hình Compose. Nếu backend không
healthy, xem `docker compose logs --tail=100 api` để tìm lỗi giá trị biến hoặc TTL.
`docker compose restart` không cập nhật các biến môi trường đã thay đổi; dùng
lệnh `up` ở trên để Compose tạo lại container khi cần.

Nếu chạy Python local, dừng Uvicorn bằng `Ctrl+C` rồi khởi động lại, hoặc chạy lại
CLI. Việc sửa `.env` không tự cập nhật cấu hình của process đang chạy.

Biến môi trường đã đặt trong terminal có thể ghi đè giá trị cùng tên trong `.env`.
Ví dụ, nếu trước đó đặt `$env:BINANCE_MARKET='futures'` trong PowerShell, sửa `.env`
thành `spot` vẫn có thể bị ghi đè. Xóa biến của terminal nếu muốn dùng lại file:

```powershell
Remove-Item Env:BINANCE_MARKET -ErrorAction SilentlyContinue
```

## 7. Xử lý lỗi thường gặp

### Không kết nối được Docker engine

Mở Docker Desktop, chờ engine chạy và kiểm tra lại `docker info`. Trên Windows,
xác nhận đang dùng Linux containers. Nếu Docker Desktop báo lỗi khởi động riêng,
khắc phục lỗi đó trước khi chạy Compose.

### Port 8000 đã được sử dụng

Đổi `API_PORT=8001` trong `.env`, chạy lại lệnh `up` rồi mở
<http://127.0.0.1:8001/docs>. Không chạy Uvicorn local cùng port với Docker API.

### Port 6379 đã được sử dụng

Nếu Redis khác đang dùng port 6379, có thể đổi mapping của service `redis` trong
`compose.yaml` thành `127.0.0.1:6380:6379`, rồi chạy lại lệnh `up`. API trong container
vẫn kết nối `redis:6379`; chỉ port truy cập Redis từ máy host đổi thành 6380.

### Backend trả HTTP 503 hoặc service chưa healthy

Kiểm tra trạng thái và log:

```text
docker compose ps
docker compose logs --tail=100 api redis
docker compose exec -T redis redis-cli ping
```

Redis hoạt động sẽ trả `PONG`. Nếu cấu hình TTL sai, sửa `.env` theo mục 6 rồi chạy lại.

### Binance trả lỗi

- Invalid symbol: dùng symbol như `BTCUSDT`, hoặc chọn từ `GET /symbols`.
- HTTP 429/418: đợi hết thời gian `Retry-After` rồi thử lại.
- Timeout/lỗi mạng: kiểm tra Internet và log backend.
- Với Spot, nếu host mặc định không truy cập được, có thể thử
  `BINANCE_BASE_URL=https://data-api.binance.vision` trong `.env`, rồi chạy lại lệnh `up`.

### Mang source sang máy khác

Lặp lại các bước 1–4 trên máy mới. Không copy `.venv`, `.tmp` hoặc dữ liệu Docker
runtime; mỗi máy tự build môi trường và có cache Redis riêng. `127.0.0.1` luôn là
máy đang mở trình duyệt. Cấu hình hiện tại chỉ phục vụ localhost, nên máy khác phải
chạy bản riêng để dùng các URL trong hướng dẫn này.

## 8. Tài liệu thêm

- [README dự án](README.md): cấu trúc code, cách chạy Python local và kiểm thử.
- [README frontend](FE/README.md): chạy React + Vite và cấu hình `FE/.env`.
- [Docker Compose startup và healthcheck](https://docs.docker.com/compose/how-tos/startup-order/).
- [Binance Spot REST API](https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md).
