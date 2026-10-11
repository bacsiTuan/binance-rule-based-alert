# Đặc tả tính năng: Tính SMA, EMA và RSI Wilder từ nến Binance

**Nhánh tính năng**: Không tạo nhánh mới; nhánh hiện tại `main`.

**Ngày tạo**: 2026-10-11

**Trạng thái**: Bản nháp đã kiểm tra chất lượng, sẵn sàng lập kế hoạch.

**Đầu vào**: Bổ sung tính SMA, EMA và RSI theo phương pháp Wilder từ nến Binance;
làm rõ số nến tối thiểu, thiếu dữ liệu và nến chưa đóng; giữ nguyên API market data
và cache; chưa triển khai rule engine hoặc gửi cảnh báo. Tài liệu bằng tiếng Việt.

## Clarifications

### Session 2026-10-11

- Q: Trong lần phát triển này, bạn muốn người dùng lấy kết quả SMA, EMA và RSI qua cách nào? → A: API chỉ báo riêng, tái sử dụng luồng market data hiện có; chưa thêm CLI hoặc UI.
- Q: Một lần gọi API có cần tính nhiều chu kỳ của cùng một chỉ báo, chẳng hạn SMA(20) và SMA(50), không? → A: Cho phép nhiều chu kỳ; nhận diện bằng cặp tên chỉ báo và chu kỳ; từ chối yêu cầu chứa cặp trùng lặp.

## Kịch bản người dùng và kiểm thử *(bắt buộc)*

### Câu chuyện 1 - Nhận giá trị chỉ báo có thể đối chiếu (Ưu tiên: P1)

Người sử dụng dữ liệu gọi API chỉ báo riêng với symbol, khung nến, chỉ báo
và chu kỳ trên thị trường đang cấu hình để nhận chuỗi kết quả gắn với từng nến,
phục vụ phân tích sau này.

**Lý do ưu tiên**: Giá trị đúng và xác định được cách tính là mục tiêu chính của tính năng.

**Kiểm thử độc lập**: Dùng các bộ giá đóng cửa cố định, so sánh kết quả với phép tính
đối chiếu trong đặc tả; không cần rule engine, giao diện mới hay dữ liệu mạng thật.

**Kịch bản nghiệm thu**:

1. **Cho** bốn nến đóng có giá `1, 2, 3, 6`, **khi** tính SMA và EMA chu kỳ 3,
   **thì** hai điểm đầu chưa đủ dữ liệu; SMA cho hai điểm sau là `2`, `11/3`,
   EMA là `2`, `4`, theo quy tắc sai số FR-009.
2. **Cho** năm nến đóng có giá `1, 2, 3, 2, 4`, **khi** tính RSI chu kỳ 3,
   **thì** ba điểm đầu chưa đủ dữ liệu; hai điểm sau là `200/3` và `250/3`.
3. **Cho** cùng dữ liệu, chu kỳ, chính sách nến và thời điểm đánh giá,
   **khi** tính lại, **thì** nhận cùng kết quả và metadata nguồn không bị thay đổi.
4. **Cho** dữ liệu của Spot và Futures có cùng symbol, **khi** tính riêng,
   **thì** mỗi kết quả giữ đúng thị trường và chỉ sử dụng giá của nguồn tương ứng.
5. **Cho** yêu cầu hợp lệ gửi tới API chỉ báo riêng, **khi** xử lý yêu cầu,
   **thì** nhận chuỗi kết quả và metadata từ luồng market data hiện có,
   không cần CLI hoặc UI mới; các API market data cũ giữ nguyên hợp đồng.
6. **Cho** yêu cầu gồm SMA(20) và SMA(50), **khi** tính,
   **thì** nhận hai kết quả riêng, mỗi kết quả ghi rõ tên chỉ báo và chu kỳ;
   trạng thái đủ hoặc thiếu dữ liệu được xác định riêng cho từng cặp.

---

### Câu chuyện 2 - Nhận biết thiếu nến và dữ liệu không hợp lệ (Ưu tiên: P1)

Người sử dụng biết rõ chỉ báo chưa có giá trị vì thiếu lịch sử, thay vì hiểu nhầm
giá trị 0 là kết quả tính hoặc gặp lỗi không giải thích được.

**Lý do ưu tiên**: Trạng thái thiếu dữ liệu ảnh hưởng trực tiếp cách diễn giải chỉ báo.

