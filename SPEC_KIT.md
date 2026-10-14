# Hướng dẫn sử dụng Spec Kit cho dự án Binance

## 1. Spec Kit dùng để làm gì?

Spec Kit giúp bạn và AI thống nhất yêu cầu trước khi viết code. Mỗi tính năng đi
qua các bước: đặc tả yêu cầu (spec), kế hoạch kỹ thuật (plan), danh sách công việc
(tasks), triển khai và kiểm tra kết quả.

Dự án đã tích hợp **Spec Kit 1.1.3**, dành cho **Codex**, sử dụng script Bash.
Việc khởi tạo chưa tạo đặc tả tính năng và không tự chạy ứng dụng Binance.

## 2. Mở đúng thư mục và kiểm tra công cụ

Mở phiên Codex mới tại thư mục chứa `BE/`, `FE/`, `compose.yaml` và tài liệu này
để nhận các skill của dự án. Trên máy hiện tại, đường dẫn là:

```text
/Users/jichangwook/AI_Project/binance-rule-based-alert/binance-rule-based-alert
```

Phân biệt hai loại lệnh:

- **Lệnh terminal** như `specify version`: kiểm tra hoặc cài công cụ.
- **Lời nhắc chat Codex** bắt đầu bằng `$speckit-...`: yêu cầu AI thực hiện một
  bước. Không nhập các lời nhắc này vào terminal.

Kiểm tra trong terminal:

```sh
specify version
specify integration list
specify check
```

Máy này đã cài `uv` qua Homebrew và `specify-cli` trong môi trường riêng.
`uv tool update-shell` đã thêm đường dẫn công cụ vào `~/.zshenv`.
Nếu terminal không tìm thấy `specify`, mở terminal mới.

Khi cần cài cùng phiên bản trên máy khác đã có `uv`:

```sh
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@v1.1.3
```

Không cần chạy lại `specify init` trên dự án hiện tại vì đã khởi tạo xong.

## 3. Các file quan trọng

| Đường dẫn | Vai trò |
| --- | --- |
| `.agents/skills/` | Skill Spec Kit dành cho Codex; nên lưu trong Git |
| `.specify/templates/` | Mẫu đặc tả, kế hoạch, công việc và checklist |
| `.specify/scripts/bash/` | Script hỗ trợ quy trình |
| `.specify/memory/constitution.md` | Nguyên tắc chung; ban đầu là mẫu chưa điền |
| `.specify/workflows/` | Cấu hình quy trình đã cài |
| `specs/` | Tài liệu từng tính năng, được tạo khi sử dụng quy trình |

Tài liệu tính năng thường gồm `spec.md`, `plan.md` và `tasks.md` trong thư mục
riêng dưới `specs/`. Tùy tính năng, có thể có nghiên cứu, mô hình dữ liệu hoặc
hợp đồng API bổ sung.

## 4. Thiết lập nguyên tắc chung

Thực hiện khi bắt đầu áp dụng Spec Kit; sau đó cập nhật khi nguyên tắc dự án
thay đổi. Nhập vào **chat Codex**:

```text
$speckit-constitution Xây dựng nguyên tắc dự án dựa trên README.md,
BE/pyproject.toml và FE/package.json. Giữ tương thích API dữ liệu thị trường
hiện có, timestamp UTC milliseconds, độ chính xác của giá, phân biệt Spot/Futures,
TTL cache và metadata dữ liệu cũ. Tái sử dụng kiến trúc hiện tại và test backend
dùng mock. Phân biệt chức năng đã có với indicator, rule engine và lưu trữ
đang dự kiến phát triển. Viết tài liệu bằng tiếng Việt.
```

Đọc lại `.specify/memory/constitution.md`: các nguyên tắc phải phù hợp với dự án
và không thêm yêu cầu ngoài phạm vi bạn muốn làm.

## 5. Quy trình cho một tính năng

