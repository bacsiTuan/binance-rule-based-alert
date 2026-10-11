# Checklist chất lượng đặc tả: SMA, EMA và RSI Wilder

**Mục đích**: Kiểm tra tính đầy đủ và rõ ràng trước khi lập kế hoạch.
**Ngày tạo**: 2026-10-11
**Tính năng**: [Đặc tả](../spec.md)
**Trách nhiệm review**: Checklist yêu cầu do người review đánh giá; dấu hoàn thành
chỉ biểu thị chất lượng đặc tả, không có nghĩa tính năng đã được triển khai.

## Chất lượng nội dung

- [x] CHK001 Không áp đặt ngôn ngữ, framework, cấu trúc mã hoặc thiết kế API mới.
- [x] CHK002 Tập trung giá trị người dùng và nhu cầu tính chỉ báo chính xác.
- [x] CHK003 Kịch bản giải thích được với bên nghiệp vụ; công thức định nghĩa hành vi.
- [x] CHK004 Hoàn thành mọi phần bắt buộc của mẫu.

## Tính đầy đủ của yêu cầu

- [x] CHK005 Không còn điểm cần làm rõ chưa giải quyết.
- [x] CHK006 Yêu cầu có thể kiểm thử và không mơ hồ.
- [x] CHK007 Tiêu chí thành công đo lường được.
- [x] CHK008 Tiêu chí thành công không phụ thuộc công nghệ triển khai.
- [x] CHK009 Đã xác định kịch bản nghiệm thu.
- [x] CHK010 Đã xác định các trường hợp biên.
- [x] CHK011 Phạm vi có ranh giới rõ ràng.
- [x] CHK012 Đã ghi giả định và phụ thuộc.

## Mức độ sẵn sàng

- [x] CHK013 Mọi yêu cầu chức năng có điều kiện nghiệm thu rõ ràng.
- [x] CHK014 Câu chuyện người dùng bao phủ luồng chính.
- [x] CHK015 Tiêu chí thành công bao phủ kết quả cần đạt của tính năng.
- [x] CHK016 Không đưa thiết kế triển khai vào đặc tả.

## Ghi chú

- Đã review 16/16 tiêu chí. Không còn mục cần sửa hoặc câu hỏi chặn lập kế hoạch.
- FR-003–005 quy định công thức/seed như hành vi sản phẩm, không chọn thư viện.
- FR-007–008 phân biệt thời điểm đánh giá và snapshot được fetch trước khi nến đóng.
- FR-009 đưa ngưỡng sai số cho nghiệm thu; không ép cách biểu diễn nội bộ.
- FR-010–012 nhắc hợp đồng API/cache hiện có để bảo vệ tương thích, không thiết kế
  endpoint mới. FR-014 ghi ràng buộc mock từ hiến chương, không chọn test framework.
- FR-001–005 đối chiếu câu chuyện 1–2; FR-006–008 đối chiếu câu chuyện 2–3;
  FR-009–014 đối chiếu SC-001–006 và các trường hợp biên; FR-015 xác định ngoài phạm vi.
- Chưa chạy test ứng dụng vì lần này chỉ tạo tài liệu đặc tả và con trỏ tính năng.