**Kiểm thử độc lập**: Cấp các chuỗi có 0, N-1, N và N+1 nến đủ điều kiện,
đối chiếu trạng thái và số nến yêu cầu của từng chỉ báo.

**Kịch bản nghiệm thu**:

1. **Cho** N=14 và 13 nến đủ điều kiện, **khi** tính, **thì** cả ba chỉ báo
   có giá trị mới nhất `null`, trạng thái `insufficient_data`; SMA/EMA báo cần 14,
   RSI báo cần 15, số nến hiện có là 13.
2. **Cho** 14 nến đủ điều kiện, **khi** tính chu kỳ 14, **thì** SMA/EMA có giá trị,
   RSI vẫn thiếu dữ liệu; khi đủ 15 nến, RSI có giá trị đầu tiên.
3. **Cho** chuỗi rỗng hoặc mọi nến đều bị loại vì chưa đóng, **khi** tính,
   **thì** chuỗi điểm rỗng, giá trị mới nhất `null`, số nến đủ điều kiện là 0.
4. **Cho** chu kỳ 0, số âm, số không nguyên hoặc tên chỉ báo không hỗ trợ,
   **khi** yêu cầu tính, **thì** bị từ chối với lỗi đầu vào rõ ràng, không bị
   đánh đồng với thiếu dữ liệu.
5. **Cho** giá không hợp lệ, thời gian trùng hoặc đảo thứ tự,
   **khi** tính, **thì** báo dữ liệu không hợp lệ, không tự sửa, bỏ nến hoặc trả số giả.
6. **Cho** yêu cầu chứa hai mục SMA(20), **khi** kiểm tra đầu vào,
   **thì** từ chối toàn bộ yêu cầu với lỗi cặp chỉ báo/chu kỳ trùng lặp,
   không tự gộp và không trả kết quả từng phần.

---

### Câu chuyện 3 - Kiểm soát nến mở và nhận biết nguồn dữ liệu cũ (Ưu tiên: P2)

Người sử dụng mặc định nhận chỉ báo từ nến đã đóng; nếu chủ động đưa nến đang mở
vào tính thì nhận biết kết quả tạm thời. Dữ liệu cũ phải tiếp tục được nhận diện.

**Lý do ưu tiên**: Tránh coi kết quả có thể thay đổi hoặc dựa trên cache cũ là kết quả mới.

**Kiểm thử độc lập**: Cố định thời điểm đánh giá và fetch, cấp một nến đang mở,
một snapshot cũ và các metadata nguồn khác nhau, rồi so sánh hai chính sách.

**Kịch bản nghiệm thu**:

1. **Cho** N nến có nến cuối chưa đóng, **khi** dùng mặc định,
   **thì** chỉ N-1 nến được dùng; SMA/EMA chu kỳ N báo thiếu dữ liệu.
2. **Cho** cùng chuỗi, **khi** chủ động chọn tính cả nến mở,
   **thì** nến cuối được dùng, điểm phụ thuộc nến đó được đánh dấu tạm thời.
3. **Cho** `close_time` bằng thời điểm đánh giá, **khi** dùng mặc định,
   **thì** nến bị loại; điều kiện nến đóng là nhỏ hơn nghiêm ngặt.
4. **Cho** snapshot được fetch khi nến cuối còn mở, nhưng thời gian hiện tại đã
   qua giờ đóng, **khi** dùng mặc định, **thì** vẫn loại nến đó vì chưa có snapshot
   chứng minh giá đóng cuối cùng; không tự fetch thêm để bù dữ liệu.
5. **Cho** nguồn `stale`, **khi** tính được chỉ báo, **thì** giữ nguyên `source`,
   `stale`, `warning`, `fetched_at`; trạng thái tính đủ dữ liệu không xóa cờ dữ liệu cũ.
6. **Cho** một yêu cầu market data hiện có, **khi** tính năng được bổ sung,
   **thì** response, nến cuối, key cache, TTL, retry và fallback vẫn như trước.

### Trường hợp biên

- Chu kỳ 1: SMA/EMA bằng giá từng nến; RSI cần hai nến để có một biến động.
- Giá chỉ tăng: RSI 100; chỉ giảm: RSI 0; chuỗi hoàn toàn không đổi: RSI 50.
  Giá không đổi sau một chuỗi biến động vẫn dùng trạng thái làm mượt trước đó.
