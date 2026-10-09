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
