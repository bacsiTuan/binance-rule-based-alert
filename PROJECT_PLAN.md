# Kế hoạch dự án Binance Rule Based Alert

**Cập nhật: 11/10/2026 — múi giờ Asia/Saigon.**

Đây là kế hoạch tổng thể và checklist tiến độ dựa trên source hiện tại trong
workspace, tài liệu đặc tả chỉ báo và bản `prototype-project-plan.docx` ban đầu.
Các phần mở rộng bên dưới là đề xuất cho bước tiếp theo, chưa phải tính năng đã có.

Trạng thái dựa trên source của nhánh làm việc tại ngày cập nhật, gồm cả phần
English / Tiếng Việt. Hoàn thành trong source không đồng nghĩa đã review/merge
vào `main`; bản checkout khác có thể chưa có đủ các task được đánh dấu ở đây.

## 1. Mục tiêu và phạm vi

Người dùng chọn cặp Binance và khung thời gian, tạo một điều kiện dựa trên giá
đóng cửa hoặc SMA/EMA/RSI, rồi bấm Refresh để kiểm tra điều kiện và xem cảnh báo.
Dữ liệu nến dùng Redis làm cache; luật và lịch sử cảnh báo sẽ lưu SQL.

Theo bảng kế hoạch 3 tuần được cung cấp thêm ngày 11/10/2026, mục tiêu bắt buộc
còn gồm cập nhật tự động cho tối thiểu 5 symbols và tối thiểu 5 loại indicator.
Bảng này mở rộng phạm vi so với tài liệu prototype ban đầu chỉ lấy theo yêu cầu
và tính SMA/EMA/RSI. Dùng các tiêu chí của bảng 3 tuần để đánh giá tiến độ dưới đây.

Prototype ưu tiên:

- Binance Spot; backend đã có thêm cấu hình USDⓈ-M Futures cho dữ liệu thị trường.
- Tự cập nhật dữ liệu tối thiểu 5 symbols theo lịch; realtime là lựa chọn thay thế.
- Khung `1h`, `1d`, `1w`; giá đóng cửa là đầu vào tính chỉ báo.
- Một luật có một điều kiện; so sánh với số hoặc chỉ báo khác.
- Chọn chỉ nến đóng hoặc gồm nến đang chạy, hiển thị rõ tín hiệu tạm thời.
- Tối thiểu 5 loại indicator: SMA, EMA, RSI, MACD và Bollinger Bands.
- Kiểm tra theo yêu cầu và hiển thị cảnh báo trên FE.
- SQLite trước; thiết kế để có thể chuyển PostgreSQL.

Worker cập nhật theo lịch cần đưa vào phạm vi bắt buộc theo bảng 3 tuần mới nhận.
WebSocket vẫn có thể hoãn vì cập nhật định kỳ đã đáp ứng lựa chọn trong Week 1.
Thông báo ngoài FE và AI trend Up/Down/Sideway là Optional của Week 3;
backtest và đặt lệnh giao dịch không thuộc phần bắt buộc.

## 2. Cách đọc checklist

- `[x]`: đã có trong source/tài liệu hiện tại với phạm vi mô tả trong task.
- `[ ]`: chưa hoàn thành; gồm tính năng thiếu, lỗi đã ghi nhận hoặc nghiệm thu chưa làm.
- `P1`: ưu tiên tiếp theo hoặc điều kiện để prototype hoạt động đầy đủ.
- `P2`: hoàn thiện trải nghiệm, chất lượng và vận hành.
- `P3`: mở rộng sau prototype; có thể hoãn.

Hoàn thành giao diện không có nghĩa đã có luồng backend tương ứng. Ví dụ:
form tạo luật và bật/tắt hiện hoạt động với localStorage, chưa có rule engine.
Chỉ đánh dấu task sau khi đủ tiêu chí nghiệm thu; không suy ra hoàn thành từ mock.

## 3. Tình trạng đến ngày 11/10/2026

Checklist A–L gồm **135 task: 66 đã hoàn thành, 69 còn mở**.
Ngoài ra có **10 tiêu chí nghiệm thu toàn hệ thống**. Task mở bao gồm cả phần
mở rộng tùy chọn, không chỉ công việc bắt buộc để hoàn thành prototype.

