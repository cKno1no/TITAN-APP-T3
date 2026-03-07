# Ý tưởng đột phá: Kiến trúc & Phong cách thiết kế  
## Portal & Nhập liệu — Trải nghiệm mượt mà, ấn tượng

*Tập trung vào **cảm giác** và **bản sắc hình ảnh** hơn là thêm chức năng. Mục tiêu: vào trang là nhớ, dùng xong là muốn quay lại.*

---

## A. PORTAL (Trang chủ / Cockpit)

### 1. Kiến trúc: "Một dòng tóm tắt" — Status Strip

**Ý tưởng:** Thêm **một thanh ngang cố định** (hoặc ngay dưới header) chỉ gồm 1 câu:  
*"Hôm nay: 3 task · 2 báo giá chờ · 0 nợ quá hạn"* (số liệu lấy từ data hiện có).

- **Tại sao ấn tượng:** Người dùng **đọc xong trong 2 giây** mà không cần mở bất kỳ card nào. Cảm giác "hệ thống đã tóm gọn giúp tôi".
- **Thiết kế:** Nền mờ (glass), chữ rõ, có thể kèm icon nhỏ; không chiếm diện tích. Có thể đổi màu nhẹ khi có cảnh báo (ví dụ có nợ quá hạn → viền/icon đỏ nhạt).

---

### 2. Kiến trúc: "Độ sâu" — Urgent nổi, còn lại lùi

**Ý tưởng:** Không phải tất cả card cùng "độ ưu tiên" về mặt thị giác.  
- Card **Khẩn cấp** (task trễ, nợ quá hạn): shadow đậm hơn, scale nhẹ (1.02), có thể thêm viền màu hoặc icon nhấp nháy nhẹ.  
- Các card khác: shadow nhạt hơn, opacity 0.95, cảm giác "ở phía sau".

- **Tại sao ấn tượng:** Mắt tự nhiên đi tới "điều cần làm trước". Trang không chỉ đẹp mà còn **có thứ bậc rõ ràng**.

---

### 3. Phong cách: "Chào theo buổi" — Cảm xúc theo thời gian

**Ý tưởng:** Hero "Chào, [Tên]!" không chỉ là chữ — thay đổi **tông màu / hình nền** theo buổi (sáng / chiều / tối) hoặc theo trạng thái ngày (có overdue → tông ấm/cảnh báo nhẹ; không → tông xanh mát).

- **Cách làm đơn giản:** 2–3 biến CSS (gradient gốc, gradient sáng, gradient tối). JS lấy `new Date().getHours()` và gán class cho hero → đổi `background` của block chào.
- **Tại sao ấn tượng:** Trang có **nhịp sinh học** — cảm giác hệ thống "biết" đang là lúc nào trong ngày.

---

### 4. Phong cách: "Command Palette" — Một phím, đi khắp nơi

**Ý tưởng:** Nhấn **Ctrl+K** (hoặc Cmd+K) → hiện overlay **tìm nhanh**: gõ "task", "kpi", "crm", "dự phòng"... → hiện 4–5 lựa chọn (Task, KPI, Viết CRM, Tồn kho dự phòng, v.v.). Chọn = chuyển trang hoặc mở tab.

- **Tại sao ấn tượng:** Giống Linear / Vercel / Notion — cảm giác **sản phẩm cao cấp**, dành cho người dùng thường xuyên. Không cần nhớ menu, chỉ cần nhớ một phím.

---

### 5. Phong cách: "Skeleton không chỉ là loading"

**Ý tưởng:** Lần đầu load Portal, thay vì trắng xoá hoặc spinner giữa màn hình: **skeleton theo đúng layout bento** (hình chữ nhật bo góc, gợn sóng shimmer). Sau khi data về, skeleton từng khối lần lượt "tan" thành nội dung thật (fade hoặc morph).

- **Tại sao ấn tượng:** Người dùng **thấy cấu trúc trang ngay từ giây đầu** — cảm giác nhanh, có chủ đích, không "đơ".

---

### 6. Bản sắc: "Một điểm nhấn nhỏ nhưng nhớ"

**Ý tưởng:** Thêm **một yếu tố đồ họa cố định** (illustration nhỏ, icon đặc trưng, hoặc pattern tinh tế) chỉ xuất hiện ở góc hero hoặc empty state — không lấn nội dung. Ví dụ: hình isometric nhỏ "văn phòng" hoặc logo Titan dạng mark.  
Mục tiêu: nhìn là nhận ra "đây là Titan OS", không lẫn với dashboard generic.

---

## B. NHẬP LIỆU (Soạn Báo Cáo CRM)

### 1. Kiến trúc: "Trang là tài liệu, form là phụ"

**Ý tưởng:** Hiện tại trang đọc như **form** (nhiều ô, accordion, label). Đổi góc nhìn: **nội dung chính là "bài viết"**, còn Khách hàng / Loại báo cáo / Ngày / Mục đích là **metadata** gói gọn trong một thanh cố định (sticky) phía trên hoặc sidebar hẹp.

