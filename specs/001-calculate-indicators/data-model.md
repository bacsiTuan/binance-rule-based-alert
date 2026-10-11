# Mô hình dữ liệu chỉ báo

Ngày: 2026-10-11. Áp dụng cho [API mới](contracts/indicators-api.md).
Các tên trường bên dưới là hợp đồng dự kiến, chưa phải schema đang chạy.

## IndicatorRequest

| Trường | Kiểu / mặc định | Validation |
| --- | --- | --- |
| symbol | string, BTCUSDT | ASCII chữ/số, 2–30 ký tự; chuẩn hóa uppercase; không trim ngầm |
| interval | Interval, 1h | Tái sử dụng 1h/1d/1w |
| limit | integer, 300 | Strict, 1–1000; bool/string/float không hợp lệ |
| include_open | boolean, false | Strict |
| indicators | list IndicatorSelection, bắt buộc | Không rỗng, tối đa 2997 cặp duy nhất |

Cấm trường lạ. Không nhận market, host, candles, evaluated_at từ client.
Số 2997 là toàn miền 3 tên x 999 chu kỳ, không giảm phạm vi spec.

## IndicatorSelection

name là enum chữ thường sma/ema/rsi; period là integer strict 1–999, default 14.
Khóa duy nhất là (name, period) sau default; trùng từ chối toàn request, không gộp.
Kết quả giữ thứ tự danh sách đầu vào. Một phần tử sai làm toàn body không hợp lệ.

## Snapshot nguồn

Tái sử dụng Candle(open_time:int, close:str, close_time:int), Interval, KlinesResult
từ BE/app/models.py; không đổi model chung hoặc JSON cache.
Kiểm tra bổ sung trong bộ tính: giá hữu hạn không âm; timestamp nguyên; open_time
và close_time tăng nghiêm ngặt; open_time<=close_time; nhận diện market/symbol/
interval khớp yêu cầu và cấu hình. fetched_at phải có timezone.
Không dùng cache_key để suy ra hoặc ghi đè market. Dữ liệu sai báo lỗi toàn phép tính.
Chuỗi rỗng hợp lệ. Khoảng trống không bị lấp, không kiểm tra số ms cố định của 1w.

## IndicatorsResult

| Trường | Kiểu | Ý nghĩa |
| --- | --- | --- |
| market, symbol, interval | Kiểu từ KlinesResult | Giữ nhận diện nguồn |
| source | binance/cache/stale | Nguồn snapshot, không phải nguồn của phép tính |
| stale | boolean | Giữ cờ nguồn |
| fetched_at | UTC ISO 8601 | Giữ thời điểm fetch gốc |
| cache_key | string | Key nến nguồn |
| warning | string hoặc null | Giữ cảnh báo nguồn |
| evaluated_at | integer | UTC ms cố định một lần sau khi lấy snapshot |
| include_open | boolean | Chính sách yêu cầu |
| input_candles | integer | Số nến snapshot |
| eligible_candles | integer | Số nến được dùng sau lọc |
| excluded_candles | integer | input_candles - eligible_candles |
| series_start_time | integer hoặc null | open_time đầu chuỗi đã lọc |
| results | list IndicatorSeries | Một mục mỗi cặp, đúng thứ tự request |

Không có trạng thái tổng làm che mất các cặp thiếu dữ liệu riêng lẻ.
fetched_at chuyển sang ms bằng số học nguyên để so sánh; vẫn serialize ISO ở output.

## IndicatorSeries và điểm

IndicatorSeries gồm name, period, required_candles (N hoặc N+1), available_candles
(bằng eligible_candles), points (list IndicatorPoint), latest (IndicatorPoint).
IndicatorPoint gồm open_time, close_time (UTC ms), value (chuỗi thập phân hoặc null),
status (ok/insufficient_data), provisional (boolean).

Mỗi nến được chọn có một điểm kể cả warm-up. Points không rỗng thì latest bằng điểm
cuối, không phải giá trị hợp lệ gần nhất. Points rỗng thì latest có open_time,
close_time,value đều null, status=insufficient_data, provisional=false.
Trong points, timestamp luôn là integer, chỉ sentinel latest rỗng mới cho null.

SMA/EMA có N-1 điểm warm-up; RSI có N. available_candles là số toàn chuỗi,
không phải số đã đi qua ở từng point. Không lưu model này vào Redis.

## Trạng thái và cờ

- insufficient_data chuyển sang ok ngay khi đủ seed, không thay bằng 0.
- Closed khi close_time < min(evaluated_at, fetched_at_ms); bằng cutoff là chưa đóng.
- include_open=false loại mọi nến không closed, mọi point provisional=false.
- include_open=true giữ mọi nến: SMA đánh dấu nếu cửa sổ hiện tại có nến không closed;
  EMA/RSI đánh dấu nếu bất kỳ nến từ đầu đến điểm hiện tại không closed.
  Trong warm-up, áp dụng cùng nguyên tắc trên prefix đang có.
- stale không thay đổi theo việc tính lại, độc lập status và provisional.
- Không chuyển trạng thái qua request: mỗi lần seed lại, không update snapshot nguồn.
