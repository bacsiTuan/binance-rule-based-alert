# Backend

Backend Python FastAPI lấy dữ liệu Binance và lưu cache trong Redis.

```text
BE/
  app/                    Source Python
    main.py               FastAPI
    config.py             Đọc cấu hình .env
    cli.py                Lấy dữ liệu một lần
    binance/client.py     Binance REST client
    cache/redis_cache.py  Cache Redis
    service.py            Luồng cache và fetch
    indicator_models.py   Schema API chỉ báo
    indicators.py         Bộ tính SMA/EMA/RSI Wilder bằng Decimal
  tests/                  Test tự động
  pyproject.toml          Dependency và cấu hình Python
  requirements.lock.txt   Phiên bản dependency đã kiểm thử
  Dockerfile              Build backend container
  .dockerignore           Loại file runtime khỏi Docker build
```

Chạy các lệnh tại **thư mục gốc của repository**, nơi có `compose.yaml` và `.env`:

```text
docker compose up -d --build --wait
```

Docker Compose build backend từ `BE/`. `.env` và cấu hình Redis được quản lý tại
thư mục gốc để giữ cách chạy toàn dự án bằng một lệnh.

Chạy Python local trên Windows PowerShell, cũng tại thư mục gốc:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e "./BE[dev]" -c BE/requirements.lock.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up -d redis
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir BE --reload --host 127.0.0.1 --port 8000
```

Nếu trước đây đã cài editable từ thư mục gốc, chạy lại lệnh `pip install` ở trên
để cập nhật đường dẫn source sang `BE/`. Môi trường `.venv` cũ vẫn dùng được.

Kiểm thử tại thư mục gốc:

```powershell
.\.venv\Scripts\python.exe -m pytest BE/tests -q
.\.venv\Scripts\python.exe -m ruff check --config BE/pyproject.toml BE/app BE/tests
```

Xem [hướng dẫn chạy và cấu hình .env](../HUONG_DAN_CHAY.md) để biết cách thử API,
dùng CLI và xử lý lỗi.

## API chỉ báo

`POST /indicators` nhận danh sách cặp tên–chu kỳ, ví dụ:

```json
{"indicators":[{"name":"sma","period":20},{"name":"sma","period":50},{"name":"ema"},{"name":"rsi"}]}
```

Body này dùng BTCUSDT/1h/300 nến; period mặc định 14. Chu kỳ phải nguyên 1–999;
cặp trùng hoặc body sai trả 422. SMA/EMA cần N nến, RSI Wilder cần N+1;
thiếu dữ liệu trả 200 với `null`/`insufficient_data` riêng từng cặp.

Mặc định lọc nến đóng theo cả thời điểm đánh giá và fetch. Bật `include_open=true`
để dùng nến mở với cờ `provisional`. Kết quả giữ metadata stale của snapshot,
không ghi cache chỉ báo hoặc fetch bù. `fetched_at` không chứng minh tuyệt đối
giá cuối tại ranh giới đóng nến. Yêu cầu nhiều cặp có thể chiếm worker và bộ nhớ lớn;
xem benchmark và giới hạn trong [hướng dẫn nghiệm thu](../specs/001-calculate-indicators/quickstart.md).

Test riêng chỉ báo tại gốc repository:

```sh
.venv/bin/python -m pytest BE/tests/test_indicators.py BE/tests/test_indicators_api.py -q
```

Trên Windows dùng `.venv/Scripts/python.exe`. Test dùng fixture, HTTP mock và
fakeredis, không cần Redis/Binance thật. [Hợp đồng đầy đủ](../specs/001-calculate-indicators/contracts/indicators-api.md)
mô tả schema, lỗi và defaults. CLI market data giữ nguyên; chưa có CLI/UI chỉ báo,
rule engine hoặc gửi cảnh báo.