- Một yêu cầu nhiều chỉ báo có thể vừa có kết quả hợp lệ vừa có chỉ báo thiếu dữ liệu.
- Nến đóng nhưng nguồn stale và nến mở nhưng nguồn mới là hai tình trạng độc lập.
- Dữ liệu hợp lệ nhưng thiếu một khoảng nến: dùng các nến thực tế theo thứ tự,
  không chèn giá hay suy diễn nến; chu kỳ là số quan sát, không phải thời gian đã trôi qua.
- Không trộn symbol, interval hoặc market trong cùng chuỗi. Dữ liệu sai nhận diện
  hoặc sai thời gian bị từ chối, không âm thầm chuẩn hóa thành chuỗi khác.
- Không có dữ liệu vì lỗi nguồn/cache là lỗi nguồn hiện có, không phải chuỗi rỗng
  thành công với trạng thái thiếu dữ liệu.

## Yêu cầu *(bắt buộc)*

### Yêu cầu chức năng

- **FR-001**: PHẢI hỗ trợ yêu cầu tính một hoặc nhiều chỉ báo SMA, EMA, RSI trên
  giá `close` của một chuỗi nến Binance cùng market, symbol và interval. Mỗi chỉ báo
  có chu kỳ N nguyên từ 1 đến 999; mặc định N=14 nếu không chỉ định. Không suy ra
  tên chỉ báo từ cấu hình rules và không cho phép yêu cầu danh sách chỉ báo rỗng.
  PHẢI cho phép nhiều chu kỳ của cùng loại trong một yêu cầu, nhận diện duy nhất
  bằng cặp tên chỉ báo và chu kỳ sau khi áp dụng chu kỳ mặc định. Mỗi kết quả PHẢI
  ghi rõ cặp này. Nếu có cặp trùng lặp, PHẢI từ chối toàn bộ yêu cầu bằng lỗi đầu vào,
  không tự gộp hoặc trả kết quả từng phần.
- **FR-002**: PHẢI tính trên chuỗi theo thời gian tăng dần, không trùng timestamp,
  với giá hữu hạn, không âm và `open_time <= close_time`. Không được âm thầm bỏ
  dữ liệu hỏng, nội suy nến, sắp lại hoặc trộn nguồn. Chuỗi rỗng hợp lệ được xử lý
  như thiếu dữ liệu. Khoảng trống thời gian được xử lý theo quy tắc trường hợp biên.
- **FR-003**: SMA(N) tại mỗi điểm đủ dữ liệu PHẢI bằng tổng N giá gần nhất chia N.
  Giá trị đầu tiên xuất hiện ở nến thứ N; N-1 điểm trước đó có giá trị `null`.
- **FR-004**: EMA(N) PHẢI khởi tạo bằng SMA của N giá đầu tiên đủ điều kiện.
  Sau đó `EMA_mới = alpha * close_mới + (1-alpha) * EMA_trước`,
  với `alpha = 2/(N+1)`. Cần ít nhất N nến; không seed bằng nến đầu đơn lẻ
  khi N lớn hơn 1 và không dùng hệ số Wilder `1/N` cho EMA.
- **FR-005**: RSI(N) PHẢI dùng làm mượt Wilder. Từ mỗi cặp giá liên tiếp,
  `gain = max(close_mới - close_trước, 0)` và
  `loss = max(close_trước - close_mới, 0)`. Seed bằng trung bình cộng N gain
  và N loss đầu tiên; cần N+1 nến. Các bước sau dùng
  `avg_mới = (avg_trước * (N-1) + giá_trị_mới) / N` riêng cho gain và loss.
  Khi cả hai trung bình dương, `RSI = 100 - 100/(1 + avg_gain/avg_loss)`.
  Nếu chỉ avg_loss bằng 0, RSI=100; nếu chỉ avg_gain bằng 0, RSI=0;
  nếu cả hai bằng 0, quy ước RSI=50. Không trả NaN hoặc vô cực.
- **FR-006**: PHẢI tính số nến tối thiểu sau khi áp dụng chính sách nến.
  Với mỗi chỉ báo, trả chuỗi điểm tương ứng nến được chọn; mỗi điểm chứa thời gian,
  giá trị hoặc `null`, và trạng thái `ok` hoặc `insufficient_data`.
  Đồng thời trả giá trị/trạng thái mới nhất, số nến cần và số nến đủ điều kiện.
  Thiếu dữ liệu không phải lỗi yêu cầu và không thay bằng 0. Chuỗi rỗng không có
  thời gian điểm mới nhất; giá trị và thời gian mới nhất đều `null`.