Thực hiện từng bước, đọc kết quả rồi mới chuyển bước tiếp theo. Ví dụ dưới đây
là tính chỉ báo SMA, EMA và RSI, chưa phải yêu cầu đã được triển khai.

### Bước 1: Mô tả yêu cầu với specify

Tập trung vào kết quả mong đợi và giới hạn phạm vi:

```text
$speckit-specify Bổ sung tính SMA, EMA và RSI theo phương pháp Wilder từ nến
Binance. Làm rõ số nến tối thiểu, kết quả khi thiếu dữ liệu và việc sử dụng nến
chưa đóng. Giữ hành vi API dữ liệu thị trường và cache hiện tại. Lần này chỉ
tính chỉ báo, chưa triển khai rule engine hoặc gửi cảnh báo.
Viết đặc tả bằng tiếng Việt.
```

Đọc `spec.md`, kiểm tra phạm vi, tình huống sử dụng và tiêu chí nghiệm thu:
làm thế nào để biết tính năng đã đúng và đủ?

### Bước 2: Làm rõ yêu cầu với clarify

```text
$speckit-clarify
```

Trả lời câu hỏi về các điểm còn mơ hồ, ví dụ chỉ dùng nến đã đóng hay cả nến
đang chạy. Thống nhất các quy tắc nghiệp vụ quan trọng trước khi lập kế hoạch.

### Bước 3: Lập kế hoạch kỹ thuật với plan

```text
$speckit-plan Dựa trên spec đã thống nhất, lập kế hoạch theo kiến trúc hiện có:
backend Python/FastAPI trong BE/, Redis để cache và frontend React/Vite trong FE/.
Tái sử dụng Binance client và schema dữ liệu hiện có. Nêu cách tính chỉ báo,
xử lý thiếu nến và kiểm thử bằng dữ liệu cố định. Chỉ thay đổi các phần cần thiết
cho phạm vi đã chốt. Viết kế hoạch bằng tiếng Việt.
```

Đọc `plan.md` và tài liệu bổ sung nếu có. Kiểm tra module sẽ sửa, dependency
dự kiến thêm, ảnh hưởng API và cách kiểm thử.

### Bước 4: Chia công việc với tasks

```text
$speckit-tasks
```

Đọc `tasks.md`. Các đầu việc cần có thứ tự thực hiện, file liên quan và phần
kiểm thử tương ứng.

### Bước 5: Kiểm tra tính nhất quán với analyze

```text
$speckit-analyze
```

Đối chiếu yêu cầu, kế hoạch và công việc để tìm phần thiếu hoặc mâu thuẫn.
Xử lý các vấn đề quan trọng trước khi yêu cầu viết code.

Có thể dùng thêm `$speckit-checklist` để rà soát chất lượng yêu cầu.
Checklist tài liệu không thay thế kiểm thử code.

### Bước 6: Triển khai với implement

Chỉ nhập lời nhắc này khi đã xem và đồng ý với spec, plan và tasks:

```text
$speckit-implement
```

Đây là bước AI thực hiện các đầu việc và thay đổi code. Nếu có giới hạn như
chưa được chạy Docker, cài dependency hay khởi động dịch vụ, ghi rõ trong cùng
lời nhắc.

### Bước 7: Đối chiếu kết quả với converge

```text
$speckit-converge
```

Kiểm tra code so với tài liệu và tìm phần còn thiếu. Nếu có công việc mới,
đọc lại rồi tiếp tục `implement` và `converge` đến khi đáp ứng yêu cầu.
Xem kết quả test và các hạn chế được báo cáo trước khi coi tính năng hoàn tất.

## 6. Áp dụng cho dự án Binance

Theo README tại thời điểm tích hợp, backend đã cung cấp dữ liệu thị trường qua
FastAPI và Redis; frontend React mặc định dùng dữ liệu mock. Indicator, lưu rules
và lịch sử alerts là các phần dự kiến bổ sung. Đối chiếu lại code khi bắt đầu
tính năng mới vì trạng thái này có thể thay đổi.

