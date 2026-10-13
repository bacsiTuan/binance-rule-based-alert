# 📖 BẢN GIẢI THÍCH CHI TIẾT TOÀN DIỆN DỰ ÁN
## Đề tài: Rule-Based Indicator Alert System for Binance Market Data (PPR501)

> *Tài liệu này được biên soạn để lưu trữ vĩnh viễn ngữ cảnh dự án, kiến trúc hệ thống, tiến độ công việc và toàn bộ các cuộc thảo luận kỹ thuật. Khi chuyển sang máy tính mới, chỉ cần mở file này là bạn hoặc trợ lý AI có thể nắm trọn vẹn toàn bộ dự án từ A đến Z.*

---

## 1. Mục tiêu và Bản chất của Dự án

### Dự án này là gì?
Đây là một **hệ thống cảnh báo kỹ thuật theo luật (Rule-Based Alert)** cho dữ liệu thị trường tiền mã hóa của sàn Binance trên các khung thời gian: **1 giờ (1h), 1 ngày (1D), 1 tuần (1W)**.

### Kịch bản sử dụng thực tế:
1. **Người dùng thiết lập luật** trên giao diện:
   - *Ví dụ 1*: "Khi RSI(14) cắt lên mức 30 trên khung 1D của BTCUSDT" (tín hiệu bắt đáy quá bán).
   - *Ví dụ 2*: "Khi đường SMA(50) cắt lên đường SMA(200) của ETHUSDT" (Golden Cross - tín hiệu tăng giá dài hạn).
2. **Hệ thống xử lý**:
   - Dữ liệu nến được tải từ Binance REST API, lưu đệm vào bộ nhớ tạm **Redis** (thời gian sống TTL 60 giây để chống bị sàn chặn IP / Rate limit).
   - Các chỉ báo kỹ thuật (SMA, EMA, RSI theo công thức làm mượt Wilder chuẩn TradingView) được tính toán trên giá đóng cửa (`close`).
   - Bộ máy so sánh điều kiện (`gt`, `lt`, `cross_above`, `cross_below`) kiểm tra nến gần nhất hoặc các nến vừa qua.
3. **Kích hoạt cảnh báo**:
   - Luật và lịch sử cảnh báo được lưu trữ an toàn trong Database (Redis persistent volume trên Docker).
   - Cảnh báo hiển thị trực tiếp trên giao diện Frontend và có thể bắn tin nhắn tự động về ứng dụng **Telegram Bot**.

---

## 2. Kiến trúc Hệ thống (Monorepo: Backend + Frontend + Docker)

```text
                  +----------------------------------------------+
                  |         Giao diện người dùng (Frontend)      |
                  |     - 2/3 diện tích: TradingView Chart       |
                  |     - 1/3 diện tích: Form tạo luật & List    |
                  |     - Bảng giá trị chỉ báo & Đa ngôn ngữ EN/VI|
                  +----------------------+-----------------------+
                                         |
                       HTTP API Requests | (Proxy qua Vite /api)
                                         v
                  +----------------------------------------------+
                  |          FastAPI Backend (Docker Container)  |
                  |  - GET /symbols : Danh sách coin             |
                  |  - GET /klines  : Lấy nến giá từ Binance     |
                  |  - POST /indicators : Tính toán chỉ báo      |
                  |  - CRUD /rules  : Quản lý luật giao dịch     |
                  |  - Telegram & OpenAI Clients                 |
                  +----------------------+-----------------------+
                                         |
                         Đọc / Ghi Cache | & Lưu trữ luật bền vững
                                         v
                  +----------------------------------------------+
                  |          Redis Server (Docker Container)     |
                  |  - Cache nến 60s (Stale fallback 1 giờ)      |
                  |  - Hash lưu luật `app:rules`                 |
                  |  - Volume `redis_data` lưu trên ổ cứng       |
                  +----------------------------------------------+
```

---

## 3. Cấu trúc Thư mục Chi tiết trong Kho Code