| Hạng mục | Hiện trạng | Phần còn thiếu |
| --- | --- | --- |
| Binance REST | Đã có lấy nến và symbol, Spot/Futures qua cấu hình | Lấy theo lịch, streaming nếu mở rộng |
| Redis | Đã có cache, TTL và stale fallback | Đồng bộ cấu hình password; lock/cooldown nhiều process |
| Chỉ báo | Đã có SMA, EMA, RSI Wilder và `POST /indicators` | Task Decimal T031; nghiệm thu đối chiếu TradingView |
| Frontend | Đã kết nối symbol/chỉ báo thật; dark/light; responsive; EN/VI | CRUD luật qua BE, kiểm tra điều kiện và lịch sử cảnh báo |
| Luật | Đã có form, mô tả, luật mẫu, lưu/bật/tắt/xóa tại trình duyệt | Schema BE, SQL và API CRUD |
| Cảnh báo | Chưa có | Rule engine, dedupe, `/evaluate`, `/alerts`, UI cảnh báo |
| Chạy ứng dụng | Docker Compose chạy BE + Redis; FE chạy Vite riêng | Chạy cả FE/BE/Redis bằng một lệnh; cấu hình triển khai |
| Kiểm thử | Đã có bộ test BE và FE | Tích hợp SQL/rules/alerts, end-to-end và CI |

### Luồng đang có

```text
FE -> GET /symbols hoặc POST /indicators -> FastAPI
                                             |
                                             v
                                        Redis cache
                                             |
                                  miss -> Binance REST -> ghi cache

FE -> tạo/bật/tắt/xóa luật -> localStorage của trình duyệt
FE -> TradingView widget -> dữ liệu trực tiếp từ TradingView
```

### Luồng prototype cần hoàn thiện

```text
FE -> CRUD /rules -> FastAPI -> SQL rules
FE -> POST /evaluate -> đọc enabled rules từ SQL
                     -> Binance/Redis -> tính chỉ báo -> kiểm tra điều kiện
                     -> SQL alerts, chống trùng theo rule + candle
                     -> FE hiển thị kết quả
FE -> GET /alerts -> lịch sử cảnh báo từ SQL
```

### Đối chiếu bảng kế hoạch 3 tuần của nhóm

Đánh giá dưới đây dựa trên source workspace ngày 11/10/2026; không xác nhận
phân công đã được thực hiện chỉ từ tên người trong bảng kế hoạch.

| Week | Phân công theo bảng gốc | Kết quả yêu cầu | Kết quả hiện tại | Đánh giá / việc còn thiếu |
| --- | --- | --- | --- | --- |
| 1 | Phương Hữu Thành Nam, Bùi Quý Đăng, Nguyễn Anh Vũ | Binance API, cập nhật tự động tối thiểu 5 symbols | REST và Redis đã có; symbol được chọn theo request; chưa có scheduler/WebSocket | Đạt một phần. Bổ sung B15–B16, lưu bằng chứng K09 |
| 2 | Nguyễn Anh Vũ, Phương Hữu Thành Nam, Đào Công Tuấn | Ít nhất 5 loại indicator và 5 trading rules | Có 3 loại SMA/EMA/RSI, 10 luật mẫu FE; chưa có MACD/BB hoặc engine thực thi | Chưa đủ. Bổ sung C15–C18, hoàn thành H/I và J09 |
| 3 | Đào Công Tuấn, Bùi Quý Đăng | Luồng Binance Data → Indicator → Trading Rule hoạt động | Luồng Data → Indicator → FE đã có; rules lưu localStorage, chưa đánh giá hoặc tạo alert | Chưa đạt end-to-end. Hoàn thành G–K |
| 3 Optional | Đào Công Tuấn, Bùi Quý Đăng | Một kênh thông báo; AI trả Up / Down / Sideway nếu chọn làm | Chưa có module gửi thông báo hoặc AI trend | Có thể hoãn. Theo dõi L07 và L09 riêng với phần bắt buộc |

MA là nhóm moving averages, không nên tính MA và SMA thành hai loại độc lập.
SMA(20)/SMA(50) cũng là hai chu kỳ của cùng một loại, không đủ để tăng số loại.
10 mẫu trong form chứng minh cấu hình luật đã có; chưa chứng minh ít nhất 5 luật
được thực thi và trả kết quả đúng. Widget TradingView có các indicator riêng cũng
không thay cho việc triển khai và kiểm thử chúng trong backend dự án.

## 4. Checklist công việc

### A. Nền tảng và cấu trúc dự án

- [x] A01 Tách source thành `FE/` và `BE/`.
- [x] A02 Khởi tạo backend Python 3.11+, FastAPI và Uvicorn.
- [x] A03 Khởi tạo frontend React + Vite.
- [x] A04 Khai báo dependency Python và file khóa phiên bản kiểm thử.
- [x] A05 Khai báo dependency frontend và `package-lock.json`.
- [x] A06 Đọc cấu hình backend bằng settings từ `.env`.
- [x] A07 Cung cấp `.env.example` ở gốc và `FE/.env.example`.
- [x] A08 Cấu hình logging backend và đóng HTTP/Redis connections khi shutdown.
- [x] A09 Cung cấp Swagger và endpoint `GET /health` kiểm tra Redis.
- [x] A10 Viết hướng dẫn clone, chạy lại sau pull và chạy trên máy khác.