- **FR-007**: Mặc định chỉ dùng nến có `close_time < thời_điểm_đánh_giá_UTC_ms`.
  Thời điểm đánh giá PHẢI được cố định cho toàn bộ lần tính. Ngoài ra, nến phải
  đã đóng tại `fetched_at` của snapshot: `close_time < fetched_at_UTC_ms`.
  Điều này ngăn coi giá của nến từng đang mở trong cache là giá đóng cuối cùng.
  Không được sửa hoặc loại nến trong response market data gốc.
- **FR-008**: PHẢI có lựa chọn rõ ràng để tính cả nến chưa đóng, mặc định tắt.
  Khi bật, dùng toàn bộ nến hợp lệ của snapshot, không dự đoán giá đóng.
  Mọi điểm phụ thuộc nến không thỏa FR-007 PHẢI có cờ tạm thời; các điểm thiếu
  dữ liệu vẫn giữ giá trị `null`. Kết quả PHẢI cho biết chính sách đã chọn,
  thời điểm đánh giá và số nến bị loại. Tạm thời và stale là hai cờ độc lập.
- **FR-009**: PHẢI giữ nguyên độ chính xác chuỗi giá đầu vào; giá trị chỉ báo
  trả dưới dạng chuỗi thập phân hoặc `null`, không làm tròn giá đầu vào hoặc
  trạng thái trung gian để phục vụ hiển thị. So với giá trị toán học đối chiếu,
  sai số tuyệt đối không vượt `max(1e-12, abs(giá_trị_đối_chiếu) * 1e-12)`.
  Kết quả RSI PHẢI nằm trong [0, 100].
- **FR-010**: PHẢI giữ nhận diện market, symbol, interval và metadata nguồn
  `source`, `stale`, `warning`, `fetched_at`, `cache_key` trong kết quả tính.
  Timestamp nến và thời điểm đánh giá dùng UTC milliseconds; `fetched_at` giữ
  UTC ISO 8601. Không cập nhật thời điểm fetch thành thời điểm tính chỉ báo.
- **FR-011**: PHẢI giữ nguyên hành vi API market data và CLI hiện có, gồm schema,
  validation, số lượng nến, nến chưa đóng, lỗi nguồn và Redis. Không thêm chỉ báo
  vào response cũ hoặc sửa key/payload/TTL cache market data để chứa chỉ báo.
  Giữ phân biệt Spot/Futures/host, retry/cooldown, stale fallback và lock hiện có.
- **FR-012**: Chỉ tính trên snapshot do luồng market data hiện có cung cấp,
  không tự phân trang, tăng limit, fetch bù hoặc dựng kho lịch sử để đạt đủ N.
  Giữ limit hiện có 1–1000, mặc định 300; limit nhỏ hơn số nến yêu cầu vẫn hợp lệ.
  Không lưu lâu dài hoặc tạo cache chỉ báo trong phạm vi này.
- **FR-013**: PHẢI khởi tạo và tính EMA/RSI từ đầu snapshot được chọn cho mỗi lần
  tính; không ngầm dùng trạng thái lần gọi trước. Cùng chuỗi được chọn và tham số
  phải cho cùng kết quả; snapshot có điểm bắt đầu khác có thể cho EMA/RSI khác.
  Kết quả PHẢI cho biết điểm bắt đầu chuỗi để người dùng đối chiếu khác biệt này.
- **FR-014**: PHẢI có nghiệm thu tự động bằng dữ liệu cố định và mock cho công thức,
  seed, biên N, độ chính xác, chính sách nến, metadata và tương thích market data/cache.
  Không gọi Binance hoặc Redis thật trong bộ test backend tự động; tái sử dụng
  kiến trúc hiện có theo hiến chương, không tạo luồng lấy dữ liệu song song.
- **FR-015**: PHẢI cung cấp API chỉ báo riêng để tính và nhận kết quả theo yêu cầu,
  tái sử dụng luồng market data hiện có. Không thêm lệnh CLI hoặc giao diện UI mới.
  Không triển khai rule engine, đánh giá điều kiện, gửi cảnh báo, giao dịch, SQL,
  scheduler hoặc tích hợp biểu đồ/UI mới. Lỗi nguồn được truyền theo hành vi cũ;
  không giả lập kết quả chỉ báo khi nguồn lỗi.

### Thực thể dữ liệu chính

- **Snapshot nến**: Chuỗi giá/thời gian cùng nhận diện market, symbol, interval,
  nguồn, thời điểm fetch, trạng thái stale và cảnh báo; không bị phép tính sửa đổi.
