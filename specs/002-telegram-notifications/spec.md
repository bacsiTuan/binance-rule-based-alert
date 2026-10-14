# Đặc tả: Cảnh báo Telegram theo lịch đóng nến

**Feature Branch**: `feat/telegram-notifications`
**Created**: 2026-10-13
**Status**: Clarified - hoàn tất 5 câu hỏi, sẵn sàng lập kế hoạch
**Input**: Theo dõi rule đang bật, tự gửi Telegram khi indicator thỏa gt/gte/lt/lte với ngưỡng số;
không gửi lặp khi điều kiện còn đúng, tái kích hoạt sau khi xuống dưới rồi đạt
ngưỡng trở lại. Quét một lần sau mỗi lần đóng nến 1h/1d/1w, chỉ quét rule
đang bật cùng timeframe. Không phụ thuộc Refresh hoặc frontend đang mở.

## User Scenarios & Testing

### User Story 1 - Nhận cảnh báo tự động (Priority: P1)

Người dùng bật một rule đủ điều kiện và nhận Telegram khi chỉ báo tại nến vừa đóng đạt ngưỡng,
kể cả khi không mở giao diện, miễn backend theo dõi đang hoạt động.

**Why this priority**: Đây là kết quả chính của tính năng, không thay thế bằng gửi thử.
**Independent Test**: Với dữ liệu thị trường và nơi nhận giả lập, bật một rule,
không gọi Refresh; giả lập đóng nến và kiểm tra chỉ rule cùng timeframe được quét.

**Acceptance Scenarios**:

1. **Given** rule đủ điều kiện đang bật, **When** giá trị tại lần quét nến đóng hợp lệ đầu tiên là 75 với ngưỡng 70, **Then** tạo một thông báo, không đòi hỏi đã quan sát giá trị dưới 70 trước đó.
2. **Given** lần đầu giá trị là 68, **When** nến tiếp theo đóng với giá trị hợp lệ đạt 70, **Then** tạo một thông báo vì bằng ngưỡng cũng thỏa mãn.
3. **Given** cùng indicator nhưng khác symbol, period hoặc timeframe, **When** đánh giá, **Then** dùng đúng dữ liệu của từng rule và không trộn kết quả.
4. **Given** Telegram xác nhận chấp nhận tin, **When** người dùng xem tin, **Then** có rule, market, symbol, timeframe, indicator/period, giá trị thực tế, ngưỡng, thời gian nến và nhãn nến đã đóng.
5. **Given** rule 1h, 1d, 1w đang bật, **When** chỉ nến 1h đóng, **Then** chỉ quét rule 1h; tại mốc nhiều khung cùng đóng, mỗi nhóm được quét một lần.
6. **Given** rule vừa bật giữa nến, **When** chưa đến lần đóng nến tiếp theo, **Then** không đánh giá hoặc gửi ngay; chờ lịch của timeframe đó.

### User Story 2 - Không bị gửi lặp khi điều kiện còn đúng (Priority: P1)

Người dùng chỉ nhận một thông báo cho mỗi giai đoạn điều kiện liên tục đúng.

**Why this priority**: Mỗi lần quét không được mặc định tạo tin mới khi điều kiện vẫn đúng.
**Independent Test**: Đưa chuỗi giá trị tại các lần đóng nến liên tiếp vào rule, so sánh số sự kiện
và số tin được chấp nhận khi nơi nhận giả lập luôn thành công.

**Acceptance Scenarios**:

1. **Given** ngưỡng 70, **When** nhận 68 -> 70 -> 75 -> 69 -> 71, **Then** tạo hai sự kiện, tại 70 và 71; nếu gửi thành công thì có hai tin.
2. **Given** đã kích hoạt tại 70, **When** tiếp tục nhận 70 -> 75 -> 80, **Then** không tạo sự kiện mới hoặc nhắc lại định kỳ.
3. **Given** điều kiện đang đúng, **When** thiếu dữ liệu/lỗi rồi nhận 75, **Then** không coi lỗi là giá trị dưới ngưỡng và không tái kích hoạt.
4. **Given** đã thông báo trong nến trước, **When** sang nến mới mà mọi giá trị hợp lệ vẫn >= ngưỡng, **Then** không gửi lại chỉ vì đổi nến.

### User Story 3 - Kiểm soát phạm vi và nhận biết lỗi (Priority: P2)