**Bằng chứng:** `BE/pyproject.toml`, `BE/app/config.py`, `BE/app/main.py`,
`FE/package.json`, [hướng dẫn chạy](HUONG_DAN_CHAY.md).

### B. Binance REST và Redis

- [x] B01 Tạo Binance REST client lấy nến theo symbol, interval và limit.
- [x] B02 Hỗ trợ các khung `1h`, `1d`, `1w`.
- [x] B03 Hỗ trợ `spot` và `futures` bằng cấu hình backend.
- [x] B04 Giữ `open_time`, `close`, `close_time`; giá là chuỗi để giữ độ chính xác.
- [x] B05 Lấy `exchangeInfo`, lọc các cặp USDT có trạng thái `TRADING`.
- [x] B06 Cung cấp `GET /symbols` và cache danh sách symbol.
- [x] B07 Cung cấp `GET /klines` và chuẩn hóa symbol thành uppercase.
- [x] B08 Lưu JSON nến trong Redis; cache hit không gọi lại Binance.
- [x] B09 Tách key theo market, API host, symbol, interval và limit.
- [x] B10 Cấu hình TTL nến mới, bản stale và danh sách symbol.
- [x] B11 Retry có backoff cho lỗi mạng/5xx; xử lý invalid symbol và cooldown 429/418.
- [x] B12 Dùng stale fallback khi phù hợp, giữ nguồn và thời điểm fetch gốc.
- [x] B13 Gộp refresh đồng thời bằng lock trong một process; đọc cache lại trong lock.
- [x] B14 Cung cấp CLI fetch một lần, ghi Redis và báo lỗi bằng mã thoát.
- [ ] B15 **P1 — Week 1** Thêm worker cập nhật định kỳ; cấu hình danh sách ít nhất 5 symbols và chu kỳ chạy; ghi Redis, quản lý shutdown, lỗi từng symbol và không tạo job chồng nhau.
- [ ] B16 **P1 — Week 1** Kiểm thử tự cập nhật cho ít nhất 5 symbols hợp lệ, ví dụ BTCUSDT/ETHUSDT/BNBUSDT/SOLUSDT/XRPUSDT; xác nhận vẫn cập nhật khi không mở FE hoặc gọi HTTP thủ công.

**Bằng chứng:** `BE/app/binance/client.py`, `BE/app/cache/redis_cache.py`,
`BE/app/service.py`, `BE/app/cli.py`, `BE/tests/test_market_data.py`.
TTL là thời gian hết hạn cache, không phải lịch tự fetch. Lock/cooldown hiện chỉ
dùng trong một process, chưa đủ cho worker pool.

### C. Tính chỉ báo và API chỉ báo

- [x] C01 Tạo schema request/response cho API chỉ báo.
- [x] C02 Tính SMA theo cửa sổ trượt.
- [x] C03 Tính EMA với seed SMA và hệ số `2/(N+1)`.
- [x] C04 Tính RSI bằng Wilder smoothing, xử lý chuỗi tăng/giảm/đi ngang.
- [x] C05 Dùng Decimal và xuất giá trị dưới dạng chuỗi thập phân.
- [x] C06 Trả `insufficient_data` và `value=null` khi chưa đủ nến.
- [x] C07 Mặc định lọc nến đóng theo cutoff của thời điểm đánh giá và snapshot.
- [x] C08 Hỗ trợ `include_open=true` và đánh dấu `provisional`.
- [x] C09 Hỗ trợ nhiều cặp chỉ báo–chu kỳ trong cùng một snapshot.
- [x] C10 Validate request strict, từ chối trường lạ và cặp chỉ báo trùng.
- [x] C11 Giữ metadata `source`, `stale`, `warning`, `fetched_at`, `cache_key`.
- [x] C12 Cung cấp `POST /indicators`, không thay đổi contract `GET /klines`.
- [ ] C13 **P1** Hoàn thành task [T031](specs/001-calculate-indicators/tasks.md): cô lập đầy đủ Decimal context, tránh phụ thuộc traps/exponent của bên gọi; thêm kiểm thử và cập nhật nghiệm thu.
- [ ] C14 **P2** Đối chiếu SMA/EMA/RSI với TradingView trên cùng market, nến, chu kỳ và lịch sử khởi tạo; ghi sai số, timezone và nguyên nhân khác biệt.
- [ ] C15 **P1 — Week 2** Implement MACD: tham số fast/slow/signal, MACD line, signal line, histogram; chốt warm-up và contract chuỗi nhiều output.
- [ ] C16 **P1 — Week 2** Implement Bollinger Bands: period, hệ số độ lệch, middle/upper/lower; chốt quy ước độ lệch chuẩn và warm-up.
- [ ] C17 **P1 — Week 2** Mở rộng API, form, bảng chỉ báo và schema luật để chọn đúng output MACD/BB; giữ tương thích SMA/EMA/RSI và thêm EN/VI.
- [ ] C18 **P1 — Week 2** Viết test công thức/HTTP cho MACD/BB, đủ/thiếu nến và nến mở; nghiệm thu 5 loại indicator trên fixture tham chiếu độc lập.

