# Đánh giá 5 file module Duyệt PO (sau khi tích hợp)

Đánh giá sau khi bạn đã chuyển file vào `blueprints/`, `services/`, `templates/` và cập nhật `factory.py`, `config.py`.

---

## 1. Tổng quan từng file

| File | Vị trí | Đánh giá ngắn |
|------|--------|----------------|
| **po_approval_bp.py** | blueprints/ | Route đủ, phân quyền + audit log ổn. Thiếu truyền `is_admin`, import trùng, risk_debug dùng `cfg` riêng. |
| **po_approval_service.py** | services/ | Logic 5 tầng rõ. Thiếu map VoucherNo, thiếu xử lý khi re-verify lỗi (server_check None). |
| **po_approval_dashboard.html** | templates/ | UI đủ, Alpine + HTMX. Phụ thuộc `is_admin` và `order.VoucherNo` từ backend. |
| **factory.py** | (gốc) | Đã import POApprovalService và po_approval_bp, gắn service và đăng ký blueprint — **ổn**. |
| **config.py** | (gốc) | Đã có SP_PO_*, PO_RISK_*, TABLE_DHB_RISK_HISTORY, APPROVE_PO — **đủ**. |

---

## 2. Điểm tốt (đã làm đúng)

- **Factory:** Import và đăng ký blueprint/service đúng thứ tự, không conflict.
- **Config:** SP, bảng, ngưỡng risk (GM 80, MGR 50, months 6/12/24), quyền APPROVE_PO đều có.
- **Blueprint:** Phân quyền DPO (Manager/GM), guard score ≥ 80 (chỉ GM), audit log sau khi duyệt, permission APPROVE_PO và record_activity.
- **Service:** Tách lớp rõ (get_orders, run_full_check, approve_purchase_order), re-verify trước khi gọi SP, dùng config thống nhất (trừ risk_debug trong bp).
- **Template:** Filter ngày/loại phiếu, stat chips, bảng PO, modal 3 tab, nút theo quyền; dùng biến môi trường CSS (var(--border-color)...).

---

## 3. Lỗi cần sửa ngay

### 3.1 Service — Số phiếu không hiển thị (VoucherNo)

- **Nguyên nhân:** SP `sp_GetPOPendingList` trả về cột **VoucherDisplay**, không trả **VoucherNo**. Service dùng `dict(r)` nên key là `VoucherDisplay`. Template dùng `order.VoucherNo` → undefined/trống.
- **Sửa:** Trong `get_orders_for_approval()`, sau `order = dict(r)` thêm:
  `order['VoucherNo'] = order.get('VoucherDisplay', order.get('VoucherNo', ''))`

### 3.2 Service — Duyệt khi re-verify lỗi (rủi ro bảo mật)

- **Nguyên nhân:** Khi `run_full_check(porder_id)` ném exception thì `server_check = None`. Code chỉ vào block `if server_check:` nên bỏ qua kiểm tra, nhưng vẫn chạy **Bước 2** và gọi `sp_ApprovePO` với payload từ client → có thể duyệt dù server không kiểm tra được.
- **Sửa:** Ngay sau khi gán `server_check = None`, thêm:
  - Nếu `server_check is None` thì **return** `{'success': False, 'message': '...'}` và **không** gọi SP.

### 3.3 Blueprint — Template báo lỗi / ẩn nút sai (is_admin)

- **Nguyên nhân:** `render_template(..., voucher_type_filter=voucher_type)` không truyền `is_admin`. Template dùng `is_admin` để hiện tab Risk Debug, nút Override, điều kiện nút Duyệt/Từ chối → Jinja có thể báo undefined hoặc ẩn/hiện sai.
- **Sửa:** Trong `po_approval_dashboard()` tính `is_admin` (ví dụ `(session.get('user_role') or '').upper() in ('ADMIN', 'GM')`) và truyền `is_admin=is_admin` vào `render_template`.

