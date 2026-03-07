# Báo cáo review: Module Duyệt PO/DPO (folder claude)

## 1. Tổng quan

Module gồm: **Blueprint** (`po_approval_bp.py`), **Service** (`po_approval_service.py`), **Template** (`po_approval_dashboard.html`), và **SQL** (gemini_01–04): bảng audit, SP risk context, SP validation 2 tầng, SP pending list + approve. Luồng: dashboard lọc theo ngày/loại phiếu → modal 3 tab (Kiểm tra & Duyệt, Chi tiết dòng hàng, Risk Debug) → re-verify 5 tầng khi duyệt → gọi `sp_ApprovePO`.

---

## 2. Ưu điểm

- **Kiến trúc rõ:** Tách BP / Service / SP, dễ bảo trì và test.
- **Validation nhiều tầng:** 5 tầng (link dòng, giá, risk context, risk score, escalation GM/MGR) phù hợp quy trình duyệt mua hàng.
- **Phân quyền:** SP `sp_GetPOPendingList` dùng `@UserRole` (ADMIN/GM/MANAGER/SALES) để giới hạn PO theo nhân viên; template ẩn nút theo `CanSelfApprove` / `RequiresGM` / `is_admin`.
- **Audit:** Bảng `CRM_PO_Approval_History`, `CRM_PO_Violation_History`, `CRM_DHB_Risk_History` lưu lịch sử duyệt và vi phạm.
- **Re-verify khi duyệt:** Trước khi gọi `sp_ApprovePO`, service gọi lại `run_full_check` để tránh duyệt dựa trên kết quả cũ.
- **Risk scoring có cấu trúc:** `PORiskScorer` dùng tham số cấu hình (tháng tồn, ngưỡng giá, escalation) và trả về verdict + cấp duyệt.
- **UI:** Filter theo ngày/loại phiếu, stat chips, modal 3 tab, trạng thái màu theo block/warn/ok.

---

## 3. Nhược điểm

- **Ô tìm kiếm chưa dùng:** Form có `name="search"` và `htx-include` nhưng `get_orders_for_approval()` không nhận tham số search và SP không lọc theo từ khóa → search hiện không có tác dụng.
- **Risk debug dùng CSV chuỗi:** `inv_list = ','.join(lines_map.keys())` gửi danh sách InventoryID; nếu mã vật tư chứa dấu phẩy sẽ parse sai phía SP.
- **Trùng CSS:** Hai khai báo rule cho `.rfl-pts` trong template.
- **Config PO chưa có trong `config.py`:** Ứng dụng sẽ lỗi khi gọi service vì thiếu: `SP_PO_PENDING_LIST`, `SP_PO_CHECK_LINES`, `SP_PO_CHECK_PRICE`, `SP_PO_RISK_CONTEXT`, `SP_PO_APPROVE`, `TABLE_DHB_RISK_HISTORY`, `PO_RISK_SCORE_ESCALATE_GM`, `PO_RISK_SCORE_ESCALATE_MGR`, `PO_RISK_MONTHS_*`, `PO_RISK_PRICE_*` (xem mục 4).

---

## 4. Lỗi và rủi ro

### 4.1 Lỗi cần sửa ngay

| Mục | Mô tả | Hậu quả |
|-----|--------|---------|
| **VoucherNo vs VoucherDisplay** | SP `sp_GetPOPendingList` trả về cột `VoucherDisplay` (alias của `VoucherNo`). Service dùng `dict(r)` nên key là `VoucherDisplay`. Template dùng `order.VoucherNo` ở nhiều chỗ. | Cột số phiếu trống hoặc lỗi hiển thị trên dashboard và modal. |
| **is_admin không truyền vào template** | `render_template` trong `po_approval_dashboard()` không truyền `is_admin`. Template dùng `is_admin` (ẩn/hiện nút, tab Risk Debug). | Jinja có thể báo undefined; nút duyệt/override và tab Risk Debug không đúng theo quyền. |
| **Thiếu cấu hình PO trong config** | `config.py` hiện không có: `SP_PO_PENDING_LIST`, `SP_PO_CHECK_LINES`, `SP_PO_CHECK_PRICE`, `SP_PO_RISK_CONTEXT`, `SP_PO_APPROVE`, `TABLE_DHB_RISK_HISTORY`, `PO_RISK_SCORE_ESCALATE_GM`, `PO_RISK_SCORE_ESCALATE_MGR`, `PO_RISK_MONTHS_WARN/HIGH/CRITICAL`, `PO_RISK_PRICE_THRESHOLD_PCT`, `PO_RISK_PRICE_HISTORY_DAYS`. | `AttributeError` khi chạy bất kỳ route PO approval nào. |

### 4.2 Rủi ro nghiệp vụ

