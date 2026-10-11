# Hợp đồng HTTP: POST /indicators

Ngày: 2026-10-11. API dự kiến, chưa triển khai.
Request và response JSON; không cần API key, giống market data public hiện có.
Không thay GET /klines, /symbols, /health hoặc CLI.

## Yêu cầu

POST /indicators, Content-Type: application/json.

```json
{
  "symbol": "BTCUSDT",
  "interval": "1h",
  "limit": 300,
  "include_open": false,
  "indicators": [
    {"name": "sma", "period": 20},
    {"name": "sma", "period": 50},
    {"name": "ema", "period": 14},
    {"name": "rsi", "period": 14}
  ]
}
```

Chỉ indicators bắt buộc. Default symbol=BTCUSDT, interval=1h, limit=300,
include_open=false, period=14. Tên chỉ báo phải chữ thường chính xác; symbol cho
phép chữ thường và đổi uppercase. period/limit phải JSON integer, không chấp nhận
boolean, số dạng 14.0 hoặc chuỗi "14". Từ chối trường lạ, danh sách rỗng, tên lạ,
ngoài khoảng, cặp trùng sau áp dụng default. Toàn bộ validation trước market I/O.

Thị trường/host dùng cấu hình backend hiện có, không đổi bằng request.
Một request hợp lệ gọi luồng lấy snapshot đúng một lần; các retry bên trong client
vẫn theo chính sách hiện tại, không đồng nghĩa một HTTP upstream duy nhất.

## Thành công: HTTP 200

Schema đầy đủ và bất biến tại [data-model.md](../data-model.md).
Ví dụ dùng snapshot giả lập một nến, đủ SMA(1):

```json
{
  "market": "spot",
  "symbol": "BTCUSDT",
  "interval": "1h",
  "source": "cache",
  "stale": false,
  "fetched_at": "2026-10-11T01:00:01Z",
  "cache_key": "binance:spot:example0:klines:BTCUSDT:1h:1",
  "warning": null,
  "evaluated_at": 1791680402000,
  "include_open": false,
  "input_candles": 1,
  "eligible_candles": 1,
  "excluded_candles": 0,
  "series_start_time": 1791676800000,
  "results": [
    {
      "name": "sma",
      "period": 1,
      "required_candles": 1,
      "available_candles": 1,
      "points": [
        {
          "open_time": 1791676800000,
          "close_time": 1791680399999,
          "value": "2",
          "status": "ok",
          "provisional": false
        }
      ],
      "latest": {
        "open_time": 1791676800000,
        "close_time": 1791680399999,
        "value": "2",
        "status": "ok",
        "provisional": false
      }
    }
  ]
}
```

cache_key ở ví dụ chỉ minh họa, output thật giữ chính xác key nguồn.
Thiếu nến vẫn HTTP 200: value=null, status=insufficient_data.
Snapshot rỗng: points=[], latest có cả hai timestamp/value null, provisional=false.
Các số thập phân xuất dưới dạng string fixed-point, không dùng JSON number;
không bảo đảm số lượng chữ số 0 cuối. Sai số theo FR-009.

Metadata stale giữ nguyên kể cả tính ra giá trị ok. include_open=true có thể cho
provisional=true cả khi source=cache/binance và stale=false.
Không tự fetch bổ sung khi lọc bỏ nến hoặc chu kỳ lớn hơn dữ liệu.

## Lỗi

| HTTP | Điều kiện | Body và hành vi |
| --- | --- | --- |
| 422 | Body/chu kỳ/cặp trùng không hợp lệ | detail là danh sách lỗi validation FastAPI; không gọi market service |
| 400 | Binance từ chối symbol | Handler BinanceError hiện có: detail, retry_after |
| 418/429 | Cooldown/rate limit và không có fallback hợp lệ | Giữ detail, retry_after và header Retry-After hiện tại |
| 502 | Lỗi nguồn không được fallback | Giữ handler BinanceError và thông báo hiện tại |
| 503 | Redis lỗi | Giữ handler CacheError: detail |
| 502 | Snapshot đã nhận sai bất biến/nhận diện hoặc không tính được số hợp lệ | detail là object có code=invalid_indicator_data và message rõ ràng |

Lỗi invalid_indicator_data chỉ được ánh xạ trong endpoint mới, không đổi handlers
hoặc quy tắc fallback chung. Ví dụ:
```json
{"detail":{"code":"invalid_indicator_data","message":"Candles must be ordered and unique"}}
```

Dữ liệu upstream/cache bị service hiện có loại và refetch/fallback vẫn theo hành vi
cũ. Bộ tính chỉ kiểm tra snapshot cuối service trả về; không tạo retry/fallback mới.
Lỗi không được biến thành kết quả thiếu nến hoặc thành công từng phần.