### 3.4 Blueprint — Import trùng và nhất quán config

- **Import trùng:** Trong `api_po_pending()` có `from datetime import datetime, timedelta` trong khi đầu file đã có — nên xóa dòng trong hàm.
- **Risk debug:** Trong `api_po_risk_debug` dùng `from config import config as cfg` và `cfg.SP_PO_RISK_CONTEXT`. Cả blueprint đã `import config` — nên dùng `config.SP_PO_RISK_CONTEXT` cho thống nhất.

---

## 4. Điểm nên cải tiến (không bắt buộc ngay)

### 4.1 Template — Ô tìm kiếm

- Form có ô search và HTMX (keyup delay 500ms) nhưng **không** gửi `name="search"` vào payload khiến backend không nhận. Service và SP cũng chưa có tham số search.
- **Gợi ý:** Hoặc thêm `hx-include="[name='search']"` và xử lý `search` trong view + service/SP, hoặc tạm bỏ/disable ô search cho đến khi implement đủ.

### 4.2 Template — HTMX search và swap

- Hiện `hx-post` của form search trỏ vào `po_approval_dashboard`, `hx-target="#po-table-container"`, `hx-select="#po-table-container"`. Nếu response trả về full page (render_template cả trang) thì `#po-table-container` có thể không tồn tại trong response → swap lỗi.
- **Gợi ý:** Đảm bảo view khi gọi bằng HTMX chỉ trả về fragment chứa `#po-table-container` (ví dụ dùng `request.headers.get('HX-Request')` và return fragment), hoặc tách endpoint riêng cho filter/search.

### 4.3 Blueprint — Database cứng trong api_po_detail / api_po_risk_debug

- SQL dùng `[OMEGA_STDD].[dbo].[PT3001]` v.v. Nên dùng `config.ERP_DB` (hoặc biến tương đương) để đổi môi trường (test/prod) dễ.

### 4.4 Service — Risk context dạng CSV

- `inv_list = ','.join(lines_map.keys())` (và tương tự trong record_dhb_risk). Nếu **InventoryID** có dấu phẩy sẽ làm sai khi parse trong SP.
- **Gợi ý:** Dùng TVP (table-valued parameter) hoặc quy ước mã vật tư không chứa dấu phẩy; hoặc escape/chuẩn hóa.

### 4.5 Template — Jinja session

- Dùng `session.user_code`; Flask session thường là dict → nên `session.get('user_code')` trong Python. Trong Jinja có thể giữ vì Flask session hỗ trợ attribute; nếu muốn an toàn có thể truyền `current_user_code` từ view.

---

## 5. Checklist sau khi sửa

- [ ] **Service:** Thêm map `VoucherNo` từ `VoucherDisplay` trong `get_orders_for_approval`.
- [ ] **Service:** Khi `server_check is None` thì return lỗi, không gọi `sp_ApprovePO`.
- [ ] **Blueprint:** Truyền `is_admin` vào `render_template` trong `po_approval_dashboard()`.
- [ ] **Blueprint:** Xóa import datetime/timedelta trùng trong `api_po_pending()`.
- [ ] **Blueprint:** Trong `api_po_risk_debug` dùng `config.SP_PO_RISK_CONTEXT` thay cho `cfg`.
- [ ] (Tùy chọn) Thêm xử lý search hoặc tạm bỏ/disable ô search; kiểm tra HTMX fragment khi filter.

---

## 6. Kết luận

- **Factory và config** đã được cập nhật đúng, không cần chỉnh thêm cho luồng cơ bản.
- **Ba lỗi cần sửa ngay:** (1) VoucherNo trong service, (2) không duyệt khi server_check is None trong service, (3) truyền is_admin trong blueprint. Sau đó nên chỉnh import và dùng config thống nhất trong blueprint.
- Các cải tiến còn lại (search, HTMX fragment, ERP_DB, CSV risk) có thể làm theo từng bước để tăng ổn định và bảo trì.
