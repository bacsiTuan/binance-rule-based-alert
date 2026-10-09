# Frontend

Frontend React + Vite gồm form quản lý rule, danh sách rule và biểu đồ TradingView.
Source được chuyển từ thư mục `frontend/` trên repository sang `FE/`.

## Chạy frontend

Cần Node.js và npm. Mở terminal tại thư mục `FE/`:

```text
npm ci
```

Tạo file cấu hình trên Windows PowerShell:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Trên Linux/macOS:

```bash
if [ ! -f .env ]; then cp .env.example .env; fi
```

Sau đó chạy:

```text
npm run dev
```

Mở URL Vite in trong terminal, mặc định <http://localhost:5173>.

## Cấu hình và phạm vi hiện tại

`FE/.env` mặc định có `VITE_USE_MOCK=true`: dùng dữ liệu rule/symbol mẫu,
lưu rule trong localStorage của trình duyệt và chạy thử UI độc lập với backend.

`VITE_USE_MOCK=false` chọn gọi API qua proxy `/api` trong `vite.config.js`, đích
mặc định `http://localhost:8000`. Chỉ bật khi backend cung cấp đủ API cho frontend.
Backend v1 hiện có `/klines`, `/symbols`, `/health`; CRUD `/rules` chưa có và
response `/symbols` hiện là object có metadata, cần tích hợp thêm trước khi dùng
chế độ API thật cho toàn bộ UI. Sau khi sửa `.env`, khởi động lại Vite.

Build frontend:

```text
npm run build
```

Kết quả nằm trong `FE/dist/`. Lệnh Docker Compose tại thư mục gốc hiện chạy backend
và Redis; frontend được chạy riêng bằng npm như trên.

Backend hiện chạy ở `http://127.0.0.1:8000`; có thể thử API bằng Swagger tại
<http://127.0.0.1:8000/docs>.

Hướng dẫn chạy backend và Redis: [HUONG_DAN_CHAY.md](../HUONG_DAN_CHAY.md).