Thứ tự phát triển đề xuất:

1. Tính chỉ báo SMA, EMA, RSI.
2. Đánh giá điều kiện rule và xử lý giao cắt.
3. Lưu rules, alerts và chống trùng cảnh báo.
4. Kết nối frontend với API thật.

Mỗi phần nên có spec riêng với phạm vi đủ nhỏ để kiểm tra. Không cần viết lại
ứng dụng hoặc tạo spec hồi tố cho mọi chức năng đang có.

## 7. Kiểm thử khi triển khai

Sau khi cài dependency ứng dụng và kích hoạt môi trường Python phù hợp, chạy
các kiểm tra liên quan từ thư mục gốc dự án:

```sh
python -m pytest BE/tests -q
python -m ruff check --config BE/pyproject.toml BE/app BE/tests
npm --prefix FE run build
```

Các lệnh lần lượt kiểm thử backend, kiểm tra quy tắc code Python và build
frontend. Chúng không phải các bước đã chạy khi cài Spec Kit. Cài Spec Kit
không tự cài dependency ứng dụng hay khởi động API, frontend, Redis hoặc Docker.

## 8. Prompt từng bước cho chức năng Telegram

Phạm vi đã chốt: quét rule đang bật sau mỗi lần đóng nến 1h/1d/1w và gửi Telegram khi
giá trị indicator thỏa gt/gte/lt/lte với ngưỡng số, không cần Refresh hoặc frontend.
Backend theo dõi phải đang chạy. Đây là phần mở rộng ngoài prototype gốc.

Quy tắc gửi đã được xác nhận:

- Khi bật rule, chờ lần đóng nến tiếp theo; nếu điều kiện hợp lệ đầu tiên đúng thì gửi một lần.
- Khi điều kiện vẫn đúng, không gửi lặp theo từng cập nhật hoặc định kỳ.
- Khi điều kiện sai, cho phép kích hoạt lại; lần tiếp theo đúng mới tạo tin mới.
  Rearm của gt/gte/lt/lte lần lượt là <= / < / >= / > ngưỡng.
- Rule tắt không tạo thông báo mới. Không dùng dữ liệu thiếu/lỗi để coi như
  điều kiện đã sai và đặt lại trạng thái.

Ví dụ gte ngưỡng 70, giá trị tại các lần đóng nến liên tiếp là 68 -> 70 -> 75 -> 69 -> 71:
gửi tại 70 và 71. Bỏ qua biến động trong nến. Quét một lần mỗi nến không có nghĩa
là gửi một tin mỗi nến: quy tắc chống gửi lặp vẫn giữ nguyên.

Amendment 2026-10-14 theo yêu cầu người dùng: thêm >, <, <= bên cạnh >=;
Value hai chữ số thập phân, ví dụ `Value: 51.66 >= 40`, bỏ Threshold.
Open/Close yyyy-mm-dd HH:MM:SS với nhãn UTC; chỉ format hiển thị, so sánh/lưu
vẫn Decimal đầy đủ và UTC milliseconds. Không thêm cross_above/cross_below.
Lịch sử quyết định gte-only giữ tại Clarifications trong spec, không áp dụng
để thu hẹp lại yêu cầu hiện hành. Một tin thực tế không thay nghiệm thu toàn luồng.

Giới hạn thiết kế để tránh dư thừa: ưu tiên một tiến trình theo dõi và một nơi
nhận Telegram cấu hình qua môi trường. Chỉ triển khai nguồn dữ liệu đã chọn,
dùng job theo mốc đóng nến; không xây luồng WebSocket theo dõi nội nến. Không thêm hệ thống nhiều
người dùng, broadcast, dashboard lịch sử, framework rule tổng quát, hàng đợi
phân tán hoặc cơ chế nhiều worker. Nếu yêu cầu đã chốt thật sự cần mở rộng,
phải nêu lý do trước khi đưa vào plan. Các giới hạn này là định hướng triển khai
tối giản; không thay thế những quyết định nghiệp vụ cần làm rõ ở bước 2.