- `binance-rule-based-alert/`
  - `compose.yaml`: File Docker Compose điều phối khởi động cả Backend và Redis chỉ bằng 1 lệnh.
  - `HUONG_DAN_CHAY.md`: Hướng dẫn vận hành Docker và xử lý sự cố.
  - `PROJECT_PLAN.md`: Kế hoạch và checklist tiến độ 3 tuần.
  - `BE/` *(Backend)*:
    - `Dockerfile`: Đóng gói môi trường Python 3.13-slim.
    - `app/main.py`: Điểm khởi chạy FastAPI, cấu hình CORS, vòng đời lifespan và tất cả API endpoints.
    - `app/models.py`: Định nghĩa schemas Pydantic cho Klines, Symbols, Rule, Indicator, TargetIndicator.
    - `app/rules.py`: Lớp `RuleStorage` thao tác CRUD trực tiếp với Redis.
    - `app/indicators.py`: Thuật toán tính toán chỉ báo SMA, EMA, RSI Wilder.
    - `app/service/binance_client.py`: Client gọi API sàn Binance có retry và xử lý lỗi mạng.
    - `app/service/telegram_client.py`: Module gửi cảnh báo về Telegram.
    - `app/service/open_ai_client.py`: Tích hợp AI phân tích tín hiệu.
    - `tests/`: Bộ kiểm thử tự động pytest.
  - `FE/` *(Frontend)*:
    - `index.html`: Cấu hình SEO và font Inter, JetBrains Mono.
    - `vite.config.js`: Cấu hình proxy `/api` chuyển tiếp sang Backend cổng 8000.
    - `src/App.jsx`: Component gốc điều phối trạng thái, kết nối API và bố cục.
    - `src/components/TradingViewWidget.jsx`: Nhúng biểu đồ TradingView Advanced Chart của Binance.
    - `src/components/RuleForm.jsx`: Form tạo luật trực quan, chọn 10 luật mẫu, validation chặt chẽ.
    - `src/components/RuleList.jsx`: Danh sách luật có bật/tắt (toggle) và xóa, bấm vào để đổi chart.
    - `src/components/IndicatorPanel.jsx`: Bảng hiển thị giá trị chỉ báo hiện tại của coin đang xem.
    - `src/api/rulesClient.js`: Client gửi request HTTP CRUD `/api/rules` lên server FastAPI.
    - `src/i18n.js` & `LanguageContext.jsx`: Cơ chế đa ngôn ngữ (EN mặc định / VI).
    - `src/index.css`: Toàn bộ CSS Dark mode, Glassmorphism, Responsive.

---

## 4. Hướng dẫn Chạy khi sang Máy tính Mới

Khi sang máy mới, bạn chỉ cần làm theo 3 bước:

### Bước 1: Khởi động Backend & Redis
1. Cài đặt và mở **Docker Desktop**.
2. Mở terminal tại thư mục dự án và chạy:
   ```bash
   cp .env.example .env
   docker compose up -d --build --wait
   ```
3. Kiểm tra tại: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### Bước 2: Khởi động Frontend
1. Mở terminal trong thư mục `FE`:
   ```bash
   cd FE
   cp .env.example .env
   npm install
   npm run dev
   ```
2. Mở trình duyệt tại: **`http://localhost:5173`** (hoặc `5174`).

---

## 5. Lộ trình Công việc Tiếp theo

1. **Rule Evaluator (`POST /evaluate`)**: Viết logic để khi người dùng bấm nút **Refresh**, hệ thống quét nến, tính chỉ báo và trả về danh sách các luật đã kích hoạt (`Triggered Alerts`).
2. **Bảng Alert Panel trên Frontend**: Hiển thị popup hoặc danh sách các cảnh báo vừa nổ ra.
3. **Bắn thông báo Telegram**: Kích hoạt hàm gửi tin nhắn từ `BE/app/service/telegram_client.py`.