**Bằng chứng:** `BE/app/indicators.py`, `BE/app/indicator_models.py`,
[contract API](specs/001-calculate-indicators/contracts/indicators-api.md),
[nghiệm thu chỉ báo](specs/001-calculate-indicators/quickstart.md).
Task C05 xác nhận Decimal đã được dùng; chưa xác nhận đã giải quyết C13.

### D. Frontend và kết nối API hiện tại

- [x] D01 Xây dashboard gồm biểu đồ, form luật, bảng chỉ báo và danh sách luật.
- [x] D02 Gọi API thật `GET /symbols`; giữ chế độ mock riêng để thử giao diện.
- [x] D03 Cấu hình Vite proxy `/api` và `VITE_API_TARGET`.
- [x] D04 Gọi `POST /indicators` theo lựa chọn trong form.
- [x] D05 Chuyển schema form sang contract chỉ báo; chỉ yêu cầu các cặp cần dùng.
- [x] D06 Debounce chỉnh form và hủy request cũ để tránh ghi đè kết quả mới.
- [x] D07 Hiển thị giá trị, nguồn, thời gian cập nhật, thiếu nến và trạng thái provisional.
- [x] D08 Thêm nút Refresh cho bảng chỉ báo và trạng thái loading/error.
- [x] D09 Thêm tìm kiếm cặp giao dịch trong danh sách Binance.
- [x] D10 Đồng bộ symbol và timeframe giữa form, TradingView và bảng chỉ báo.
- [x] D11 Tạo form giá/SMA/EMA/RSI, chu kỳ, toán tử, target và chế độ nến.
- [x] D12 Thêm 10 luật mẫu, mô tả luật và lỗi theo từng trường.
- [x] D13 Lưu luật trong localStorage; bật/tắt/xóa luật tại trình duyệt.
- [x] D14 Nhúng TradingView, có loading, retry và liên kết mở biểu đồ ngoài.

**Bằng chứng:** `FE/src/App.jsx`, `FE/src/api/`, `FE/src/components/`.
Nút Refresh hiện tính lại chỉ báo; chưa gọi `/evaluate` và chưa tạo cảnh báo.
TradingView có nguồn riêng, chưa được cấp chuỗi giá từ backend.

### E. Giao diện, điện thoại và ngôn ngữ

- [x] E01 Chỉnh màu nền, chữ, border và nút theo hệ màu dùng chung.
- [x] E02 Thêm dark/light, mặc định dark và nhớ lựa chọn trong trình duyệt.
- [x] E03 Đồng bộ theme của TradingView với theme ứng dụng.
- [x] E04 Mở rộng dashboard theo chiều ngang cửa sổ, giữ lề nhỏ.
- [x] E05 Tăng chiều cao TradingView trên desktop và đặt chiều cao riêng theo breakpoint.
- [x] E06 Sắp xếp lại chart/form/rules trên tablet và điện thoại.
- [x] E07 Sửa card luật đã lưu trên mobile để có cùng chiều rộng với form.
- [x] E08 Thêm English / Tiếng Việt, mặc định English và nút EN / VI.
- [x] E09 Nhớ ngôn ngữ; dịch nhãn, luật mẫu, mô tả, lỗi, ngày giờ và locale TradingView; đổi ngôn ngữ giữ dữ liệu form.
- [x] E10 Cung cấp focus bàn phím, nhãn điều khiển và liên kết lỗi form; đã kiểm tra bố cục từ màn hình nhỏ 320px đến desktop.

**Bằng chứng:** `FE/src/index.css`, `FE/src/i18n.js`,
`FE/src/LanguageContext.jsx`, `FE/tests/i18n.test.js`, [README FE](FE/README.md).
Các chi tiết lỗi kỹ thuật do backend/Binance trả về có thể giữ ngôn ngữ gốc.
E10 là kiểm tra cơ bản, chưa phải nghiệm thu accessibility toàn bộ.

### F. Kiểm thử, tài liệu và chạy bản hiện tại