Nhập từng prompt bên dưới vào **chat Codex**, không phải shell. Đọc kết quả trước
khi chuyển bước. Đây chỉ là hướng dẫn; các prompt chưa được thực thi khi thêm
mục này. Giữ nhánh `feat/telegram-notifications` và dùng thư mục feature
`specs/002-telegram-notifications` xuyên suốt.

### Bước 1: Tạo đặc tả

```text
$speckit-specify Tạo đặc tả bằng tiếng Việt cho chức năng tích hợp gửi thông báo
Telegram trong dự án Binance hiện tại.
Dùng SPECIFY_FEATURE_DIRECTORY=specs/002-telegram-notifications
và giữ nhánh feat/telegram-notifications.
Lưu feature_directory vào .specify/feature.json để các bước sau chọn đúng feature.
Nếu thư mục đã có tài liệu, đọc và cập nhật thay vì ghi đè mù hoặc tạo feature trùng.

Đọc README, hiến chương và code hiện tại trước khi xác định phần cần bổ sung.
Telegram là phần mở rộng ngoài prototype gốc. Phạm vi lần này: schedule job sau mỗi lần đóng nến 1h, 1d, 1w;
mỗi mốc quét một lần các rule đang bật cùng timeframe, tính giá trị indicator theo symbol/period/timeframe của rule,
so sánh ngưỡng số bằng gt/gte/lt/lte và tự gửi Telegram, không phụ thuộc nút Refresh
hay frontend đang mở. Backend theo dõi phải đang chạy.

Quy tắc đã chốt: chờ lần đóng nến tiếp theo sau khi bật rule; lần quét hợp lệ
đầu tiên nếu điều kiện đúng thì gửi một lần;
giữ nguyên trạng thái đúng thì không gửi lặp. Chỉ khi có quan sát hợp lệ làm
điều kiện sai mới rearm, rồi gửi khi điều kiện đúng trở lại. Rule tắt không
tạo thông báo mới. Không coi lỗi/thiếu dữ liệu là điều kiện sai.
Đây là so sánh có ghi nhớ trạng thái, không đổi thành cross_above/cross_below.
Value hiển thị hai chữ số, ký hiệu đúng operator, bỏ Threshold; Open/Close
yyyy-mm-dd HH:MM:SS UTC. Tính toán/lưu giữ Decimal đầy đủ và UTC milliseconds.
Tin cần có rule, symbol, timeframe, indicator/period, giá trị thực tế, ngưỡng
và thời gian nến đã đóng. Không đánh giá nến đang chạy. Cùng rule/nến không
xử lý hiệu lực hai lần nếu job bị gọi lặp; không lấy nến cũ thay nến vừa đóng.

Tái sử dụng khả năng gửi Telegram đã có nếu phù hợp. Khi chưa cấu hình Telegram,
các chức năng hiện tại vẫn hoạt động. Gửi thử chỉ là cách nghiệm thu phụ, không
thay thế luồng gửi tự động; không bắt buộc xây UI/API/CLI gửi thử riêng.
Không để lộ token qua frontend, log hoặc thông báo lỗi. Không coi timeout
là bằng chứng tin chưa được gửi, không hứa chống trùng nếu chưa có cơ chế.
Yêu cầu test tự động bằng mock, không gửi tin thật khi chạy test thường.
Ghi rõ giả định và câu hỏi cần làm rõ. Chỉ tạo đặc tả, chưa triển khai code.
Giữ phạm vi nhỏ: gt/gte/lt/lte với ngưỡng số và các indicator hiện có hỗ trợ;
không xây mọi toán tử hay tự thêm chỉ báo mới. Không đổi nghĩa rule cũ.
```

Đọc `spec.md` và checklist yêu cầu. Kiểm tra có đủ luồng theo dõi -> tính chỉ báo
-> đánh giá -> chống gửi lặp -> gửi Telegram; không mở rộng sang nhiều người dùng.

