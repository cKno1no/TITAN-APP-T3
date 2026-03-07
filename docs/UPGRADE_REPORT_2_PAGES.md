# Báo cáo nâng cấp UX/UI – 2 trang tiếp theo

## 1. Hai trang được chọn

| # | Trang | File | Lý do chọn |
|---|--------|------|------------|
| 1 | **Đề nghị thanh toán (Budget Dashboard)** | `budget_dashboard.html` | Form tạo phiếu đề nghị chi phí là luồng nghiệp vụ quan trọng; hiện dùng nhiều `alert()` và `confirm()`; thiếu validation inline, loading nút và phản hồi thân thiện (toast). Cải thiện ở đây tác động trực tiếp đến trải nghiệm tài chính. |
| 2 | **Phê duyệt nhanh (Quick Approval Form)** | `quick_approval_form.html` | Trang duyệt Chào giá & Đơn hàng dùng nhiều `alert()`/`confirm()`; logic chặn cứng (failed hard) và override cần modal rõ ràng hơn; cần toast, loading nút chuẩn và empty state khi không có phiếu. |

**Các trang đã nâng cấp trước đó:** `task_dashboard.html`, `kpi_evaluation.html`.

---

## 2. Budget Dashboard – Hiệu chỉnh lỗi & cải tiến

### 2.1 Lỗi / rủi ro hiện tại

- **Validation chỉ bằng alert:** Thiếu lý do, số tiền, loại chi phí, đối tượng → toàn bộ dùng `alert()`; người dùng không thấy lỗi gắn với từng ô.
- **confirm("Xác nhận gửi đề nghị?")** → trải nghiệm thô, không thống nhất với các trang đã dùng SweetAlert.
- **Thành công / lỗi:** `alert()` rồi reload hoặc bật lại nút; không có toast, dễ bỏ lỡ thông báo.
- **Nút gửi:** Có loading text nhưng không có spinner rõ, dễ nhầm với trạng thái bình thường.
- **Bảng lịch sử:** Empty state chỉ là một dòng chữ "Chưa có dữ liệu."; không có icon/CTA.
- **CSS inline trong template:** Khó bảo trì; chưa tách file riêng như task_dashboard / kpi_evaluation.

### 2.2 Cải tiến áp dụng

- **Validation inline:** Thẻ lỗi dưới từng field (loại chi phí, đối tượng, số tiền, lý do); xóa lỗi khi user sửa.
- **Toast thay alert:** Thành công → SweetAlert toast → reload sau ~1.5s; lỗi → toast, không reload, giữ form.
- **Xác nhận gửi:** Dùng SweetAlert modal (title + text) thay `confirm()`.
- **Loading nút:** Nút "Gửi Đề Nghị" có id; khi submit: disabled + spinner + "Đang gửi..."; khi lỗi trả về text/spinner như cũ.
- **Empty state bảng:** Khi không có `my_requests`: block có icon + text + (tuỳ chọn) CTA "Tạo phiếu mới" (scroll đến form).
- **Tách CSS:** Tạo `static/css/budget_dashboard.css`, link trong `extra_css`; thêm padding card/form/table để nội dung không dính viền.
- **A11y:** `aria-label` cho ô tìm kiếm, nút gửi; `aria-describedby` cho các ô có lỗi inline.

### 2.3 Ý tưởng đột phá (Budget Dashboard)

- **Ô “Kiểm tra ngân sách” (budgetStatusBox):** Khi đang gọi `check_balance` hiển thị trạng thái loading (spinner + "Đang kiểm tra...") thay vì chỉ bật box sau khi có kết quả.
- **Gợi ý nhanh:** Sau khi chọn loại chi phí, có thể (sau này) gợi ý đối tượng thụ hưởng gần đây theo loại chi phí đó.
- **Lưu bản nháp (future):** Nút "Lưu nháp" lưu localStorage form để tránh mất dữ liệu khi reload/đóng tab.

---

## 3. Quick Approval Form – Hiệu chỉnh lỗi & cải tiến

### 3.1 Lỗi / rủi ro hiện tại