- **Layout gợi ý:** Phía trên: một dải metadata (KH, loại, ngày, mục đích) — có thể thu gọn thành 1 dòng. Bên dưới: **editor chiếm gần full width**, font chữ thoáng, line-height rộng.
- **Tại sao ấn tượng:** Cảm giác **đang soạn một bản báo cáo**, không phải "điền form". Giảm áp lực tâm lý, tăng tập trung vào nội dung.

---

### 2. Phong cách: "Focus mode" — Chỉ còn chữ

**Ý tưởng:** Nút **"Chế độ viết"** (icon fullscreen hoặc bút): ẩn header, sidebar tag, chỉ còn **editor + thanh công cụ tối giản** (in đậm, in nghiêng, có thể thêm "Chèn thẻ"). Nền tối nhẹ hoặc màu kem để giảm chói.

- **Tại sao ấn tượng:** Giống iA Writer / Notion focus — **không bị phân tâm**, cảm giác chuyên nghiệp dành cho người viết nhiều.

---

### 3. Phong cách: "Mẫu là lựa chọn, không phải dropdown"

**Ý tưởng:** Thay dropdown "Dùng mẫu" bằng **3–4 card** (icon + tiêu đề ngắn): ví dụ "Gặp gỡ giới thiệu SP", "Chăm sóc định kỳ", "Xử lý khiếu nại". Click card = điền sẵn Mục đích + (tuỳ chọn) gợi ý đoạn mở đầu cho Tab A.

- **Tại sao ấn tượng:** Mẫu trở thành **hành động có ý nghĩa** (chọn "kịch bản"), không còn là một ô trong form. Gợi cảm giác "hệ thống hiểu cách tôi làm việc".

---

### 4. Phong cách: "Nhịp điệu chữ" — Typography làm chủ

**Ý tưởng:** Định nghĩa **type scale** rõ (tiêu đề section, tiêu đề nhỏ, body, chú thích) và **khoảng trắng** hào phóng quanh editor. Có thể dùng **serif** cho nội dung báo cáo (Georgia, Lora, hoặc font có sẵn) để phân biệt "đây là nội dung cần đọc" so với label form.

- **Tại sao ấn tượng:** Trang không chỉ "có chữ" mà **chữ tạo nhịp** — cảm giác chỉn chu, đáng tin.

---

### 5. Cảm xúc: "Xác nhận lưu không im lặng"

**Ý tưởng:** Sau khi lưu thành công: ngoài toast, có thể thêm **micro-animation** rất ngắn (ví dụ icon check lớn nổi lên rồi fade, hoặc một vệt màu xanh chạy ngang nút "Lưu"). Mục tiêu: **khoảnh khắc "đã xong"** rõ ràng, tạo thói quen tích cực.

- **Tại sao ấn tượng:** Hành động "Lưu" có **phản hồi cảm xúc** — người dùng cảm thấy được xác nhận, không nghi ngờ "đã gửi chưa?".

---

### 6. Bản sắc: "Một không gian cố định cho viết"

**Ý tưởng:** Đặt trang trong **một "khung" đồ họa nhẹ** (ví dụ viền mỏng, hoặc nền editor khác biệt rõ với nền trang) để vùng soạn thảo luôn được nhận diện là "đây là chỗ tôi viết". Có thể kèm placeholder đẹp: *"Kể lại cuộc gặp và kết quả đạt được..."*.

- **Tại sao ấn tượng:** Không gian viết có **ranh giới rõ** — tâm lý "vào đây là để viết" thay vì "điền form".

---

## C. GỢI Ý ƯU TIÊN (ít code, nhiều ấn tượng)

| Trang    | Ý tưởng nên làm trước | Lý do |
|----------|------------------------|--------|
| **Portal** | Status strip (1 dòng tóm tắt) | Một dòng thêm, thông tin "at a glance", rất dễ nhớ. |
| **Portal** | Command palette (Ctrl+K) | Một component, tạo cảm giác sản phẩm cao cấp. |
| **Portal** | Skeleton đúng layout bento | Chỉ cần HTML/CSS skeleton + logic show/hide theo data. |
| **Nhập liệu** | Metadata thu gọn + editor rộng | Thay đổi layout nhẹ, cảm giác "trang tài liệu" ngay. |
| **Nhập liệu** | Nút "Chế độ viết" (focus mode) | Một class ẩn/hiện, trải nghiệm khác biệt rõ. |
| **Nhập liệu** | Mẫu dạng card thay dropdown | 3–4 card, click gán value — ấn tượng và dễ dùng. |

---

## D. Tóm tắt triết lý

- **Portal:** "Một cái nhìn biết hết — một phím đi khắp — nhịp theo ngày."  
  → Kiến trúc: tóm tắt + độ sâu + command; phong cách: chào theo buổi + skeleton có chủ đích + một điểm nhấn nhận diện.

- **Nhập liệu:** "Trang là tài liệu — viết là trọng tâm — lưu là khoảnh khắc."  
  → Kiến trúc: metadata gọn, editor làm trung tâm; phong cách: focus mode + mẫu dạng card + typography và micro-animation khi lưu.

Tài liệu này có thể dùng làm **brief thiết kế** hoặc **backlog** khi triển khai từng bước — ưu tiên những mục tạo **cảm giác mượt mà và ấn tượng** trước, chức năng nền giữ nguyên.