### Bước 2: Làm rõ cách sử dụng

```text
$speckit-clarify Rà soát specs/002-telegram-notifications/spec.md.
Giữ lịch quét sau đóng nến 1h/1d/1w và chống gửi lặp đã xác nhận; không hỏi lại.
Làm rõ phần còn lại: xử lý các rule cũ có candle_mode=include_current hoặc
có operator ngoài gt/gte/lt/lte hoặc target là indicator thay vì số. Không âm thầm đổi
ý nghĩa rule cũ. Làm rõ trạng thái khi sửa ngưỡng, tắt/bật lại, restart, mất mạng
và phục hồi kết nối; có gửi bù tín hiệu đã bỏ lỡ hay không.
Chốt nơi nhận, nội dung tin, định nghĩa gửi thành công và retry khi timeout
hoặc bị rate limit. Phân biệt chống kích hoạt lặp với retry vận chuyển tin.
Đề xuất phương án phù hợp code, ghi câu trả lời vào spec bằng tiếng Việt.
Phân biệt yêu cầu đã chốt và đề xuất chưa xác nhận. Nếu chưa chốt cách xử lý
rule cũ hoặc lỗi gửi/khôi phục, chưa coi spec sẵn sàng implement.
Chưa viết code.
```

Trả lời các câu hỏi và đọc lại spec. Hiến chương đã có nên không cần tạo lại;
nếu mô tả hiện trạng bị cũ, ghi nhận và đề xuất sửa phần liên quan riêng.

### Bước 3: Lập kế hoạch kỹ thuật

```text
$speckit-plan Lập kế hoạch từ specs/002-telegram-notifications/spec.md đã làm rõ.
Đọc BE/app/service/telegram_client.py, BE/app/config.py, BE/app/errors.py,
BE/app/main.py và BE/tests/test_telegram_client_live.py trước khi thiết kế.
Đọc thêm BE/app/rules.py, BE/app/models.py, BE/app/indicators.py và luồng FE
bật/tắt rules để không nhầm rule lưu trong trình duyệt với rule backend.
Tái sử dụng Python, httpx và pydantic-settings hiện có; chỉ thêm dependency
khi có lý do cụ thể. Giữ tương thích các API market data, indicators và CRUD rules.

Xác định cấu hình môi trường và Docker, vòng đời HTTP client, timeout, kiểm tra
phản hồi Telegram, xử lý lỗi và chính sách retry đúng theo spec. Bảo vệ token
trong URL, HTTP logs, exception và đầu ra lệnh. Không tắt xác thực TLS.
Không thêm endpoint hoặc màn hình cấu hình/gửi thử riêng nếu không cần cho spec.

Thiết kế job nền độc lập Refresh, bám lịch đóng nến của Binance cho 1h/1d/1w,
không dùng lịch tính từ lúc bật rule/khởi động app. Có thể gom rule theo timeframe
và tái sử dụng dữ liệu cùng symbol thay vì tạo job riêng cho mỗi rule.
Tải đủ lịch sử tính chỉ báo, xác nhận có đúng nến vừa đóng và loại nến đang chạy.
Cache cũ chưa có nến mục tiêu không được coi là lần quét thành công; xác định
cách chờ/thử lấy dữ liệu lại có giới hạn và chống xử lý lặp rule/nến.
Không triển khai WebSocket nội nến hoặc polling liên tục.
Tái sử dụng tính chỉ báo, giữ Decimal/UTC/Spot-Futures và chính sách nến theo spec.
Ưu tiên một tiến trình theo dõi; tài liệu chạy phải tránh khởi tạo watcher lặp
trong nhiều API worker. Tái sử dụng Redis để lưu trạng thái rule nếu chính sách
restart đã chốt yêu cầu, không tạo thêm cơ sở dữ liệu. Phân biệt
trạng thái điều kiện, sự kiện cảnh báo và trạng thái gửi. Không đánh dấu đã gửi
khi chỉ vừa phát hiện điều kiện; không hứa exactly-once khi Telegram timeout.
Nêu xử lý reconnect, dữ liệu stale/thiếu/out-of-order, kiểm tra rule vẫn bật
trước khi gửi, retry/rate limit và shutdown theo spec. Không thêm queue/outbox,
distributed lock hoặc hệ thống worker riêng trừ khi chứng minh là bắt buộc
để đáp ứng yêu cầu đã xác nhận. Không tự hứa phục hồi mọi tín hiệu bị bỏ lỡ.
Chỉ sửa FE nếu cần lưu rule/bật tắt vào backend hoặc chọn gt/gte/lt/lte/ngưỡng số;
không thiết kế lại giao diện. Mỗi module mới phải gắn với một yêu cầu cụ thể.

Thiết kế test mock cho cả thành công/lỗi và cơ chế opt-in riêng cho test live,
kể cả khi máy đã có credentials trong .env. Không gửi tin thật ở bước này.
Tạo plan.md, research.md, data-model.md, contracts/ và quickstart.md bằng tiếng
Việt. Kiểm tra hiến chương, ghi rõ giới hạn lịch quét và các sai lệch cần giải
quyết. Chỉ tạo tài liệu thiết kế, chưa triển khai code.
```