- **alert() cho mọi tình huống:** Chưa chọn phiếu, chặn cứng (failed hard), override, thành công, lỗi API → đều dùng alert; khó đọc và không thống nhất.
- **confirm() cho override:** Câu dài, xuống dòng trong alert; cần modal có tiêu đề + nội dung rõ (cảnh báo vàng).
- **Thành công:** alert rồi `location.reload()`; nên dùng toast rồi reload sau vài giây.
- **Empty state:** Khi `quotes`/`orders` rỗng, select chỉ có option "-- Vui lòng chọn phiếu --"; không có block empty có icon + hướng dẫn.
- **CSS inline:** Giống budget_dashboard, nên tách file.

### 3.2 Cải tiến áp dụng

- **SweetAlert cho chặn cứng (failed hard):** Modal icon error, title "Không thể duyệt", nội dung lý do + gợi ý "Cần NV kinh doanh sửa lại"; không dùng alert.
- **SweetAlert cho xác nhận (bình thường & override):** Modal xác nhận; nếu override thì thêm cảnh báo vàng (icon warning, text rõ).
- **Toast cho kết quả:** Thành công → toast success → reload sau ~1.5s; lỗi API → toast error, bật lại nút.
- **Loading nút:** Giữ spinner + "Đang xử lý...", thêm id cho từng nút để reset chính xác.
- **Empty state từng card:** Nếu không có quote/order: ẩn hoặc thay input + select bằng block "Chưa có phiếu nào trong 90 ngày" + icon; có thể ẩn nút Duyệt khi empty.
- **Tách CSS:** `static/css/quick_approval_form.css`; padding card/input/button; focus-visible cho suggestion.
- **A11y:** aria-label cho ô tìm Chào giá / Đơn hàng và nút Duyệt; role/aria cho list gợi ý.

### 3.3 Ý tưởng đột phá (Quick Approval Form)

- **Phím tắt:** Ctrl+Enter (hoặc nút nhanh) để duyệt phiếu đang chọn, giảm số lần click.
- **Highlight phiếu vừa duyệt:** Sau khi reload, highlight (hoặc scroll đến) phiếu vừa duyệt nếu backend trả về id (hoặc dùng sessionStorage).
- **Lịch sử duyệt nhanh (future):** Một tab/section "Đã duyệt gần đây" trong 24h để kiểm tra nhanh.

---

## 4. Chuẩn áp dụng chung (đồng bộ với Task Dashboard & KPI Evaluation)

- **Toast:** SweetAlert `Swal.fire({ toast: true, position: 'top-end', ... })` cho success/error sau thao tác.
- **Loading nút:** Disabled + spinner icon + đổi text (ví dụ "Đang gửi...", "Đang xử lý...").
- **Xác nhận quan trọng:** SweetAlert modal (confirm/cancel), không dùng `confirm()`.
- **Validation:** Ưu tiên inline (thẻ lỗi dưới field); chỉ dùng modal/alert khi lỗi toàn form hoặc lỗi từ server không gắn field.
- **Empty state:** Icon + text ngắn + CTA nếu phù hợp (ví dụ "Tạo phiếu mới").
- **CSS:** Tách file riêng; padding/margin để chữ và control không dính viền; focus-visible cho a11y.
- **Sau thành công:** Toast → `setTimeout(() => location.reload(), 1500)` (hoặc tương đương).

---

## 5. File giao nộp

| File | Mô tả |
|------|--------|
| `docs/UPGRADE_REPORT_2_PAGES.md` | Báo cáo này (lý do chọn, lỗi, cải tiến, đột phá). |
| `static/css/budget_dashboard.css` | CSS cho Budget Dashboard (tách từ inline + bổ sung). |
| `templates/budget_dashboard.html` | Full bản HTML nâng cấp (link CSS, validation inline, toast, Swal, empty state, a11y). |
| `static/css/quick_approval_form.css` | CSS cho Quick Approval Form. |
| `templates/quick_approval_form.html` | Full bản HTML nâng cấp (toast, Swal confirm/block, empty state, a11y). |