- [x] F01 Viết test market data dùng HTTP mock và fakeredis.
- [x] F02 Viết test công thức, biên dữ liệu, snapshot và HTTP contract chỉ báo.
- [x] F03 Viết test FE cho API contract, lỗi mạng, payload, định dạng và song ngữ.
- [x] F04 Build production frontend bằng Vite.
- [x] F05 Tạo Dockerfile backend và Compose cho API + Redis, healthcheck, AOF/volume, restart policy.
- [x] F06 Viết README gốc/FE/BE, tài liệu chạy và hướng dẫn biến môi trường.
- [ ] F07 **P1** Đồng bộ `REDIS_PASSWORD` trong `.env.example` với Compose; thay password cố định trong Compose và khớp URL Redis khi chạy local/Docker.
- [ ] F08 **P1** Sửa tài liệu network/Redis cho đúng Compose hiện tại: port đang bind `0.0.0.0`, khác phần hướng dẫn ghi localhost; chốt cấu hình mặc định và cách chạy LAN.
- [ ] F09 **P1** Commit/push phần song ngữ và file kế hoạch; cập nhật PR tiếng Anh, review và merge các thay đổi FE còn chờ.
- [ ] F10 **P2** Rà soát tài liệu lỗi thời, gồm đoạn README còn nói chưa tích hợp FE chỉ báo; thống nhất giới hạn chu kỳ FE 250 với API tối đa 999 và quy tắc thiếu lịch sử.

**Bằng chứng:** `BE/tests/`, `FE/tests/`, `BE/Dockerfile`, `compose.yaml`,
[README](README.md), [hướng dẫn chạy](HUONG_DAN_CHAY.md).
F07–F10 đang để mở; tài liệu hướng dẫn đã có không đồng nghĩa mọi ví dụ đang khớp cấu hình mới nhất.

### G. SQL và lưu luật tại backend

- [ ] G01 **P1** Chốt schema SQL cho rules/alerts, khóa và index; SQLite trước, tương thích PostgreSQL.
- [ ] G02 **P1** Thêm SQLAlchemy, session lifecycle và biến `DATABASE_URL`.
- [ ] G03 **P1** Tạo migration ban đầu và hướng dẫn chạy migration trên máy mới.
- [ ] G04 **P1** Tạo bảng rules với symbol, timeframe, indicator, operator, target, candle_mode, enabled và timestamps.
- [ ] G05 **P1** Tạo bảng alerts với rule_id, candle time, giá trị hai vế, thời điểm đánh giá và metadata nguồn/nến.
- [ ] G06 **P1** Đặt unique constraint chống trùng alert theo `(rule_id, candle_open_time)` cho luật một điều kiện trong prototype.
- [ ] G07 **P1** Tạo repository CRUD rules và transaction ghi alerts.
- [ ] G08 **P1** Quy định khi sửa/xóa luật thì lịch sử và khóa chống trùng được xử lý thế nào; dùng snapshot/revision nếu cần để giữ ý nghĩa cảnh báo cũ.
- [ ] G09 **P2** Thêm import/export luật JSON và luồng chuyển luật localStorage sang backend có xác nhận.
- [ ] G10 **P1** Kiểm thử persistence qua restart, rollback khi lỗi và hành vi constraint với request đồng thời.

**Nghiệm thu:** tạo luật qua BE, restart ứng dụng rồi vẫn đọc được; alert được lưu
bằng transaction và không bị ghi trùng khi hai lần đánh giá chạy đồng thời.
Chưa cần đăng nhập cho demo một người dùng; mô hình nhiều người dùng thuộc nhóm L.

### H. Rule engine một điều kiện

- [ ] H01 **P1** Tạo Pydantic rule schema phía BE; validate symbol, timeframe, indicator, target, operator và candle_mode.
- [ ] H02 **P1** Tái sử dụng bộ tính chỉ báo; hỗ trợ giá đóng cửa ở vế trái và target số/chỉ báo.
- [ ] H03 **P1** Implement toán tử `gt` và `lt`, xác định hành vi tại giá trị bằng nhau.
- [ ] H04 **P1** Implement `gte` và `lte` theo bản kế hoạch gốc; bổ sung lựa chọn FE tương ứng khi API đã có.
- [ ] H05 **P1** Implement `cross_above`: `prev_A <= prev_B` và `cur_A > cur_B`.
- [ ] H06 **P1** Implement `cross_below`: `prev_A >= prev_B` và `cur_A < cur_B`.
- [ ] H07 **P1** Bỏ qua điểm thiếu dữ liệu; không dùng null/0 giả để tạo tín hiệu, không đủ hai nến thì chưa thể xác nhận cross.
- [ ] H08 **P1** Đánh giá đúng closed/include-current và gắn provisional cho tín hiệu nến mở.
- [ ] H09 **P1** Thêm lookback scan N nến, xác định giới hạn N và trả các tín hiệu bị bỏ lỡ giữa hai lần Refresh.
- [ ] H10 **P1** Gom luật theo market/symbol/timeframe để dùng chung snapshot và chỉ báo; chỉ xử lý enabled rules, giữ nguồn/cutoff nhất quán.
- [ ] H11 **P1** Chốt vòng đời cảnh báo nến mở: cập nhật hay giữ bản lần đầu, cách chuyển sang closed và tránh dedupe che thay đổi tín hiệu.
- [ ] H12 **P1** Viết test fixture độc lập cho 6 toán tử, target số/chỉ báo, equality, null, lookback và hai chế độ nến.