Đọc kế hoạch, hợp đồng và hướng dẫn nghiệm thu. Kiểm tra rằng thiết kế khớp
các câu trả lời ở bước 2.

### Bước 4: Chia công việc

```text
$speckit-tasks Tạo tasks.md cho specs/002-telegram-notifications từ spec và plan
đã thống nhất. Chia theo user story, có ID, đường dẫn file, thứ tự phụ thuộc và
tiêu chí kiểm tra. Bao gồm cấu hình, lịch job 1h/1d/1w, dữ liệu nến đã đóng, lịch sử khởi tạo,
tiến trình nền, đồng bộ rule bật/tắt, tính indicator, so sánh gt/gte/lt/lte, trạng thái
chống lặp, gửi Telegram, retry theo spec, bảo vệ token và tài liệu vận hành.
Thêm test mock cho chuỗi 68 -> 70 -> 75 -> 69 -> 71 với ngưỡng 70 (hai sự kiện),
lần quét đầu sau khi bật đã đạt ngưỡng (một sự kiện), rule tắt (không có sự kiện), dữ liệu lỗi
không reset trạng thái; thêm restart/reconnect theo chính sách đã chốt.
Ưu tiên ngăn test thường gửi tin thật trước khi chạy bộ test hiện tại.
Bao gồm test đồng hồ giả: mỗi mốc chỉ quét đúng timeframe, mốc ngày/tuần trùng
khung giờ không gây trùng, bật giữa nến phải chờ; job gọi lặp không gửi thêm.
Test end-to-end bằng nguồn thị trường và Telegram giả lập, không cần Refresh.
Mỗi task phải dẫn tới yêu cầu trong spec. Loại bỏ task không phục vụ trực tiếp
luồng này; không thêm framework, nhiều worker, UI mới hoặc gửi thử riêng chỉ
vì có thể làm. Việc cải tiến ngoài phạm vi ghi vào danh sách tương lai.
Viết bằng tiếng Việt; chưa thực hiện các task.
```

### Bước 5: Rà soát tính nhất quán

```text
$speckit-analyze Kiểm tra spec.md, plan.md và tasks.md trong
specs/002-telegram-notifications với hiến chương và code hiện tại.
Tìm yêu cầu thiếu task, mâu thuẫn phạm vi, định nghĩa thành công chưa rõ,
rủi ro gửi lặp khi timeout, lộ token và test vô tình gửi thật. Kiểm tra đặc biệt
các operator/target/candle_mode cũ, lịch đóng nến, persistence chống lặp,
restart, rule bị sửa/tắt, dữ liệu thiếu và tránh chạy watcher trùng. Phân biệt số sự kiện
được kích hoạt với số lần thử gửi và số tin Telegram chấp nhận.
Đánh dấu task/module không có yêu cầu tương ứng hoặc giải pháp phức tạp hơn
cần thiết. Xác nhận không bỏ sót tích hợp backend rules do quá tập trung gửi thử.
Phân loại mức độ và đề xuất sửa bằng tiếng Việt. Chỉ phân tích, không sửa file
hoặc triển khai code ở bước này.
```

