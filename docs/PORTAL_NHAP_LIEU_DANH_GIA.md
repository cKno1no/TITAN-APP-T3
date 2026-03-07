# Đánh giá & Phương án cải tiến: Portal Dashboard & Nhập liệu

## 1. Portal Dashboard (Cockpit)

### Hiện trạng
- **Ưu điểm:** Bento layout rõ ràng, glassmorphism, modals chi tiết (Task, Nợ, Báo giá, Giao hàng...), progress ring KPI, phân quyền theo phòng ban (is_kho, is_acc, is_sales).
- **Hạn chế:** Toàn bộ CSS inline (~85 dòng), script animation inline; chưa có phản hồi khi load (skeleton/toast); không có nút "Làm mới" rõ ràng; empty state một số khối chỉ là text nhỏ.

### Đã thực hiện
- Tách CSS → `static/css/portal_dashboard.css` (đặt tên keyframe tránh trùng: `portal-float`, `portal-fadeInUp`, `portal-glowRed`, `portal-pulse`).
- Tách JS → `static/js/portal_dashboard.js` (animation vòng tròn KPI khi load).
- Template chỉ còn link 1 CSS + 1 JS.

### Ý tưởng đột phá (gợi ý triển khai sau)
| Ý tưởng | Mô tả | Lợi ích UX |
|--------|--------|------------|
| **One-click shortcuts** | Floating bar hoặc dropdown "Hành động nhanh": Lên Plan, Viết CRM, Xem KPI, Daily Challenge – mở tab mới hoặc slide-over panel. | Giảm số lần click, người dùng thường xuyên vào đúng luồng trong 1 click. |
| **Personalized greeting** | Hiển thị tên + thông điệp theo buổi (sáng/chiều/tối) hoặc theo ngày trong tuần; gợi ý 1 việc "Nên làm ngay" dựa trên overdue/task. | Cảm giác được dẫn dắt, tăng engagement. |
| **Làm mới không reload** | Nút "Làm mới" gọi API dashboard (nếu có) hoặc reload trang; khi reload hiện toast "Đã cập nhật dữ liệu". | Người dùng chủ động cập nhật mà không bối rối. |
| **Keyboard shortcut** | Ví dụ: `Ctrl+K` mở ô tìm nhanh (quick search) đến Task / CRM / Khách hàng. | Power user làm việc nhanh hơn. |
| **Skeleton loading** | Lần đầu vào trang: hiện skeleton cho từng bento thay vì trống, sau khi data load xong mới render số liệu. | Giảm cảm giác "đơ", trang có cảm giác nhanh hơn. |

---

## 2. Nhập liệu (Soạn Báo Cáo CRM)

### Hiện trạng
- **Ưu điểm:** Accordion rõ ràng (Thông tin & KH → Phân loại → Nội dung), tìm KH realtime, tag pool theo loại báo cáo, contenteditable editors, đính kèm file có validate (Swal) loại file + 10MB.
- **Hạn chế:** CSS inline (~95 dòng); submit form chỉ set hidden, không có loading; lỗi lấy nội dung chỉ alert; chưa có draft autosave.

### Đã thực hiện
- Tách CSS → `static/css/nhap_lieu.css`.
- Nút "Lưu Báo Cáo" thêm id `btn-submit-nhaplieu`, class `btn-submit-nhaplieu`.
- Trong `nhap_lieu.js`: khi submit → set hidden xong thì disable nút + đổi thành "Đang lưu..." + spinner; lỗi set hidden → Swal (fallback alert).
- Giữ nguyên logic tìm KH, tag pool, file validation (Swal) đã có.

### Ý tưởng đột phá (gợi ý triển khai sau)
| Ý tưởng | Mô tả | Lợi ích UX |
|--------|--------|------------|
| **Draft autosave** | Mỗi 30–60s lưu nội dung (loại BC, KH, 3 editor) vào localStorage; lần sau mở trang hỏi "Khôi phục bản nháp?" (Swal). | Tránh mất dữ liệu khi đóng nhầm hoặc sự cố. |
| **Validation inline** | Trước khi submit: kiểm tra đã chọn KH, đã chọn Mục đích/Kết quả/Hành động, nội dung Tab A tối thiểu N ký tự; lỗi highlight field + message bên dưới. | Lỗi rõ ràng ngay trên form, ít lần gửi lên server mới báo lỗi. |
| **Toast sau khi lưu** | Nếu server trả JSON (hoặc redirect kèm flash): sau khi submit thành công hiện toast "Đã lưu báo cáo #XXX" thay vì chỉ chuyển trang im lặng. | Người dùng biết chắc thao tác đã thành công. |
| **Template nhanh** | Dropdown "Dùng mẫu": chọn 1 trong 3–5 mẫu nội dung (ví dụ: Gặp gỡ giới thiệu SP, Chăm sóc định kỳ...) → điền sẵn Mục đích + gợi ý nội dung Tab A. | Giảm thời gian soạn, chuẩn hóa cách viết. |
| **Gợi ý AI** | Nút "Viết giúp tôi" bên cạnh editor: gửi ngữ cảnh (KH, Mục đích, vài dòng đã nhập) lên API AI, điền vào editor. | Hỗ trợ người dùng khi bí ý tưởng, tăng tốc nhập liệu. |

---

## 3. Tổng kết thay đổi code đã làm

- **user_profile.html:** Sửa lỗi đổi tên (Jinja `namespace` cho `has_rename_card`), Swal thay confirm/alert, input Swal thay prompt, loading khi gọi API, `.catch` và xử lý lỗi.
- **portal_dashboard.html:** Tách CSS/JS, giữ nguyên cấu trúc HTML và modals.
- **nhap_lieu.html:** Tách CSS, thêm loading nút submit và Swal khi lỗi map editor.
- **File mới:** `static/css/portal_dashboard.css`, `static/js/portal_dashboard.js`, `static/css/nhap_lieu.css`.