Người dùng không nhận cảnh báo từ rule đã tắt hoặc dữ liệu không đủ tin cậy;
người vận hành nhận biết lỗi gửi mà không lộ thông tin bí mật.

**Why this priority**: Tránh cảnh báo sai và thành công giả trong vận hành thực tế.
**Independent Test**: Dùng rule tắt, rule không hỗ trợ, dữ liệu lỗi và Telegram
giả lập lỗi; kiểm tra không tạo sự kiện sai, không rò token và không ảnh hưởng API cũ.

**Acceptance Scenarios**:

1. **Given** rule tắt hoặc bị xóa trước lúc đánh giá, **When** giá trị vượt ngưỡng, **Then** không tạo sự kiện mới.
2. **Given** Telegram chưa cấu hình, **When** sử dụng market data, indicators và CRUD rules, **Then** các chức năng này vẫn hoạt động; không báo đã gửi Telegram.
3. **Given** timeout khi gửi, **When** ghi nhận kết quả, **Then** báo chưa xác định kết quả; không coi đó là bằng chứng tin chưa đến nơi.
4. **Given** thiếu nến hoặc indicator không hỗ trợ, **When** đánh giá, **Then** bỏ qua lần đánh giá và ghi lý do an toàn; không dùng 0 hoặc giá trị giả để so sánh.
5. **Given** các rule phù hợp chỉ khác trigger_type, **When** nhận cùng chuỗi giá trị nến đóng, **Then** chúng có cùng hành vi chống lặp Telegram; trigger_type đã lưu không thay đổi.
6. **Given** Telegram từ chối tin, **When** xử lý lỗi, **Then** không báo thành công, không in token và không làm ngừng theo dõi các rule khác.
7. **Given** một sự kiện đã thử gửi nhưng lỗi/timeout/rate limit, **When** job chạy lại hoặc nến sau điều kiện vẫn đúng, **Then** không thử gửi lại sự kiện đó và không reset; chỉ sự kiện mới sau chu kỳ điều kiện sai rồi đúng mới có lần gửi mới.

### Edge Cases

- Giá trị bằng ngưỡng; ngưỡng thập phân; không làm tròn giá trị trước so sánh để tạo kết quả sai.
- Cập nhật trùng, sai thứ tự hoặc thuộc symbol/timeframe/market khác; không làm lùi trạng thái điều kiện.
- Nến đang chạy vượt/ngắt ngưỡng nhiều lần: bỏ qua, chỉ dùng kết quả nến đã đóng. Một lần xuống dưới trong nến nhưng đóng vẫn >= không reset chống lặp.
- Đã tới giờ chạy job nhưng dữ liệu chưa có nến vừa đóng: không dùng nến cũ thay thế hoặc đánh dấu đã đánh giá; ghi lỗi dữ liệu chưa sẵn sàng. Chính sách thử lấy lại cần nêu trong plan.
- Job bị gọi lặp cho cùng rule/nến: không đánh giá hiệu lực hoặc tạo thông báo mới lần hai.
- Dữ liệu stale, mất kết nối, thiếu lịch sử, NaN/vô cực; không kích hoạt hoặc reset điều kiện từ dữ liệu không hợp lệ.
- Sửa cấu hình, tắt/bật lại, restart, reconnect: áp dụng chính sách Q3, không tự suy diễn.
- Rule có operator ngoài gt/gte/lt/lte hoặc target là indicator bị bỏ qua; không chọn Telegram trong notifications không loại rule phù hợp khỏi luồng gửi. Telegram dùng quy tắc chống lặp FR-005 độc lập với trigger_type; giữ nguyên trường trigger_type cho các luồng khác.
- Rule hết hạn: không tạo sự kiện sau thời điểm hết hạn hợp lệ; thời gian hết hạn không hợp lệ phải được báo rõ, không tự coi là vô hạn.
- Tắt/xóa rule trước khi bắt đầu gửi: không bắt đầu gửi mới; tin đã gửi ra ngoài không thể cam kết thu hồi.
- Token/chat sai, bot bị chặn, rate limit, lỗi dịch vụ và timeout; phân biệt sự kiện kích hoạt với kết quả vận chuyển tin.

## Requirements

### Functional Requirements

