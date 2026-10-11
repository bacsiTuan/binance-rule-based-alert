# Nghiên cứu: SMA, EMA và RSI Wilder

Ngày: 2026-10-11. Căn cứ: [spec](spec.md), hiến chương và mã hiện tại.
Không còn quyết định kỹ thuật chặn thiết kế. Các quyết định dưới đây chưa phải mã đã triển khai.

## 1. Điểm tích hợp

**Quyết định**: Thêm POST /indicators trong BE/app/main.py; validate request trước I/O,
gọi app.state.service.klines(symbol, interval, limit) đúng một lần rồi gọi bộ tính thuần.
Tái sử dụng Candle, Interval, KlinesResult; thêm schema chỉ báo riêng.

**Lý do**: BE/app/service.py đã quản lý hit/miss, lock, TTL, stale fallback và metadata;
BE/app/binance/client.py đã tách Spot/Futures, retry và cooldown.
Dùng chung instance service giữ nguyên hành vi và tránh tạo lock/client riêng.

**Phương án khác**: Gọi Binance trực tiếp hoặc thêm service lấy dữ liệu mới gây trùng logic.
GET với chuỗi query mã hóa nhiều cặp khó kiểm tra hơn body có cấu trúc.
FastAPI hỗ trợ model body và validation tự động:
[tài liệu request body](https://fastapi.tiangolo.com/tutorial/body/).
Không thay CLI, FE, Redis schema, deployment hoặc dependency.

## 2. Số học và thuật toán

**Quyết định**: Dùng decimal của thư viện chuẩn, khởi tạo từ chuỗi close.
Trong localcontext riêng, ROUND_HALF_EVEN, precision tối thiểu 50 chữ số;
tăng tới max(50, A-E+1+32), với A là adjusted exponent lớn nhất và E là exponent
nhỏ nhất của các giá khác 0; chuỗi toàn 0 dùng 50. Không dùng quantize cho hiển thị,
không thay context toàn cục, không đi qua float. Xuất format(value, "f"), chuẩn hóa
giá trị 0 thành "0"; không cam kết số lượng số 0 cuối chuỗi.

SMA dùng tổng cửa sổ; EMA seed SMA(N), alpha=2/(N+1); RSI seed N biến động
trên N+1 nến và làm mượt Wilder. Thiếu seed trả null. RSI không biến động trả 50,
chỉ tăng trả 100, chỉ giảm trả 0 đúng spec. Không có trạng thái qua các lần gọi.

**Lý do**: Tương thích chuỗi giá và ngưỡng sai số FR-009; tránh mất biến động nhỏ
trên giá có nhiều chữ số. Context hữu hạn vẫn có làm tròn số học ở phép chia,
khác với làm tròn phục vụ hiển thị. Kiểm tra sai số bằng oracle Fraction độc lập
trên fixture và chuỗi dài; không coi precision được chọn là bằng chứng tự thân.
[Tài liệu Decimal](https://docs.python.org/3/library/decimal.html) mô tả tạo từ chuỗi
và context điều khiển độ chính xác phép toán.

**Phương án khác**: float hoặc thư viện chỉ báo bổ sung không cần thiết cho ba
công thức đã được đặc tả và có thể khác seed/RSI đi ngang. Không thêm pandas/TA-Lib.

## 3. Snapshot và nến mở

**Quyết định**: Lấy evaluated_at một lần sau khi nhận snapshot; chuyển UTC sang ms
bằng số học nguyên. cutoff=min(evaluated_at, fetched_at_ms). Chỉ nến có close_time
nhỏ hơn cutoff mới đủ điều kiện mặc định. Khi include_open=true, giữ toàn bộ
snapshot, gắn provisional theo phụ thuộc: SMA theo cửa sổ N; EMA/RSI tích lũy từ
seed và mọi bước trước đó. Điểm chưa có giá trị cũng phản ánh nến tạm thời trong
prefix đã dùng để warm-up. stale và provisional độc lập.

**Lý do**: Không coi nến mở trong cache tự trở thành giá đóng cuối chỉ vì thời gian
trôi qua. Việc tính không được fetch bù, đổi TTL hoặc sửa snapshot gốc.

**Giới hạn đã biết**: service.py ghi fetched_at sau khi nhận HTTP, không phải thời
điểm Binance chụp dữ liệu. Điều kiện của spec là quy ước theo metadata hiện có,
không chứng minh tuyệt đối finality nếu HTTP đi qua ranh giới đóng nến hoặc đồng hồ
lệch. Giữ hợp đồng hiện tại; không tự thêm timestamp nguồn hoặc cơ chế xác minh.
Kiểm thử chính xác quy ước cutoff, không tuyên bố bảo đảm mạnh hơn metadata.

## 4. Validation và lỗi

**Quyết định**: Body dùng tên chữ thường sma/ema/rsi, period nguyên strict 1–999,
default 14; include_open boolean strict; limit nguyên strict 1–1000. Trùng cặp sau
default, danh sách rỗng, trường lạ, loại không hỗ trợ: 422 trước khi gọi service.
Giữ thứ tự kết quả theo request. Tối đa 2997 cặp hợp lệ theo miền tên/chu kỳ,
không thêm giới hạn sản phẩm ngoài spec.

Kiểm tra snapshot ở bộ tính: nhận diện khớp cấu hình/yêu cầu, datetime có timezone,
timestamp nguyên, open_time tăng nghiêm ngặt, close_time tăng nghiêm ngặt và
open_time<=close_time, giá hữu hạn không âm. Không suy diễn độ dài interval hoặc
lấp khoảng trống. Lỗi snapshot sau khi service trả về: 502 với mã
invalid_indicator_data, không retry/fallback mới. Lỗi nguồn do service ném ra
giữ handler và status hiện tại.

**Lý do**: BE/app/models.py kiểm tra giá nhưng không toàn bộ bất biến chuỗi;
cache đã parse thành KlinesResult vẫn có thể sai thứ tự hoặc nhận diện.
Validation bổ sung chỉ thuộc API chỉ báo, không sửa endpoint cũ.

**Phương án khác**: Sửa Candle/KlinesResult toàn cục hoặc tự sửa cache có thể thay
hành vi market data. Trả 200/null cho lỗi nguồn làm lẫn thiếu dữ liệu và dữ liệu hỏng.

## 5. Kiểm thử và hiệu năng

**Quyết định**: pytest, pytest-asyncio, httpx.MockTransport và fakeredis đã có.
Bộ tính nhận evaluated_at rõ ràng; test I/O dùng đồng hồ cố định.
Độ phức tạp O(K*M), M<=1000, K là số cặp; response O(K*M) vì trả chuỗi đầy đủ.
Không hứa SLA mới. Đo thời gian/size cho 3 chỉ báo x 1000 nến và thử miền tối đa,
ghi kết quả làm căn cứ nếu sau này cần giới hạn request.

**Lý do**: Test không dùng Binance/Redis thật; giữ nền kiểm thử hiện tại.
Test fixture nhỏ bằng phân số chính xác và bộ 1000 điểm phát hiện sai seed,
lệch timestamp và mất độ chính xác; benchmark không được biến thành ngưỡng
thời gian CI không ổn định.

**Phương án khác**: Scheduler, worker, cache kết quả chỉ báo và frontend mới ngoài phạm vi.
