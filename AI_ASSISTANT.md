# AI phân tích cảnh báo và chatbot thị trường

Tính năng bổ sung ngày 15/10/2026, sử dụng OpenAI client đã có trong backend.
Model lấy từ `OPENAI_MODEL`, mặc định giữ `gpt-5-mini`.

## 1. Phân tích kèm tin Telegram

Khi một rule được scheduler hiện tại xác nhận kích hoạt, backend dùng chính
snapshot nến đóng của lần đánh giá đó để chuẩn bị phần phân tích AI:

- Ý nghĩa tín hiệu và các chỉ báo hỗ trợ/mâu thuẫn.
- Kịch bản tăng/giảm có điều kiện, dấu hiệu cần xác nhận và điểm vô hiệu hóa nếu có dữ liệu.
- Rủi ro, dữ liệu còn thiếu và lựa chọn chờ xác nhận.

Context gồm close price, tối đa 24 giá đóng gần nhất, SMA20/50/200, EMA12/26,
RSI14 và indicator của rule. AI không có order book, OHLCV đầy đủ hoặc tin tức.
Không yêu cầu AI tự tạo giá vào lệnh/stop/target khi snapshot không cung cấp cơ sở.

Phần phân tích được nối vào **cùng tin Telegram**, có nhãn `Phân tích AI` hoặc
`AI analysis`. Tin vẫn chứa rule, symbol, timeframe, giá trị/ngưỡng và thời gian nến gốc.
Toàn tin được giới hạn 4096 ký tự. AI không quyết định điều kiện kích hoạt.

Nếu AI thiếu cấu hình, bận, lỗi hoặc vượt timeout, hệ thống gửi cảnh báo gốc.
Sau khi AI trả lời, backend kiểm tra lại rule còn bật/đúng generation trước khi gửi.
Cơ chế chống trùng, rearm và chính sách không retry Telegram được giữ nguyên.

Phạm vi scheduler chưa thay đổi: chỉ SMA/EMA/RSI so với ngưỡng số bằng
gt/gte/lt/lte trên nến đóng 1h/1d/1w. Cross/Close/target indicator vẫn bị bỏ qua.
`trigger_type` và `notifications` chưa điều khiển cách gửi Telegram.

## 2. Chatbot trên dashboard

Nhấn **AI assistant / Trợ lý AI** ở góc dưới bên phải để mở chat.
Chat theo ngôn ngữ EN/VI đang chọn. Có các câu hỏi gợi ý để phân tích cặp,
giải thích RSI/đường trung bình và tìm hiểu Telegram.

Mỗi câu hỏi gửi symbol và timeframe đang chọn tới backend. Backend tự lấy
snapshot 300 nến, loại nến mở, tính chỉ báo và đọc tối đa 10 rule cùng cặp/khung.
FE không được cung cấp giá hoặc kết quả indicator làm dữ liệu đáng tin cậy.
Rule trong ngữ cảnh chat được gắn `evaluation_status=not_evaluated`: đây là cấu hình
đã lưu, chưa phải tín hiệu kích hoạt. `has_indicator_reading` chỉ rõ có kết quả chỉ
báo tương ứng trong snapshot hay không; lưu một indicator chưa hỗ trợ không làm nó được tính.
Tin trả lời có nguồn cặp/khung và thời gian đóng nến; stale/thiếu nến được ghi rõ.
Nếu đổi cặp khi đang chờ, nguồn trên câu trả lời vẫn ghi cặp đã dùng cho lần hỏi đó.

Chat giữ hội thoại trong bộ nhớ tab, truyền tối đa 8 lượt trước, mỗi lượt tối đa
2000 ký tự. Reload sẽ xóa cuộc trò chuyện. Nội dung được hiển thị như văn bản,
không thực thi HTML hoặc JavaScript từ model.

Chatbot chỉ đọc và giải thích. Nó không đặt lệnh, sửa/xóa rule, gửi tin hoặc có
quyền truy cập tài khoản giao dịch. Các hành động trên dashboard vẫn do người dùng thao tác.

## 3. Cấu hình backend

Thêm vào `.env` tại gốc, không đặt key trong `FE/.env` hoặc các biến `VITE_*`:

```dotenv
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5-mini
OPENAI_TIMEOUT_SECONDS=60
AI_ENABLED=true
TELEGRAM_AI_ENABLED=true
TELEGRAM_AI_LANGUAGE=vi
TELEGRAM_AI_TIMEOUT_SECONDS=8
AI_CHAT_REQUESTS_PER_MINUTE=6
```