- **Yêu cầu chỉ báo**: Tập chỉ báo và chu kỳ từng chỉ báo, lựa chọn nến mở,
  phạm vi nến theo limit hiện có; mặc định chỉ nến đóng. Cặp tên chỉ báo và chu kỳ
  là duy nhất trong yêu cầu; cùng loại có thể xuất hiện với các chu kỳ khác nhau.
- **Kết quả chỉ báo**: Chuỗi điểm và giá trị mới nhất, số nến yêu cầu/đủ điều kiện/
  bị loại, đầu chuỗi, thời điểm đánh giá, chính sách nến và metadata snapshot;
  mỗi kết quả được nhận diện bằng tên chỉ báo và chu kỳ.
- **Điểm chỉ báo**: Thời gian nến UTC milliseconds, giá trị thập phân hoặc `null`,
  trạng thái đủ/thiếu dữ liệu, cờ tạm thời; gắn đúng nến, không dịch lệch thời gian.

## Tiêu chí thành công *(bắt buộc)*

### Kết quả đo lường được

- **SC-001**: 100% trường hợp đối chiếu cho ba chỉ báo, gồm seed và ít nhất hai
  bước sau seed, nằm trong sai số FR-009; bao gồm chuỗi tăng, giảm, đi ngang và hỗn hợp.
- **SC-002**: 100% trường hợp 0, N-1, N, N+1 nến và N=1 phân biệt đúng đủ dữ liệu,
  thiếu dữ liệu và đầu vào không hợp lệ; không có giá trị giả thay cho dữ liệu thiếu.
- **SC-003**: 100% trường hợp nến mở, đúng thời điểm đóng và snapshot cũ cho đúng
  tập nến/cờ tạm thời theo chính sách; metadata nguồn được giữ nguyên.
- **SC-004**: Toàn bộ kịch bản market data/cache hiện có tiếp tục đạt sau bổ sung;
  người dùng hiện tại không phải đổi yêu cầu hay cách đọc response cũ.
- **SC-005**: Người sử dụng xác định được chỉ báo, chu kỳ, mốc thời gian, tính tạm
  thời, độ cũ và lý do chưa có giá trị chỉ từ kết quả trong mọi kịch bản nghiệm thu,
  không cần đọc log hoặc suy đoán từ giá trị 0.
- **SC-006**: Với cùng snapshot và tham số cố định, 100 lần tính liên tiếp cho
  cùng giá trị, không làm đổi nến nguồn hoặc gia hạn thời gian sống của dữ liệu.

## Giả định

- “Theo phương pháp Wilder” được hiểu là áp dụng cho RSI; SMA là trung bình cộng,
  EMA dùng `2/(N+1)`. Không bổ sung một chỉ báo Wilder moving average riêng.
- Mặc định chu kỳ 14 cho mỗi chỉ báo là lựa chọn sản phẩm cho lần đầu; cho phép
  cấu hình riêng từng chỉ báo. Giới hạn 999 cho phép RSI có khả năng đủ dữ liệu
  trong tối đa 1000 nến của hợp đồng hiện tại, nhưng không bảo đảm đủ sau lọc nến mở.
- Quy ước RSI=50 khi không có gain và loss thể hiện trạng thái trung tính; đây là
  quy ước của tính năng, không cam kết giống mọi thư viện hoặc nền tảng bên ngoài.
- Chuỗi kết quả, không chỉ giá trị cuối, là đầu ra của API chỉ báo riêng để đối chiếu
  theo từng nến; đường dẫn và thiết kế hợp đồng chi tiết được xác định trong kế hoạch.
  Phạm vi API riêng, chưa thêm CLI/UI, đã được người dùng xác nhận.
- Phụ thuộc snapshot có metadata tin cậy từ luồng market data hiện tại và đồng hồ UTC.
  Nến có giá snapshot từ trước thời điểm đóng không được coi là giá đóng cuối cùng.
- Đây là đặc tả cho chức năng chưa triển khai. Rules trên UI hiện có vẫn là mock/
  localStorage; indicator, rule engine và gửi cảnh báo không được đánh đồng.
- Tuân thủ [hiến chương](../../.specify/memory/constitution.md), hiện trạng trong
  [README](../../README.md) và manifest backend/frontend đã đối chiếu ở bước lập
  hiến chương; không yêu cầu đổi công nghệ hoặc bổ sung hạ tầng trong đặc tả này.