Sau báo cáo, yêu cầu sửa các vấn đề cần thiết rồi chạy lại analyze. Chỉ chuyển
sang bước 6 khi yêu cầu, thiết kế và task đã nhất quán.

### Bước 6: Triển khai sau khi đã xem tài liệu

```text
$speckit-implement Triển khai theo specs/002-telegram-notifications/tasks.md
và các quyết định đã chốt trong spec/plan. Giữ thay đổi đúng phạm vi Telegram.
Tái sử dụng code hiện có, giữ nguyên thay đổi không liên quan của tôi.
Chỉ thực hiện task đã có trong plan; không refactor ngoài phạm vi hoặc thêm
tính năng phụ. Không tự giải quyết điểm nghiệp vụ còn chưa chốt bằng giả định.
Chỉ chạy test mock; không gọi Telegram thật, không tự gửi tin và không in token.
Đảm bảo test live không tự chạy chỉ vì .env có credentials trước khi chạy pytest.
Chạy kiểm thử backend và lint phù hợp; nếu có thay đổi FE theo plan thì chạy
test/build FE và kiểm tra luồng UI. Cập nhật tasks theo kết quả thực tế.
Báo rõ phần hoàn thành, kiểm tra đã chạy và hạn chế. Không tự commit/push.
```

### Bước 7: Đối chiếu kết quả và nghiệm thu

```text
$speckit-converge Đối chiếu code với specs/002-telegram-notifications.
Kiểm tra toàn bộ luồng job sau đóng nến không cần Refresh bằng mock: rule bật, indicator
thỏa gt/gte/lt/lte, gửi lần đầu, giữ đúng không lặp, sai rồi đúng tái kích hoạt.
Giữ ví dụ gte 68->70->75->69->71; kiểm tra equality cho cả bốn toán tử.
Kiểm tra cron/executor tự dispatch với đồng hồ giả, không chỉ gọi scan trực tiếp.
Kiểm tra rule tắt, restart/reconnect, dữ liệu thiếu/stale, cấu hình thiếu/tắt,
phản hồi Telegram lỗi, timeout/rate limit, bảo vệ token và test thường không
gọi dịch vụ thật. Đối chiếu lịch quét đúng timeframe và chỉ dùng nến đã đóng;
không suy ra job chạy đúng từ việc gửi thử thành công. Xác nhận API hiện có không
bị thay đổi ngoài kế hoạch. Ghi phần thiếu vào tasks và phân biệt kết quả mock
với nghiệm thu thật. Không tự gửi tin Telegram. Chỉ kết luận đạt những tiêu chí
có bằng chứng kiểm chứng; ghi riêng phần cần nghiệm thu thực tế. Báo cáo bằng tiếng Việt.
```

Nếu còn task, đọc lại rồi tiếp tục implement/converge. Khi muốn thử tin thật,
cấu hình token và chat ID ở máy local, rồi yêu cầu riêng sau khi xem quickstart.
Không gửi token trong prompt. Tin thử thành công không đồng nghĩa rule engine
đã được nối với Telegram.

## 9. Tài liệu tham khảo

- [Repository Spec Kit](https://github.com/github/spec-kit)
- [Áp dụng cho dự án có sẵn, phiên bản 1.1.3](https://github.com/github/spec-kit/blob/v1.1.3/docs/guides/existing-projects.md)
- [Tích hợp coding agent, phiên bản 1.1.3](https://github.com/github/spec-kit/blob/v1.1.3/docs/reference/integrations.md)