**Nghiệm thu:** fixture RSI `25, 28, 33, 38` với target 30 cho một cross tại 33;
`gt` đúng ở 33 và 38; Refresh lặp lại không tạo alert mới cho cùng rule/candle.

### I. API luật, đánh giá và lịch sử

- [ ] I01 **P1** Cung cấp `POST /rules` tạo luật và trả ID backend.
- [ ] I02 **P1** Cung cấp `GET /rules` và `GET /rules/{id}`.
- [ ] I03 **P1** Cung cấp `PATCH /rules/{id}` chỉnh điều kiện hoặc enabled; kiểm tra field được phép sửa.
- [ ] I04 **P1** Cung cấp `DELETE /rules/{id}` theo chính sách lịch sử đã chốt.
- [ ] I05 **P1** Cung cấp `POST /evaluate`, tham số lookback và kết quả đánh giá từng luật.
- [ ] I06 **P1** Ghi alert chống trùng trong SQL trước khi trả response; báo rõ alert mới và alert đã tồn tại.
- [ ] I07 **P1** Cung cấp `GET /alerts` có phân trang, lọc symbol/rule/time và thứ tự thời gian ổn định.
- [ ] I08 **P1** Chuẩn hóa lỗi và bổ sung OpenAPI/examples; quy định đánh giá nhiều luật khi một nhóm dữ liệu lỗi, không coi stale là kết quả mới.

**Nghiệm thu:** thao tác đầy đủ bằng Swagger; request sai không ghi SQL;
hai request evaluate đồng thời không ghi trùng và lỗi được trả rõ theo contract.

### J. FE quản lý luật và cảnh báo qua BE

- [ ] J01 **P1** Chuyển rule store từ localStorage sang API CRUD; giữ local/mock mode rõ ràng nếu còn dùng.
- [ ] J02 **P1** Nối tạo/sửa/xóa/bật/tắt luật với BE và xử lý lỗi, chờ lưu, ID backend.
- [ ] J03 **P1** Thêm Refresh đánh giá luật gọi `/evaluate`, phân biệt với Refresh bảng chỉ báo.
- [ ] J04 **P1** Tạo panel cảnh báo mới: symbol, luật, giá trị hai vế, candle time và trạng thái nến.
- [ ] J05 **P1** Hiển thị loading, không có tín hiệu, lỗi từng nhóm và stale/provisional trong kết quả đánh giá.
- [ ] J06 **P1** Tạo màn hình lịch sử cảnh báo có phân trang và bộ lọc.
- [ ] J07 **P2** Nối cảnh báo tới đúng cặp/khung TradingView; hiển thị snapshot luật tại thời điểm kích hoạt.
- [ ] J08 **P1** Dịch các màn hình/API error mới sang EN/VI và kiểm tra điện thoại, bàn phím, lưu qua restart.
- [ ] J09 **P1 — Week 2/3** Tạo ít nhất 5 luật qua BE và chạy thật với fixture có/không kích hoạt; ghi điều kiện, giá trị hai vế, candle time và kết quả mong đợi/thực tế, không chỉ đếm luật mẫu FE.

**Nghiệm thu:** tạo một luật từ FE, reload vẫn có luật từ BE, bấm Refresh nhận
cảnh báo và mở lịch sử; bật/tắt ảnh hưởng thực sự đến bộ đánh giá.

### K. Nghiệm thu prototype và triển khai

- [ ] K01 **P1** Thêm integration tests: mock Binance + Redis + SQL, từ tạo luật đến đánh giá và đọc alert.
- [ ] K02 **P1** Thêm hồi quy evaluate lặp/đồng thời, sửa/xóa luật và dữ liệu lỗi.
- [ ] K03 **P1** Thử end-to-end với Binance thật, luật dễ kích hoạt rồi luật khó hơn; ghi phiên bản, ngày, dữ liệu và kết quả.
- [ ] K04 **P2** Kiểm tra Chrome/Edge, desktop/tablet/mobile, theme và EN/VI cho toàn bộ luồng cảnh báo.
- [ ] K05 **P2** Thêm CI chạy BE tests/Ruff và FE tests/build khi mở PR.
- [ ] K06 **P2** Tạo Dockerfile FE và bổ sung service FE/reverse proxy để chạy FE + BE + Redis bằng một lệnh.
- [ ] K07 **P1** Cấu hình SQL volume, backup/restore và kiểm thử chạy từ clone sạch với `.env.example` trên máy khác.
- [ ] K08 **P2** Hoàn thiện README, sơ đồ, video/demo và báo cáo; ghi giới hạn, nguồn dữ liệu, công thức, sai số và hướng phát triển.
- [ ] K09 **P1 — Đối chiếu plan 3 tuần** Lập bảng nghiệm thu định lượng: 5 symbols có ít nhất 2 lần fetch thành công tự động mỗi symbol, 5 loại indicator được tính/hiển thị và 5 luật được thực thi đúng; ghi timestamps, nguồn dữ liệu và kết quả, tách cache hit khỏi fetch mới.

