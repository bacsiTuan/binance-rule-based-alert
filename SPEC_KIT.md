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

## 8. Tài liệu tham khảo

- [Repository Spec Kit](https://github.com/github/spec-kit)
- [Áp dụng cho dự án có sẵn, phiên bản 1.1.3](https://github.com/github/spec-kit/blob/v1.1.3/docs/guides/existing-projects.md)
- [Tích hợp coding agent, phiên bản 1.1.3](https://github.com/github/spec-kit/blob/v1.1.3/docs/reference/integrations.md)