- **FR-001**: Quét theo lịch đóng nến 1h/1d/1w, mỗi mốc một lần cho các rule cùng timeframe. Tự theo dõi các rule đủ điều kiện đang bật ở backend, không cần Refresh, không cần frontend đang mở. Rule chỉ tồn tại ở chế độ mock/trình duyệt không được coi là đã theo dõi ở backend.
- **FR-002**: Chỉ dùng indicator hiện có hỗ trợ: SMA, EMA, RSI; timeframe 1h, 1d, 1w; lấy đúng period của rule. Không thêm indicator hoặc toàn bộ toán tử mới trong feature này.
- **FR-003**: Đánh giá indicator_value với ngưỡng số hữu hạn bằng gt (>), gte (>=), lt (<), lte (<=). Bằng ngưỡng chỉ thỏa gte/lte. So sánh Decimal đầy đủ, không làm tròn trước so sánh. Không đổi thành cross_above/cross_below hoặc sửa operator đã lưu.
- **FR-004**: Lần đánh giá hợp lệ đầu tiên của một lần theo dõi mới, nếu điều kiện đúng, tạo một sự kiện trong lần quét đó; nếu sai, chờ nến tiếp theo. Bật rule giữa nến không kích hoạt đánh giá ngay.
- **FR-005**: Sau khi kích hoạt, không tạo sự kiện mới khi điều kiện vẫn đúng. Chỉ quan sát hợp lệ làm điều kiện sai mới rearm, rồi kích hoạt khi điều kiện đúng trở lại. Với gt/gte/lt/lte, điều kiện rearm lần lượt là <= / < / >= / > ngưỡng. Nến mới hoặc lỗi dữ liệu không tự reset.
- **FR-006**: Rule tắt, bị xóa, hết hạn hoặc không đủ điều kiện không được tạo sự kiện mới. Kiểm tra lại khả năng gửi trước khi bắt đầu gửi tin.
- **FR-007**: Nội dung tin có các trường của US1; market đúng, nhãn CLOSED và Timezone: UTC. Value hiển thị đúng hai chữ số thập phân, ví dụ `Value: 51.66 >= 40`, ký hiệu theo operator và bỏ chữ Threshold. Ngưỡng giữ giá trị đã lưu; tính toán/lưu state giữ Decimal đầy đủ, chỉ làm tròn hiển thị (half-even). Open/Close dùng yyyy-mm-dd HH:MM:SS UTC, bỏ phần milliseconds khi hiển thị, timestamp nội bộ vẫn UTC milliseconds. Chỉ gửi giá trị từ nến đã đóng.
- **FR-008**: Thiếu/lỗi/stale dữ liệu không sinh cảnh báo mới hoặc làm mất trạng thái chống lặp. Chỉ tiếp tục đánh giá khi có dữ liệu hợp lệ; không tự chuyển market hoặc nguồn dữ liệu để che lỗi.
- **FR-009**: Thiếu cấu hình Telegram không làm hỏng chức năng cũ. Thông tin bot/nơi nhận nằm ở cấu hình backend, không đưa token vào frontend, log hoặc lỗi công khai.
- **FR-010**: Chỉ báo gửi thành công khi có xác nhận hợp lệ từ Telegram; phân biệt thất bại và kết quả không xác định. Mỗi sự kiện được thử gửi tối đa một lần; không tự retry với lỗi mạng, timeout, rate limit hoặc lỗi dịch vụ, kể cả sau restart. Ghi lỗi an toàn; thất bại không reset trạng thái điều kiện để thử lại dưới dạng sự kiện mới. Không hứa exactly-once hoặc bảo đảm mọi tin được giao; có thể bỏ lỡ tin lỗi.
- **FR-011**: Giữ hợp đồng API hiện có, dữ liệu thời gian/giá và ngữ nghĩa cache/stale. Không sửa toàn bộ UI hoặc lưu trữ rules ngoài phần thật sự cần cho tính năng.
- **FR-012**: Test tự động dùng dữ liệu thị trường và nơi gửi giả lập, bao gồm luồng không Refresh, chuỗi ngưỡng, bật/tắt, lỗi và rò token. Có credentials không được tự kích hoạt test gửi thật.
- **FR-013**: Chỉ đánh giá sau khi đóng nến theo lịch Q1, không tính nến đang chạy. Lịch bám mốc nến của nguồn dữ liệu, không tính 1 giờ/ngày/tuần kể từ lúc bật rule hoặc khởi động ứng dụng. Cùng một rule và nến chỉ được xử lý hiệu lực một lần.
- **FR-014**: Phạm vi đánh giá đã chốt: chỉ rule đang bật, SMA/EMA/RSI, operator thuộc gt/gte/lt/lte, target là số hữu hạn và candle_mode=closed. Rule ngoài phạm vi được giữ nguyên, bỏ qua và ghi rõ lý do; không tự đổi operator, target hoặc candle_mode. Khi Telegram được cấu hình, mọi rule phù hợp đang bật tham gia luồng gửi, không yêu cầu notifications chứa telegram và không thêm thao tác chọn kênh trên từng rule. Giữ nguyên dữ liệu notifications hiện có. Telegram dùng quy tắc chống lặp FR-005 độc lập với trigger_type; giữ nguyên trường trigger_type cho các luồng khác.
- **FR-015**: Giữ trạng thái điều kiện và nến đã xử lý qua restart/reconnect khi cấu hình rule không đổi; tiếp tục tại lần đóng nến tiếp theo, không gửi bù nến bị bỏ lỡ. Chủ động tắt/bật rule hoặc sửa điều kiện (symbol, indicator, period, timeframe, operator, target, candle_mode) bắt đầu lần theo dõi mới tại lần đóng nến tiếp theo. Sửa nội dung tin, notifications hoặc trigger_type không phải sửa điều kiện và không reset chống lặp Telegram. Tách trạng thái điều kiện khỏi trạng thái đã gửi; retry theo Q3.

