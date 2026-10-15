# Frontend

Frontend React + Vite gồm form quản lý rule, danh sách rule, biểu đồ TradingView
và bảng chỉ báo tính từ backend qua `POST /indicators`.
Source được chuyển từ thư mục `frontend/` trên repository sang `FE/`.

Giao diện mặc định dùng nền tối. Nút **Sáng/Tối** ở thanh trên đổi giao diện
và đồng bộ nền biểu đồ TradingView; lựa chọn được nhớ trên trình duyệt này.
Bố cục dùng toàn bộ chiều rộng cửa sổ, chừa lề nhỏ và tự xếp lại trên điện thoại.

Website hỗ trợ **English / Tiếng Việt**, mặc định **English**. Chọn **EN / VI**
ở thanh trên để đổi ngôn ngữ; lựa chọn được nhớ trên trình duyệt này. Nhãn,
luật mẫu, mô tả luật, lỗi form, thông báo và ngày giờ thay đổi theo ngôn ngữ.
TradingView cũng đổi ngôn ngữ tương ứng. Đổi ngôn ngữ giữ nguyên dữ liệu form và luật đã lưu.

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

Luật dùng CRUD `/rules` và lưu **Redis** khi `VITE_USE_MOCK=false`.
Chỉ chế độ mock mới lưu rule trong localStorage. Scheduler Telegram kiểm tra các
rule được hỗ trợ khi `TELEGRAM_ENABLED=true`; bật rule không tự gửi ngay.
Nút **Check all rules / Kiểm tra tất cả luật** yêu cầu xác nhận, kiểm tra các rule
đang bật và gửi tin cho điều kiện đúng. Nó không bật tất cả rule.
Tin thủ công dùng cùng định dạng với tin theo lịch, kèm AI khi sẵn sàng. Gửi thủ công không thay đổi
trạng thái chống trùng của scheduler, vì vậy cảnh báo theo lịch vẫn có thể gửi riêng.
Nút này cần watcher đang bật, `TELEGRAM_TEST_ENABLED=true` và khóa trong `.env` gốc;
Vite tự nhận khóa cho dashboard local. Xem [AI_ASSISTANT.md](../AI_ASSISTANT.md).

Chatbot AI mở ở góc dưới bên phải. Mục nhỏ **Connection check / Kiểm tra kết nối**
ở cuối khung chat gửi thử một phân tích AI độc lập với rule, dùng được khi watcher tắt.

Chạy bản build với proxy API bằng `npm.cmd start` trong `FE/`: lệnh build rồi
chạy Vite preview, mặc định port 5173 hoặc `PORT` của môi trường chạy.
Nếu truy cập bằng domain, thêm domain cụ thể vào `VITE_ALLOWED_HOSTS` trong `FE/.env`.
Phần gửi thủ công tự nhận khóa chỉ hoạt động qua localhost/127.0.0.1 trên máy chạy Vite.

Biểu đồ TradingView vẫn lấy dữ liệu trực tiếp từ TradingView; các giá trị trong
bảng bên cạnh được tính bởi BE, có thể khác widget do snapshot/chính sách nến.

Giao diện hỗ trợ nền tối/sáng và giữ màu nút xanh ngọc, tự chuyển bố cục theo màn hình.
Ô **Tìm cặp giao dịch** lọc danh sách theo mã (BTC/ETH/SOL…), không tự đổi cặp đang chọn.
Nút **1H / 1D / 1W** trên biểu đồ đồng bộ khung thời gian với form và chỉ báo.
Form có nhãn Anh/Việt, trạng thái lỗi, thông báo lưu thành công và hỗ trợ bàn phím.
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