**Nghiệm thu:** người mới clone làm theo tài liệu chạy được, không cần file cá nhân
của máy phát triển; toàn bộ luồng tạo luật → Refresh → cảnh báo → lịch sử hoạt động.

### L. Mở rộng sau prototype — chưa triển khai

- [ ] L01 **P3** Mở rộng worker từ cập nhật dữ liệu B15 sang tự đánh giá enabled rules theo lịch, có heartbeat và retry có giới hạn; prototype đánh giá luật bằng Refresh trước.
- [ ] L02 **P3** Thêm Redis distributed lock/cooldown và job idempotency trước khi chạy nhiều workers.
- [ ] L03 **P3** Kết nối Binance WebSocket, reconnect/backfill và xác định nến đã đóng; REST vẫn phục vụ khôi phục.
- [ ] L04 **P3** Đẩy trạng thái/cảnh báo mới về FE qua SSE hoặc WebSocket.
- [ ] L05 **P3** Thêm tài khoản, quyền sở hữu luật/alerts và kiểm thử chống truy cập chéo người dùng.
- [ ] L06 **P3** Mở rộng luật AND/OR, OHLCV và registry để thêm chỉ báo mới.
- [ ] L07 **P3** Thêm Telegram/email/webhook sau khi chốt kênh gửi, cấu hình và chính sách chống spam.
- [ ] L08 **P3** Thêm backtest và thống kê tín hiệu, dữ liệu lịch sử/incremental Redis, metrics và kiểm thử tải worker pool.
- [ ] L09 **P3 — Optional Week 3** Nếu nhóm chọn AI trend: chốt model và input, trả 3 nhãn Up/Down/Sideway, hiển thị kết quả trên FE và đánh giá với bộ mẫu có nhãn; quy tắc if/else thuần indicator phải được gọi đúng là rule-based, không nghiệm thu thành AI.

Không dùng tỷ lệ hoàn thành toàn bộ nhóm A–L để đánh giá prototype:
nhóm L là hướng mở rộng tùy chọn, không phải yêu cầu bắt buộc cho demo đầu tiên.

## 5. Thứ tự triển khai đề xuất

| Mốc | Công việc | Phụ thuộc | Kết quả cần có |
| --- | --- | --- | --- |
| M0 — Chốt nền và tiêu chí Week 1/2 | C13, C15–C18, B15–B16, F07–F10 | Source hiện có | Cấu hình/tài liệu khớp, FE song ngữ được đưa vào Git; dữ liệu tự cập nhật và có đủ 5 loại indicator |
| M1 — Lưu luật thật | G01–G08, G10, H01, I01–I04 | M0 | Luật nằm trong SQL, CRUD qua BE |
| M2 — Đánh giá điều kiện | H02–H12, I05–I06 | M1 và bộ tính chỉ báo | Evaluate đúng, lookback hoạt động, alert không trùng |
| M3 — Giao diện cảnh báo | I07–I08, J01–J09; G09 nếu cần chuyển luật cũ | M1/M2 | Tạo luật, Refresh và xem lịch sử từ FE; ít nhất 5 luật thực thi được |
| M4 — Demo hoàn chỉnh | C14, K01–K09 | M3 | Kiểm thử, CI, chạy trên máy mới, tài liệu và bằng chứng chỉ tiêu 5/5/5 |
| M5 — Tự động/realtime | Nhóm L được chọn | Prototype ổn định | Worker theo lịch/streaming và vận hành nhiều process |

Mỗi mốc nên làm thành nhánh `feat/<ten-tinh-nang>` riêng và PR có mô tả tiếng Anh,
tiêu chí nghiệm thu, kết quả kiểm thử. Các mốc thể hiện thứ tự phụ thuộc;
chưa gán deadline vì khối lượng SQL/rule engine chưa được triển khai và đo thực tế.

## 6. Điều kiện hoàn thành prototype