### Key Entities

- **Rule theo dõi**: định danh, bật/tắt, symbol/market, timeframe, indicator/period, ngưỡng, chính sách nến, trigger, kênh và thời hạn.
- **Giá trị quan sát**: giá trị chỉ báo, thời gian dữ liệu, trạng thái nến và tính hợp lệ.
- **Trạng thái điều kiện**: chưa có quan sát hợp lệ, điều kiện sai hoặc đã kích hoạt; gắn với rule và cấu hình đang có hiệu lực. Tên lưu trữ legacy `below` có nghĩa điều kiện sai, không nhất thiết nhỏ hơn ngưỡng.
- **Sự kiện cảnh báo**: ghi nhận một lần điều kiện kích hoạt, không đồng nghĩa tin đã được gửi.
- **Kết quả gửi**: được chấp nhận, thất bại hoặc chưa xác định; liên hệ với sự kiện tương ứng.

## Success Criteria

- **SC-001**: Trong nghiệm thu mô phỏng không mở frontend/không Refresh, rule đủ điều kiện sinh đúng sự kiện theo gt/gte/lt/lte; nơi gửi thành công nhận một tin cho mỗi sự kiện. Bằng ngưỡng chỉ thỏa gte/lte.
- **SC-002**: Chuỗi 68 -> 70 -> 75 -> 69 -> 71 với ngưỡng 70 tạo đúng hai sự kiện; chuỗi 75 -> 75 -> 80 từ lần bật đầu tạo đúng một sự kiện.
- **SC-003**: 100% tình huống rule tắt/không đủ điều kiện và dữ liệu lỗi/thiếu/stale trong bộ nghiệm thu không tạo cảnh báo sai hoặc reset chống lặp sai.
- **SC-004**: Trong kiểm thử lịch với đồng hồ giả lập, mỗi mốc đóng nến 1h/1d/1w tạo đúng một lượt quét cho nhóm tương ứng; không quét giữa nến hoặc do Refresh. Gọi lặp cùng mốc không tạo thêm sự kiện cho nến đã xử lý. Thời gian gửi thực tế được ghi nhận riêng, chưa cam kết SLA 5 giây.
- **SC-005**: Không có token giả đánh dấu riêng trong đầu ra/log kiểm thử thành công và lỗi; test thường tạo 0 yêu cầu gửi Telegram thật.
- **SC-006**: Các kiểm tra hồi quy API hiện có vẫn đạt; không tạo tin chỉ vì gọi CRUD, health hoặc indicators nếu không có lần đánh giá hợp lệ kích hoạt.
- **SC-007**: Trong mô phỏng lỗi mạng, timeout, rate limit và lỗi Telegram, mỗi sự kiện có tối đa một lần thử gửi; khởi động lại hoặc quét lại không tạo lần thử thứ hai. Sau một nến hợp lệ làm điều kiện sai rồi nến làm điều kiện đúng trở lại, sự kiện mới được phép thử gửi một lần.

## Assumptions