- `OPENAI_API_KEY`: điền API key của tài khoản dùng cho tính năng này.
- `AI_ENABLED=false`: tắt cả chat và phân tích AI, giữ các chức năng market/rule.
- `TELEGRAM_AI_ENABLED=false`: chỉ tắt phần phân tích Telegram, chat vẫn dùng được.
- `TELEGRAM_AI_LANGUAGE`: `vi` hoặc `en`; tách khỏi ngôn ngữ của từng tab FE.
- `TELEGRAM_AI_TIMEOUT_SECONDS`: mặc định 8 giây, tối đa 60; có thể đặt 45 giây cho model chậm.
  AI quá thời gian vẫn dùng cảnh báo gốc; tăng giá trị này sẽ kéo dài thời gian chờ tin.
- `AI_CHAT_REQUESTS_PER_MINUTE`: mặc định 6 request/phút dùng chung trong một process.

Để gửi Telegram vẫn cần `TELEGRAM_ENABLED=true`, bot token và chat ID như trước.
Không tự bật Telegram để thử chat. Mỗi request AI có thể phát sinh chi phí trên tài khoản API.
Backend giới hạn hai request AI đồng thời, không retry tự động và giới hạn output tokens.
Đây là giới hạn trong process cho bản demo, chưa phải hệ thống quota/xác thực nhiều người dùng.

Sau khi sửa cấu hình, khởi động lại backend. Docker Compose đã truyền các biến AI
ở trên vào container; nếu dùng Docker, build lại bằng `docker compose up -d --build --wait`.
Chỉ chạy một API worker/replica cho scheduler Telegram hiện tại.

## 4. API

`GET /ai/status` trả `available` và `telegram_test_available` theo cấu hình, không gọi model
và không chứng minh API key đã được OpenAI chấp nhận.

`POST /ai/chat`:

```json
{
  "message": "Phân tích tín hiệu và điều kiện cần xác nhận",
  "symbol": "BTCUSDT",
  "interval": "1h",
  "language": "vi",
  "history": []
}
```

Trả `answer`, `context`, `model`, `warnings`, `generated_at`.
422 cho request không hợp lệ; 503 khi AI tắt/thiếu cấu hình; 429 khi quá giới hạn;
502 khi AI hoặc dữ liệu chỉ báo lỗi. Lỗi provider không đưa key/nội dung lỗi thô ra FE.
Lỗi nguồn Binance/Redis giữ contract hiện có.

