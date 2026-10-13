# 📋 Nhật ký tiến độ công việc — Binance Rule Based Alert
*Cập nhật: Rạng sáng ngày 13/10/2026*

---

## ✅ Những việc đã hoàn thành:

1. **Giao diện Frontend (FE)**:
   - Nhúng thành công **TradingView Advanced Chart** chiếm 2/3 diện tích màn hình.
   - Bố cục 1/3 còn lại phân bổ dọc: Form tạo luật ở trên, Danh sách luật ở dưới.
   - Đồng bộ 2 chiều: Đổi coin/timeframe hoặc click vào luật thì biểu đồ TradingView tự nhảy theo.
   - Hỗ trợ đa ngôn ngữ (EN / VI) và Dark/Light mode.

2. **Chạy hệ thống trọn gói qua Docker**:
   - Khởi động thành công 2 container: `api` (FastAPI) và `redis` (Redis 7.4) ở trạng thái **Healthy**.
   - Cổng API: `http://127.0.0.1:8000`.
   - Cổng FE dev: `http://localhost:5173`.

3. **Lưu trữ luật vào Database Redis thật (Phương án 2: Redis Hash + Counter)**:
   - **Backend**:
     - Định nghĩa models: `Rule`, `RuleCreate`, `RuleUpdate` trong `BE/app/models.py`.
     - Xây dựng `RuleStorage` trong `BE/app/rules.py` lưu trữ luật vào Redis hash bền vững (`redis_data` volume), trả về danh sách dạng mảng (ArrayList) cho Frontend.
     - Mở 4 endpoint CRUD trong `BE/app/main.py`: `GET /rules`, `POST /rules`, `PATCH /rules/{id}`, `DELETE /rules/{id}`.
   - **Frontend**:
     - Tạo module `FE/src/api/rulesClient.js` gọi API thật qua proxy `/api`.
     - Cập nhật `FE/src/App.jsx` dùng `createRulesApi`: Tạo, bật/tắt, xóa luật đều được lưu và đồng bộ trực tiếp với Docker Redis.

4. **Tính năng "Create Alert on Mass Index" & Modal Popup chuẩn TradingView (Mới hoàn thành)**:
   - **Nâng cấp UX Modal Popup (Phương án A ⭐)**:
     - Chuyển toàn bộ Form tạo luật thành **Cửa sổ Modal Popup** hiện đại, mờ nền (`backdrop-filter: blur(8px)`), chuẩn 100% phong cách TradingView với tiêu đề `Create alert on (BTCUSDT)`.
     - Nút **`+ Tạo cảnh báo mới`** được đặt nổi bật ở đầu thanh Sidebar và trên thanh tiêu đề `page-heading`.
     - Cột bên phải (1/3 màn hình) được giải phóng hoàn toàn, dành trọn vẹn cho việc quản lý **Danh sách luật đã lưu** và nhật ký tín hiệu.
     - Hỗ trợ đóng modal linh hoạt bằng nút ✕, click ra ngoài nền mờ, hoặc bấm phím `Escape`.
   - **Bổ sung chỉ báo**: Thêm `mass_index` (Mass Index) với chu kỳ mặc định là 10.
   - **Đầy đủ toán tử**: Bổ sung `>=`, `<=`, `>`, `<`, `Cắt lên (crossup / crossing up)`, `Cắt xuống (crossdown / crossing down)`.
   - **Hỗ trợ 2 dạng luật**:
     - `Indicator - operator - value` (ví dụ: `Mass Index (10) cross_above 9.52`).
     - `Indicator - operator - Indicator` (ví dụ: `EMA(12) cross_above EMA(26)`, `SMA(50) cross_above SMA(200)`).
   - **Tùy chọn TradingView**: Thêm cơ chế kích hoạt `trigger_type` (`Once only`, `Once per bar close`, `Every time`) và trường nhập tin nhắn cảnh báo tùy chỉnh `message`.
   - **Đồng bộ thuật ngữ theo Hướng A (Chuẩn TradingView ⭐)**: Thống nhất toàn bộ câu chữ trên giao diện sang chuẩn "Cảnh báo" (*Create alert* / *Active alerts*), loại bỏ hoàn toàn sự nhập nhằng giữa "Luật" và "Cảnh báo", tạo trải nghiệm trực quan và đồng bộ 100%.
   - **Kiểm thử**: Vượt qua toàn bộ 10/10 bài kiểm thử tự động của Frontend (`npm test`).

---

## 📌 Việc cần làm tiếp theo:

1. **Đẩy code lên GitHub**:
   - `git add .`
   - `git commit -m "feat: add tradingview alert modal and mass index options with redis persistence"`
   - `git push origin feat/rules-crud-redis`
   - Mở Pull Request trên GitHub cho các bạn duyệt.
2. **Triển khai Rule Engine & Nút Refresh (Epic 3 & Ticket E4-4)**:
   - Xây dựng logic đánh giá điều kiện (`POST /evaluate`): Quét nến từ Redis/Binance, tính chỉ báo và kiểm tra xem luật nào thỏa mãn (`cross_above`, `gt`,...).
   - Hiển thị danh sách cảnh báo (Triggered Alerts) trực tiếp trên Frontend.
   - (Tùy chọn) Kích hoạt gửi thông báo qua Bot Telegram đã có sẵn trong `BE/app/service/telegram_client.py`.