- Phạm vi sản phẩm hiện tại: quét sau đóng nến để đánh giá gt/gte/lt/lte, gửi lần đầu điều kiện đúng và tái kích hoạt sau sai rồi đúng; không nhắc định kỳ. Các ví dụ chuỗi ngưỡng 70 ban đầu là trường hợp gte.
- Mặc định đề xuất để giữ phạm vi nhỏ: một người vận hành, một bot/chat cho mỗi môi trường, không broadcast hoặc cấu hình từng người dùng.
- Không thêm dashboard lịch sử, backtest, AND/OR, framework mọi toán tử, queue phân tán hoặc UI/API/CLI gửi thử riêng chỉ để demo.
- Backend và kết nối dịch vụ cần hoạt động; không cam kết bắt mọi tín hiệu trong thời gian mất mạng hoặc ứng dụng dừng.
- Tin thử nếu dùng để nghiệm thu phải được đánh dấu riêng, không thay thế chứng minh luồng tự động.
- Thiết kế nguồn dữ liệu, lưu trạng thái và tổ chức tiến trình thuộc bước plan, chưa quyết định trong spec.

## Clarifications

### Amendment 2026-10-14 - Phạm vi hiện hành

Theo yêu cầu trực tiếp của người dùng: bổ sung ba phép so sánh còn lại >, <, <=
bên cạnh >=; Value chỉ hai chữ số sau dấu chấm, bỏ Threshold và làm gọn Open/Close.
FR-003/005/007/014 phía trên là yêu cầu hiện hành, thay thế giới hạn gte-only
trong lịch sử Q2 bên dưới. Không thay lịch, no-retry, no-backfill hoặc public API.
Các đoạn "dưới ngưỡng rồi đạt lại" và ví dụ 70 trong các scenario cũ là minh họa gte;
toán tử khác dùng bảng rearm của FR-005. Không hỗ trợ cross_above/cross_below.

Nghiệm thu bổ sung: mỗi toán tử có equality, lần đầu đã đúng, giữ đúng không lặp,
sai rồi đúng có sự kiện mới; ví dụ 51.657... hiển thị 51.66 nhưng vẫn so sánh
và lưu giá trị đầy đủ. Mốc Close 10:59:59.999 UTC hiển thị 10:59:59, không đổi nến.
Ví dụ tin Rule #6 do người dùng cung cấp chỉ chứng minh một tin được quan sát;
không thay bằng chứng kiểm thử lịch hoặc nghiệm thu đầy đủ bản format mới.

Các quyết định 2026-10-13 dưới đây được giữ để truy vết, không phải phạm vi mới.

### Session 2026-10-13

- Q: Nếu gửi Telegram bị lỗi, hệ thống có tự thử lại không? A: Chọn A; mỗi sự kiện chỉ thử một lần, ghi rõ lỗi hoặc kết quả không xác định, không tự retry. Có thể bỏ lỡ tin đó nhưng vẫn tiếp tục theo dõi lần kích hoạt mới.

- Q: Khi backend restart hoặc mất mạng rồi kết nối lại, tiếp tục theo dõi thế nào? A: Chọn A; giữ trạng thái, tiếp tục tại lần đóng nến tiếp theo và không gửi bù. Người dùng tắt/bật rule hoặc sửa điều kiện thì bắt đầu theo dõi mới từ lần đóng nến tiếp theo.

- Q: Telegram dùng chống lặp chung hay tần suất gửi cũ của từng rule? A: Chọn A; dùng quy tắc đã chốt, chỉ tái kích hoạt sau nến đóng dưới ngưỡng rồi đạt lại; trigger_type cũ không chi phối Telegram và được giữ nguyên.

- Q: Với rule cũ không đúng dạng indicator >= một con số và nến đã đóng, xử lý thế nào? A: Chọn A; chỉ quét rule đang bật, SMA/EMA/RSI, gte, ngưỡng số và nến đã đóng. Rule khác giữ nguyên, bỏ qua và ghi lý do. Lựa chọn này chưa xác nhận chính sách notifications hoặc trigger_type.
- Q: Mọi rule phù hợp đang bật tự gửi Telegram hay cần chọn riêng kênh? A: Chọn A; khi Telegram được cấu hình, mọi rule phù hợp đang bật đều gửi nếu thỏa điều kiện và chống lặp, không yêu cầu chọn thêm kênh Telegram.