Gọi theo [OpenAI Responses API](https://developers.openai.com/api/reference/python/resources/responses/methods/create),
với `store=false` và giới hạn output. Prompt/history/context cần thiết vẫn được gửi tới OpenAI
để xử lý; không gửi bot token, chat ID hoặc API key trong nội dung prompt.

## 5. Nút gửi thử AI → Telegram (thu gọn trên FE)

Mở **AI assistant / Trợ lý AI** → liên kết nhỏ **Connection check / Kiểm tra kết nối**
ở cuối khung chat. Khóa được tự nhận từ `.env` gốc → **Prepare message / Chuẩn bị gửi** →
**Confirm and send / Xác nhận gửi**. Chỉ nút xác nhận cuối mới gọi AI và gửi tin thật.
Tin là bản nhận định thị trường thông thường, có tiêu đề in đậm, cặp/khung, giá đóng,
nguồn dữ liệu và phân tích AI; không có nhãn TEST/MANUAL và không giả làm rule kích hoạt.
Ngôn ngữ dùng EN/VI đang chọn lúc mở mục kiểm tra.

Cấu hình trong `.env` gốc (không dùng `FE/.env`):

```dotenv
TELEGRAM_TEST_ENABLED=true
TELEGRAM_TEST_KEY=<chuoi-ngau-nhien-24-den-256-ky-tu>
TELEGRAM_BOT_TOKEN=<bot-token-cua-ban>
TELEGRAM_CHAT_ID=<chat-id-nhan-tin>
OPENAI_API_KEY=<openai-api-key-cua-ban>
AI_ENABLED=true
# Có thể giữ tắt watcher khi chỉ muốn gửi thử thủ công:
TELEGRAM_ENABLED=false
```

Tạo khóa ngẫu nhiên bằng `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
Khóa kiểm thử là khóa riêng, không phải bot token hoặc OpenAI API key. Không commit `.env`.
Vite dev/preview đọc khóa từ `.env` gốc trên máy chủ và thêm header khi chuyển tiếp
request gửi thử tới backend. React không đọc/nhận khóa, không có ô nhập khóa.
Proxy dùng middleware phía server của [Vite 5](https://v5.vite.dev/config/server-options#server-proxy).
Proxy chỉ tự thêm khóa cho POST JSON từ cùng origin localhost/127.0.0.1/[::1],
với kết nối loopback. Khi mở web qua IP LAN/domain, gửi thử tự động nhận khóa bị chặn.
Các API market/chat thông thường không được thêm khóa này.
Backend chỉ gửi tới chat đã cấu hình; FE không thể truyền chat ID hoặc nội dung tùy ý.
Bot cần được nhấn Start trong chat riêng hoặc có quyền gửi trong nhóm đã chọn.

Sau khi sửa `.env`, chạy `docker compose up -d --build --wait`, khởi động lại frontend
bằng `npm.cmd run dev --prefix FE`, rồi tải lại trang.
Máy local đã có khóa ngẫu nhiên trong `.env`; không cần sao chép vào giao diện.
Trên máy khác cần tự cấu hình credentials và khóa riêng. Nếu thiếu khóa, Telegram hoặc AI,
liên kết kiểm tra sẽ không xuất hiện. `.env.example` mặc định tắt tính năng này.
Production chỉ phục vụ thư mục `dist` không chạy Vite proxy; cần một proxy có xác thực
phía server nếu muốn dùng chức năng tương tự sau khi deploy. Không đưa khóa vào `VITE_*`.
Khi xong có thể đặt `TELEGRAM_TEST_ENABLED=false` rồi khởi động lại backend để ẩn mục này.

Endpoint `POST /ai/telegram-test` không hiện trong Swagger, nhưng vẫn cần xác thực
`X-Telegram-Test-Key` và `confirmed: true`; việc ẩn nút không thay thế kiểm tra quyền.
Body gồm UUID `request_id`, `symbol`, `interval`, `language`, `confirmed`.
Redis giới hạn một lần/phút, giữ mã chống gửi trùng 24 giờ qua cả lần khởi động lại.
Không xóa dữ liệu Redis khi đang chờ kết quả. Sau 24 giờ, cùng mã có thể được coi là lần mới.
Không tự retry Telegram. Trạng thái `accepted` nghĩa là Telegram API chấp nhận, chưa chứng minh
người nhận đã đọc; `failed` là bị từ chối; `unknown`/`pending` cần kiểm tra chat trước khi gửi thêm.
Nếu mất phản hồi FE, giao diện báo chưa rõ kết quả để tránh hiểu nhầm rằng chưa gửi.

Đây là kiểm tra luồng **nến → AI → Telegram** thủ công. Nó không đánh giá điều kiện rule,
không sửa rule/trạng thái chống trùng của scheduler và không bật watcher.
Phân tích lỗi sẽ không gửi một tin giả làm kết quả AI thành công.
Nút thử dùng timeout AI thông thường (`OPENAI_TIMEOUT_SECONDS`, mặc định 60 giây),
khác timeout ngắn cho phần AI nối vào cảnh báo tự động.

## 6. Kiểm thử

Các test mới dùng model, HTTP và Redis giả, không gửi Telegram thật:

```powershell
$env:RUN_TELEGRAM_LIVE_TESTS='0'
$env:RUN_OPENAI_LIVE_TESTS='0'
python -m pytest BE/tests/test_trading_assistant.py -q
python -m pytest BE/tests/test_telegram_manual_test.py -q
npm.cmd test --prefix FE
npm.cmd run build --prefix FE
```

Bao gồm dữ liệu nến đóng, thiếu dữ liệu/stale, history/language, lỗi/key redaction,
rate/concurrency limit, timeout AI, cảnh báo gốc và thay đổi rule trong lúc chờ AI.
Trên Windows, test chuẩn bị asyncio runner trước guard chặn kết nối mạng nội bộ của test.
Các live test vẫn cần opt-in riêng; không coi mock là bằng chứng đã gửi tin thật.

Kết quả ngày 15/10/2026 sau khi đồng bộ: bộ backend mock đạt 356 test, 4 test OpenAI live được
skip; 22 test FE đạt và production build đạt. Test Binance WebSocket live và
Telegram live được loại khỏi lần chạy hồi quy này. Một lần kiểm tra riêng dùng
`gpt-5-mini` và 300 nến Binance BTCUSDT/1h thật đã trả nhận định tiếng Việt.
Sau khi Docker engine sẵn sàng, đã thử câu hỏi tiếng Việt ngay trên FE qua API,
đọc nến Binance và rule từ Redis, nhận câu trả lời OpenAI và hiển thị nguồn cặp/khung/
thời gian nến trên giao diện. Đã làm rõ rule được liệt kê chỉ là cấu hình, không phải
kết quả đã kích hoạt; indicator chưa hỗ trợ được đánh dấu không có số liệu.
Watcher Telegram được giữ tắt trong lần chạy local này. Đã bật riêng phần gửi thử thủ công,
kiểm tra EN/VI, kích thước khung ở viewport điện thoại và xác minh trên FE rằng khóa giả
bị từ chối trước khi gọi AI/gửi tin. Chưa nghiệm thu gửi tin AI qua Telegram thật;
người dùng thực hiện bước xác nhận cuối để gửi tới chat đã cấu hình.

Sau cập nhật tự nhận khóa, đã kiểm tra proxy local tới backend thật bằng một mã
được đặt sẵn trạng thái pending trong Redis, nên không gọi AI/gửi Telegram.
Backend xác thực thành công và trả trạng thái chống trùng. Đã kiểm tra khóa không
có trong bundle JavaScript của bản build; test proxy chặn origin khác, kết nối từ xa,
thiếu origin, sai content type và thiếu cấu hình. Giao diện bỏ ô nhập khóa và giữ nút xác nhận.

## 7. Đồng bộ code mới đến `8022139` (15/10/2026)

- Giữ các commit mới: ô nhập số có phân cách hàng nghìn, tiêu đề Telegram in đậm,
  tự tạo lại mô tả rule khi điều kiện đổi, `npm start`, `PORT`, `VITE_ALLOWED_HOSTS`.
- Ghép formatter mới với AI: chỉ tiêu đề được in đậm, mô tả không bị lặp, dành chỗ
  cho AI trước khi cắt mô tả quá dài để toàn tin không vượt 4096 ký tự.
- Nút **Kiểm tra tất cả luật** kiểm tra điều kiện ngay trên nến đóng mới nhất và
  có thể gửi nhiều tin thật. Cần `TELEGRAM_ENABLED=true` để watcher sẵn sàng, đồng
  thời `TELEGRAM_TEST_ENABLED=true`, `TELEGRAM_TEST_KEY` cho quyền gửi thủ công.
  API `POST /telegram/trigger` nhận `request_id` UUID và `confirmed: true`, cần header
  khóa giống API gửi thử AI. Vite tự thêm header cho dashboard local; remote/domain
  không được tự cấp quyền bằng khóa local.
- Có xác nhận trên FE và chặn bấm lặp. Backend giữ kết quả/mã yêu cầu 24 giờ, giới
  hạn một lần/phút dùng chung với nút gửi thử AI. Nếu lần gửi bị ngắt giữa chừng,
  mã giữ trạng thái pending; không chạy lại cả batch và gửi trùng các tin đã đi.
- Tin rule thủ công dùng định dạng thông thường, dùng cùng snapshot để tạo phân tích AI.
  AI lỗi/bận/timeout vẫn gửi cảnh báo gốc. Sau khi AI trả lời, kiểm tra lại rule còn
  bật, còn tồn tại và điều kiện không đổi. Tôn trọng thời gian chờ khi Telegram rate limit.
- Kết quả FE tách rõ Telegram chấp nhận, từ chối, chưa xác nhận, bỏ qua và hủy.
  Gửi thủ công không cập nhật latch của scheduler: có thể nhận thêm tin theo lịch
  cho cùng điều kiện, đây là hai lần kiểm tra riêng.
- Sửa form edit để giữ target chỉ báo của rule cũ thay vì đổi ngầm sang số 30.
  Target cũ hiển thị chỉ đọc; chọn template số là thao tác đổi điều kiện rõ ràng.
- Compose tiếp tục mặc định tắt watcher như `.env.example`; chỉ bật khi cấu hình
  `TELEGRAM_ENABLED=true`. `REDIS_PASSWORD` được dùng đồng nhất cho Redis, healthcheck
  và URL của backend. Máy cũ chưa có biến này dùng giá trị fallback tương thích.

Các thay đổi AI chưa commit trước khi đồng bộ được giữ bằng Git stash dự phòng;
main đã fast-forward tới `8022139`, không tạo commit hoặc push trong lần rà soát này.

Kiểm tra sau đồng bộ: 356 test BE đạt, 4 test OpenAI live skip; 22 test FE và
production build đạt, Ruff cho các file BE được rà soát đạt. Docker API/Redis healthy.
Đã khởi động lại tiến trình frontend để nhận đủ proxy mới sau pull, kiểm tra hai
đường gửi thủ công xác thực đúng bằng khóa tự nhận. Không gọi AI/gửi Telegram thật
trong lần kiểm tra này; watcher local vẫn tắt, nút gửi thử AI độc lập vẫn sẵn sàng.
Trên UI đã kiểm tra xác nhận batch, target SMA(200) của rule cũ và nhập `82,200.06`.


## 8. Định dạng tin Telegram và múi giờ

Tin nhận định gửi từ dashboard và tin rule (bấm gửi/theo lịch) dùng chung formatter.
Tiêu đề in đậm bằng Telegram entities; nội dung là plain text, không bật parse_mode.
Không thêm nhãn TEST/MANUAL vào tin nhận được. Tin nhận định độc lập có tiêu đề
“BTCUSDT · Nhận định thị trường”; tin rule giữ “Rule #id: mô tả” của hệ thống.

`TELEGRAM_TIMEZONE=Asia/Ho_Chi_Minh` mặc định hiển thị UTC+07:00; có thể chọn `UTC`.
Biến chỉ đổi thời gian trên tin nhắn. Cron, timestamp lưu Redis và phép lọc nến đóng
vẫn dùng UTC, không cộng bảy giờ vào lịch chạy hoặc timestamp gốc.

Các dòng Mở nến, Đóng nến và Gửi lúc dùng `dd/MM/yyyy HH:mm:ss`. Tin nhận định còn
có Cập nhật dữ liệu và Nguồn (Binance/Redis cache); nếu dùng cache cũ thì ghi rõ
bằng lời thay vì `Stale: True/False`. Thời gian gửi lấy sau khi AI hoàn tất, không
nhầm với thời gian đóng nến; giờ thiếu/không hợp lệ hiển thị dấu —.
Nến ngày Binance có thể mở lúc 07:00 và đóng 06:59:59 ngày tiếp theo theo giờ Việt Nam.
Chỉ đổi timezone hiển thị, không chuyển thành nến đóng theo nửa đêm Việt Nam.

Phần AI được yêu cầu không nhắc lại timestamp trong thân bài để tránh trộn UTC
với giờ hiển thị của header. Tiêu đề được rút gọn và phần phân tích cắt ở cuối nếu
cần; bảo toàn các dòng dữ liệu/thời gian, kiểm tra giới hạn 4096 theo cả UTF-16
để các tin có emoji cũng không vượt kích thước dự kiến.

Tải lại FE để thấy nhãn “Gửi nhận định qua Telegram”. Khi sửa timezone trong .env,
build/khởi động lại backend bằng `docker compose up -d --build --wait`.
Tên env/API có chữ TEST được giữ để tương thích cấu hình cũ, chỉ nội dung hiển thị đổi.

Kiểm tra phiên bản định dạng mới: 368 test BE đạt, 4 live test skip; 22 test FE,
production build và Ruff đạt. Backend local đã chạy lại với `Asia/Ho_Chi_Minh`.
Đã tạo bản xem trước từ nến thật qua API local; không gọi model hay gửi Telegram thật
trong lần chỉnh định dạng này.

## 9. Bật Telegram và nghiệm thu rule thật ngày 15/10/2026

Theo yêu cầu bật gửi tự động của người dùng, cấu hình local hiện đặt
`TELEGRAM_ENABLED=true`, `TELEGRAM_AI_ENABLED=true`, `TELEGRAM_AI_TIMEOUT_SECONDS=45`.
Giới hạn cấu hình timeout AI được mở tới 60 giây; 33 test cấu hình/AI liên quan đạt.
Lần kiểm tra đầu không có AI đã được chặn, không gửi cảnh báo trống nhận định.

Đã tạo rule #4: BTCUSDT, 1H, RSI(14) >= 0, nến đóng, được bật và hết hạn lúc
22:32 ngày 15/10/2026 giờ Việt Nam. Ngưỡng 0 dùng để kiểm tra đường gửi.
Các rule cũ giữ nguyên cấu hình.

Lần kiểm tra riêng rule #4 bằng dữ liệu Binance thật, OpenAI thật và Telegram thật:
1 rule thỏa điều kiện, 1 tin được Telegram API chấp nhận, có phần Phân tích AI,
giờ UTC+07:00, không có nhãn TEST/MANUAL. Đây là lượt kiểm tra ngay qua cùng hàm
đánh giá/gửi rule, chưa phải bằng chứng lần cron tương lai đã chạy.
Tin thử ngay không thay đổi latch của lịch tự động, nên lần quét theo giờ kế tiếp
có thể gửi thêm một cảnh báo; sau đó điều kiện giữ đúng sẽ không gửi lặp theo lịch.