| Rủi ro | Mô tả | Đề xuất |
|--------|--------|---------|
| **Duyệt khi re-verify lỗi** | Trong `approve_purchase_order`, nếu `run_full_check` ném exception thì `server_check = None`; code vẫn dùng payload từ client để gọi `sp_ApprovePO`. | Khi `server_check is None`: **không gọi SP**, trả về 403/400 và bắt buộc user mở lại modal chạy kiểm tra lại. |
| **Risk context CSV** | InventoryID đưa vào SP risk context dạng chuỗi CSV; InventoryID có dấu phẩy sẽ làm sai. | Dùng table-valued parameter (TVP) hoặc bảng tạm, hoặc escape/chuẩn hóa (ví dụ không cho dấu phẩy trong mã). |
| **Session trong template** | Template dùng `session.user_code`; Flask session là dict-like, nên dùng `session.get('user_code')` an toàn hơn (tránh KeyError nếu chưa login). | Ở view đảm bảo route có `@login_required`; trong template có thể dùng `session.get('user_code', '')` nếu muốn an toàn. |

### 4.3 Code smell / nhất quán

- **Import trùng:** Trong `po_approval_bp.py`, `datetime`/`timedelta` được import ở đầu file và có thể import lại trong hàm; nên giữ một lần ở đầu.
- **Risk debug dùng `cfg`:** Trong bp, route risk_debug dùng `from config import config as cfg` và `cfg.SP_PO_RISK_CONTEXT`; các chỗ khác dùng `config` → nên thống nhất dùng `config`.
- **Database cứng:** Một số SP/query ghi cứng `[OMEGA_STDD]`; nên lấy từ config (ví dụ `ERP_DB`) để dễ đổi môi trường.

---

## 5. Khả năng tối ưu

- **Hiệu năng:** Dashboard gọi `get_orders_for_approval` không chạy full 5 tầng (chỉ dùng AllLinesLinked từ SP) → đúng hướng. Có thể thêm phân trang hoặc giới hạn số dòng (TOP N) trong SP nếu danh sách rất lớn.
- **Search:** Implement search: SP thêm tham số `@Search NVARCHAR(100)` (lọc theo VoucherNo / SupplierName / EmployeeName) và service + form truyền `search` từ request.
- **Cache risk context:** Nếu cùng một PO được mở nhiều lần, có thể cache kết quả risk context theo `porder_id` (TTL ngắn, ví dụ 1–2 phút) để giảm gọi SP.
- **Frontend:** Tránh gửi nguyên `order` trong `data-order` (có thể to); chỉ gửi `POrderID` và gọi `/api/po/check_result/<id>` khi mở modal (đã có sẵn).
- **SP:** `sp_CheckPOLines` / `sp_CheckPOPriceHistory` có thể thêm chỉ số (index) phù hợp trên bảng PT3002 / bảng giá theo `POrderID`, `InventoryID`, `PriceDate` nếu truy vấn chậm.

---

## 6. Checklist triển khai

- [ ] Thêm toàn bộ hằng PO (SP_*, TABLE_*, PO_RISK_*) vào `config.py`.
- [ ] Trong service: sau `order = dict(r)` thêm `order['VoucherNo'] = order.get('VoucherDisplay', order.get('VoucherNo', ''))`.
- [ ] Trong `po_approval_dashboard()`: tính `is_admin` (ví dụ `(session.get('user_role') or '').upper() in ('ADMIN', 'GM')`) và truyền `is_admin=is_admin` vào `render_template`.
- [ ] Khi `server_check is None` trong `approve_purchase_order`: không gọi SP, trả về JSON lỗi và message “Cần chạy lại kiểm tra”.
- [ ] Đăng ký blueprint và service trong factory (app) nếu chưa có: `app.po_approval_service = ...`, `app.register_blueprint(po_approval_bp)`.
- [ ] Deploy script SQL gemini_01 → 04 lên DB đích (CRM_STDD + OMEGA_STDD) và kiểm tra tên SP/table trùng với config.

---

## 7. Ghi chú tích hợp

- **Config:** Các hằng PO (SP_PO_*, TABLE_DHB_RISK_HISTORY, PO_RISK_*) đã được thêm vào `config.py` ở thư mục gốc T3.
- **Factory:** Cần đăng ký blueprint và service khi đưa module vào app:
  - Import: `from claude.po_approval_bp import po_approval_bp` (hoặc copy `po_approval_bp.py` vào `blueprints/` rồi import từ `blueprints.po_approval_bp`).
  - Import service: `from claude.po_approval_service import POApprovalService` (hoặc tương ứng nếu đổi vị trí file).
  - Trước `return app`: `app.po_approval_service = POApprovalService(app.db_manager)` và `app.register_blueprint(po_approval_bp)`.
- **Template:** Đặt `po_approval_dashboard.html` vào thư mục `templates/`.
- **Phân quyền:** Đảm bảo có quyền `APPROVE_PO` trong `SYSTEM_FEATURES_GROUPS` (nhóm "QUYỀN PHÊ DUYỆT") và gán cho role tương ứng.

---

*Tài liệu này dùng để review và triển khai module Duyệt PO/DPO. Các sửa lỗi ở mục 4.1 đã được áp dụng: service (VoucherNo, re-verify khi server_check None), blueprint (is_admin), config (PO constants).*