### Q1 - Đã chốt: schedule theo đóng nến

Người dùng yêu cầu ngày 2026-10-13: mỗi lần đóng nến, quét một lần theo
khung 1h, 1d hoặc 1w của rule đang bật. Không dùng giá trị nến đang chạy.
Bật rule giữa nến chờ lần đóng tiếp theo. Không còn mục tiêu realtime nội nến
hoặc đề xuất SLA 5 giây trước đây. Plan xác định độ trễ chờ dữ liệu sẵn sàng,
không tự đổi thành quét lặp liên tục. Rule có candle_mode=include_current phải
được xử lý tương thích theo Q2, không âm thầm sửa dữ liệu rule cũ.

### Q2 - Rule đủ điều kiện và trigger cũ (lịch sử trước amendment)

Đã chốt lựa chọn A: chỉ quét rule đang bật, SMA/EMA/RSI, gte, ngưỡng số và
nến đã đóng. Rule khác giữ nguyên, bỏ qua và ghi lý do.

Đã chốt mọi rule phù hợp đang bật tham gia luồng gửi khi Telegram được cấu hình,
không yêu cầu chọn Telegram trong notifications; không sửa dữ liệu kênh cũ.

Đã chốt: Telegram dùng FR-004/FR-005 cho mọi rule phù hợp, không dùng
trigger_type để quyết định tần suất gửi. Không sửa trigger_type đã lưu và không
thay đổi cách các luồng khác sử dụng trường này. Tài liệu vận hành phải nêu rõ
sự khác biệt để người dùng không hiểu lựa chọn tần suất cũ là tần suất Telegram.

### Q3 - Khôi phục và gửi lỗi

Đã chốt khôi phục: giữ trạng thái qua restart/reconnect nếu cấu hình không đổi,
không gửi bù nến bị bỏ lỡ; tiếp tục từ lần đóng nến tiếp theo. Tắt/bật rule hoặc
sửa điều kiện bắt đầu lần theo dõi mới, cũng chờ lần đóng nến tiếp theo.
Ví dụ đã gửi tại 75 trước restart, sau restart nến tiếp theo vẫn 75 thì không
gửi lại. Nếu tắt/bật rule, nến tiếp theo là 75 thì được kích hoạt một lần mới.

Đã chốt gửi lỗi: mỗi sự kiện chỉ thử gửi một lần; lỗi/timeout/rate limit được
ghi nhận, không tự retry. Timeout có thể xảy ra sau khi Telegram đã nhận tin,
nên báo kết quả không xác định thay vì khẳng định chưa gửi. Không reset trạng
thái điều kiện khi gửi lỗi. Người dùng chấp nhận có thể bỏ lỡ tin của sự kiện
đó; vẫn đánh giá nến tiếp theo và gửi cho sự kiện kích hoạt mới theo FR-005.

Kết thúc phiên clarify: 5 câu hỏi đã trả lời. Không còn quyết định nghiệp vụ
chặn bước plan. Một bot/chat chung vẫn là giả định phạm vi đã ghi, không phải
cấu hình credentials đã được cung cấp. Cách tổ chức job, lưu trạng thái chống
gửi lại sau crash và chờ nến sẵn sàng thuộc bước plan; không tự thêm retry gửi.
Checklist được đánh giá lại theo spec này; ghi chú câu hỏi còn mở trong checklist
là văn bản của lần rà soát ban đầu, trạng thái checkbox phản ánh lần rà soát mới.

## Hiện trạng và ràng buộc đối chiếu tại thời điểm lập spec

Code hiện có indicators SMA/EMA/RSI, CRUD rules, TelegramClient đơn giản, nhưng
chưa có luồng job đánh giá/gửi theo lịch đóng nến. Rule hỗ trợ nhiều operator, target indicator,
candle_mode, trigger_type và notifications; không thể coi mọi rule bật là gte.
Một số giá trị rule đang dùng kiểu float; bước plan phải kiểm tra ảnh hưởng tới
so sánh ngưỡng chính xác, không âm thầm đổi hợp đồng cũ.

README/hiến chương có mô tả hiện trạng chưa theo kịp indicators/CRUD rules đã có.
Ghi nhận sai lệch để review; không tự thay nguyên tắc hiến chương trong feature.
Chỉ tạo đặc tả/checklist; chưa có kế hoạch kỹ thuật, tasks hay code triển khai.
