# Frontend

Frontend React + Vite gồm form quản lý rule, danh sách rule, biểu đồ TradingView
và bảng chỉ báo tính từ backend qua `POST /indicators`.
Source được chuyển từ thư mục `frontend/` trên repository sang `FE/`.

Giao diện mặc định dùng nền tối. Nút **Sáng/Tối** ở thanh trên đổi giao diện
và đồng bộ nền biểu đồ TradingView; lựa chọn được nhớ trên trình duyệt này.
Bố cục dùng toàn bộ chiều rộng cửa sổ, chừa lề nhỏ và tự xếp lại trên điện thoại.

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

File `FE/.env` dùng cấu hình sau (file `.env` ở gốc dành riêng cho BE):

```dotenv
VITE_USE_MOCK=false
VITE_API_TARGET=http://127.0.0.1:8000
```

- `VITE_USE_MOCK=false` (mặc định): lấy danh sách cặp USDT từ `GET /symbols`
  và tính chỉ báo qua `POST /indicators`. FE đọc trường `symbols` trong response,
  giữ thông báo cache cũ và lỗi backend.
- `VITE_API_TARGET`: địa chỉ backend cho proxy `/api` khi chạy Vite dev/preview.
  Nếu đổi `API_PORT` trong `.env` gốc, sửa cổng này tương ứng. FE chạy trên một
  máy khác với BE thì thay `127.0.0.1` bằng địa chỉ BE mà máy chạy Vite truy cập được.
  Cấu hình mạng và firewall máy BE phải cho phép truy cập cổng API trước khi
  dùng kiểu chạy tách máy.
- `VITE_USE_MOCK=true`: thử UI bằng symbol/rule mẫu, không gọi backend tính chỉ báo.

Nếu trước đó đã có `.env` với `VITE_USE_MOCK=true`, sửa thành `false`.
Khởi động lại Vite sau khi thay cấu hình. Không đặt API key hay mật khẩu vào biến `VITE_*`.

Chạy backend và Redis từ thư mục gốc trước:

```powershell
docker compose up -d --build --wait
```

Sau đó mở terminal tại `FE/`:

```powershell
npm.cmd ci
npm.cmd run dev
```

Khi đổi symbol, timeframe, chỉ báo/chu kỳ hoặc chế độ nến trong form, bảng
**Chỉ báo hiện tại** tự tải kết quả sau 350 ms. Nút **Làm mới** gọi lại API,
vẫn tuân theo TTL của cache Redis. Bảng hiển thị giá trị mới nhất, nguồn dữ liệu,
thời điểm lấy dữ liệu, trạng thái thiếu nến và giá trị tạm thời khi gồm nến chưa đóng.
Giá trị hiển thị tối đa 6 chữ số thập phân; rê chuột lên giá trị để xem chuỗi đầy đủ.
Nếu luật chỉ so sánh giá với một số, bảng mặc định tính SMA(20), EMA(14), RSI(14).

Luật được lưu **trong localStorage của trình duyệt**, không gọi `/rules` vì BE
chưa có CRUD luật hay rule engine. Luật ở chế độ thật và dữ liệu mẫu dùng kho
riêng; bật/tắt chưa chạy kiểm tra điều kiện hoặc gửi cảnh báo tự động.
Biểu đồ TradingView vẫn lấy dữ liệu trực tiếp từ TradingView; các giá trị trong
bảng bên cạnh được tính bởi BE, có thể khác widget do snapshot/chính sách nến.

Giao diện hỗ trợ nền tối/sáng và giữ màu nút xanh ngọc, tự chuyển bố cục theo màn hình.
Ô **Tìm cặp giao dịch** lọc danh sách theo mã (BTC/ETH/SOL…), không tự đổi cặp đang chọn.
Nút **1H / 1D / 1W** trên biểu đồ đồng bộ khung thời gian với form và chỉ báo.
Form có nhãn tiếng Việt, trạng thái lỗi, thông báo lưu thành công và hỗ trợ bàn phím.
TradingView hiển thị trạng thái đang tải; nếu không tải được sau 12 giây, có nút
thử lại và mở TradingView trực tiếp. Lỗi biểu đồ không ngăn FE lấy chỉ báo từ BE.

Proxy này chỉ dùng cho Vite dev/preview. Khi triển khai `FE/dist/` trên web server,
cần cấu hình server chuyển `/api/*` tới BE và bỏ tiền tố `/api`.

Kiểm tra frontend:

```powershell
npm.cmd test
npm.cmd run build
```

Build frontend:

```text
npm run build
```

Kết quả nằm trong `FE/dist/`. Lệnh Docker Compose tại thư mục gốc hiện chạy backend
và Redis; frontend được chạy riêng bằng npm như trên.

Backend hiện chạy ở `http://127.0.0.1:8000`; có thể thử API bằng Swagger tại
<http://127.0.0.1:8000/docs>.

Hướng dẫn chạy backend và Redis: [HUONG_DAN_CHAY.md](../HUONG_DAN_CHAY.md).