- [ ] ACCEPT01 Clone source trên máy khác, tạo env và chạy theo tài liệu thành công.
- [ ] ACCEPT02 Tự cập nhật tối thiểu 5 symbols; FE hiển thị đủ 5 loại indicator thật; xác minh khác biệt nếu đối chiếu TradingView.
- [ ] ACCEPT03 Tạo/chỉnh/xóa/bật/tắt luật từ FE, dữ liệu tồn tại sau restart BE và trình duyệt.
- [ ] ACCEPT04 Ít nhất 5 luật chạy đúng bằng Refresh kiểm tra enabled rules, hỗ trợ target số/chỉ báo và hai chế độ nến.
- [ ] ACCEPT05 Cross dùng hai nến và lookback không bỏ sót sự kiện trong phạm vi đã chọn.
- [ ] ACCEPT06 Refresh lặp/đồng thời không ghi alert trùng; lịch sử đọc được từ SQL.
- [ ] ACCEPT07 Lỗi Binance/Redis/SQL và thiếu nến được hiển thị rõ; không tạo tín hiệu giả.
- [ ] ACCEPT08 Các màn hình chính hoạt động trên điện thoại, dark/light và EN/VI.
- [ ] ACCEPT09 Bộ test tích hợp và end-to-end có bằng chứng; CI đạt; các lỗi P1 đã được giải quyết.
- [ ] ACCEPT10 README và báo cáo mô tả đúng tính năng đã có, giới hạn và cách demo.

Đây là checklist nghiệm thu toàn hệ thống, nên để mở dù một số thành phần đã hoàn thành.
Ứng dụng hiện chưa đạt prototype cảnh báo end-to-end vì còn thiếu nhóm G–J.

## 7. Bằng chứng kiểm tra và giới hạn hiện tại

| Kiểm tra | Bằng chứng đến ngày cập nhật | Giới hạn |
| --- | --- | --- |
| Backend tests | Tài liệu nghiệm thu chỉ báo ghi 134 test đạt và Ruff đạt | Không chạy lại BE trong lần viết kế hoạch này; T031 vẫn mở |
| Frontend tests | Lần hoàn thiện song ngữ ngày 11/10/2026: 10 test đạt | Chưa có bộ E2E tự động cho SQL/rule engine |
| FE production build | Vite build đạt ngày 11/10/2026 | Build đạt không thay thế kiểm thử luồng cảnh báo |
| Browser | Đã kiểm tra EN/VI, nhớ lựa chọn, giữ form khi đổi ngôn ngữ; các kích thước 320/390/640/768/1440px | Kiểm tra trên trình duyệt phát triển; chưa phủ mọi thiết bị |
| Market data thật | README ghi đã kiểm tra Binance Spot/Redis và CLI Futures ở giai đoạn trước | Chưa có cảnh báo thật end-to-end để nghiệm thu |

Các điểm cần ghi rõ trong demo/báo cáo:

- Redis đang là cache có TTL, chưa phải database lịch sử dài hạn.
- Luật hiện lưu riêng từng trình duyệt; chưa chia sẻ giữa máy và chưa gửi cảnh báo.
- Docker Compose hiện khởi động BE + Redis, không khởi động FE.
- Futures đang là cấu hình backend; FE chưa có bộ chọn market và nhãn thị trường đầy đủ.
- Giá trị indicator phụ thuộc snapshot, limit, seed và cutoff; `fetched_at` không chứng minh tuyệt đối giá đóng cuối tại ranh giới thời gian.
- API cho phép nhiều cặp chỉ báo/chu kỳ; cần chốt giới hạn sử dụng và đo tải trước khi triển khai nhiều người dùng.
- Widget TradingView phụ thuộc dịch vụ bên ngoài; lỗi widget không đồng nghĩa BE ngừng tính chỉ báo.

## 8. Cách cập nhật kế hoạch

1. Khi bắt đầu, chọn task `[ ]` theo thứ tự phụ thuộc và ghi phạm vi trong PR.
2. Khi hoàn thành, đổi thành `[x]`, bổ sung bằng chứng file/test và cập nhật ngày.
3. Nếu chỉ làm một phần, giữ `[ ]`, ghi phần đã có và điều kiện còn thiếu.
4. Nếu phát hiện lỗi mới, thêm task mới thay vì sửa lịch sử để trông như đã hoàn thành.
5. Khi scope đổi, cập nhật mục tiêu, thứ tự mốc và checklist nghiệm thu tương ứng.

Tài liệu liên quan:

- [README dự án](README.md)
- [Hướng dẫn chạy và env](HUONG_DAN_CHAY.md)
- [Frontend](FE/README.md) / [Backend](BE/README.md)
- [Đặc tả chỉ báo](specs/001-calculate-indicators/spec.md)
- [Plan chỉ báo](specs/001-calculate-indicators/plan.md)
- [Tasks chỉ báo, gồm T031 chưa hoàn thành](specs/001-calculate-indicators/tasks.md)
- [Nghiệm thu chỉ báo](specs/001-calculate-indicators/quickstart.md)
