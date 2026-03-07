# Báo cáo rà soát HTML Frontend – Titan OS

*Cập nhật sau đợt nâng cấp hàng loạt: hero strip, command bar, empty state, sticky table, CSS variables.*

---

## 1. Trạng thái theo nhóm

### 1.1. Đã nâng cấp đầy đủ (pattern: hero strip + command-bar/filter gọn + empty state có CTA + sticky table / card chuẩn)

| Template | Ghi chú |
|----------|--------|
| `sales_dashboard.html` | Hero strip, KPI cards, empty state + Về Portal |
| `sales_lookup_dashboard.html` | Command bar, empty state (nên đổi `#fefce8`/`#facc15` sang `var(--*)`) |
| `sales_order_approval.html` | Funnel strip, filter inline, sticky thead; empty chưa có nút CTA |
| `sales_details.html` | Hero strip, sticky table, empty state + Về Bảng tổng hợp |
| `study_room.html` | Strip, sidebar, viewer, empty states |
| `course_detail.html` | Hero strip, book card, empty state |
| `customer_profile.html` | Hero strip, KPI, drill-down (một số empty trong JS chưa có CTA) |
| `kpi_peer_review.html` | Hero strip, sidebar card, empty states, nút Về Portal |
| `ar_aging.html` | Hero strip, command bar, empty state + Về Portal |
| `ar_aging_detail.html` | Hero strip, command bar, empty state + Dashboard AR / Portal |
| `budget_ytd_report.html` | Hero strip, sticky table, empty + Về Dashboard NS, modal breadcrumb |
| `budget_payment_queue.html` | Hero strip, command bar, sticky table, empty + Về Dashboard NS |
| `audit_dashboard.html` | Hero strip, command bar, empty state + Về Portal, modal breadcrumb |
| `index_redesign.html` | Hero strip dưới welcome, badge dùng CSS vars |
| `realtime_dashboard.html` | Có realtime-hero-strip và realtime-empty-state (chưa thống nhất tên class) |

---

### 1.2. Có `page_title` / `page_sub` / `header_actions` nhưng chưa áp dụng đủ pattern

Các trang này đã dùng base blocks, có sticky table hoặc filter ổn, nhưng **thiếu hero strip** và/hoặc **empty state chưa có icon + CTA (Về Portal / trang trước)**.

| Template | Thiếu / Nên cải thiện |
|----------|------------------------|
| `dashboard.html` | Đã có `report-status-strip` và filter; empty "Không tìm thấy báo cáo" chưa có **icon + nút CTA**. |
| `quote_approval.html` | Có funnel strip, filter; empty "Không có báo giá nào" chỉ `text-center text-muted py-5` → thêm **empty-state class + icon + nút Về Portal**. |
| `sales_order_approval.html` | Empty "Không có đơn hàng nào" → thêm **empty-state + icon + CTA**. |
| `budget_dashboard.html` | Có filter, dropdown; empty "budget-history-empty" → thêm **icon + CTA** (Về Portal hoặc Tạo phiếu). |
| `budget_approval.html` | Empty "Không có đề nghị nào cần duyệt" → thêm **strip/empty-state + icon + CTA**. |
| `task_dashboard.html` | Có `kanban-empty-state`; bảng lịch sử empty "Không có dữ liệu phù hợp" → thêm **nút CTA**. |
| `quick_approval_form.html` | Có `approval-empty-state`; có thể thêm **nút Về Portal** trong empty. |
| `delivery_dashboard.html` | Chỉ header + content; nên thêm **hero strip** (tuần / trạng thái) và chuẩn hóa empty (nếu có). |
| `profit_dashboard.html` | KPI gradient hardcode (`#4318FF`, `#FFB547`…); empty "Không có dữ liệu phù hợp" → **empty-state + CTA**; nên thêm **hero strip** (khoảng ngày + KPIs). |
| `ap_aging.html` | KPI + table ổn, sticky; empty "Không tìm thấy dữ liệu" → **empty-state class + icon + nút Về Portal**. |
| `inventory_aging.html` | Sticky thead; empty "Không có dữ liệu tồn kho" → **empty-state + icon + CTA** (đã có nút Về Dashboard, có thể đưa vào cùng block empty). |
| `customer_replenishment.html` | Filter + table; empty trong JS ("Không tìm thấy…") → thống nhất **empty-state + CTA**. |
| `total_replenishment.html` | Empty "Không có dữ liệu" / "Không tìm thấy mã hàng" → **empty-state + CTA**. |
| `cross_sell_dashboard.html` | Có header_actions; nên **hero strip** (DNA/số liệu tóm tắt) + empty state nếu có bảng. |
| `comparison_dashboard.html` | Empty "Không có dữ liệu chi tiết" (JS) → **empty-state + CTA**. |
| `quote_table_input.html` | Sticky thead; nếu có empty → thêm **empty-state + CTA**. |
| `user_management.html` | Sticky header; empty (nếu có) → **empty-state + CTA**. |
| `report_detail_page.html` | Trang chi tiết báo cáo; có thể thêm **strip ngữ cảnh** (STT, ngày) và empty thống nhất nếu có. |
| `ar_aging_detail_single.html` | Empty "Không tìm thấy chi tiết công nợ" → **empty-state + icon + CTA** (Quay lại AR / Portal). |
| `nhansu_nhaplieu.html` | Có `.empty-state`; có thể thêm **icon + CTA** rõ ràng. |
| `ceo_cockpit.html` | Có `chart-empty-state`; empty "Không có dữ liệu chi tiết" trong bảng → **CTA** (Về Portal đã có trong header). |
| `realtime_dashboard.html` | Empty nhiều chỗ; có thể thêm **nút Về Portal** trong từng empty. |

---

### 1.3. Trang đặc thù / ít chỉnh (vẫn nên kiểm tra)

| Template | Ghi chú |
|----------|--------|
| `login.html` | Trang đăng nhập, không dùng layout dashboard → chỉ cần kiểm tra theme (CSS vars), không bắt buộc hero/empty. |
| `change_password.html` | Form đổi mật khẩu → kiểm tra dùng `var(--*)`, không cần hero. |
| `user_profile.html` | Hồ sơ cá nhân, nhiều hardcoded color (42 chỗ) → **ưu tiên thay #hex/rgb bằng var(--*)**. |
| `portal_dashboard.html` | Dashboard portal, nhiều hardcode (17) → **CSS vars** + empty "Không có báo giá/lịch giao" có thể thêm CTA. |
| `verify_result.html` | Trang kết quả xác minh → kiểm tra empty/CTA nếu có. |
| `print_expense_voucher.html` | In phiếu → chỉ cần in đúng, theme tùy chọn. |
| `chat_assistant.html` | Giao diện chat, 40 hardcoded color → **CSS vars** nếu muốn đồng bộ theme. |
| `training_dashboard_v2.html` | Có `training-empty-cat`; kiểm tra empty + CTA. |
| `training_category_detail.html` | Trang chi tiết danh mục → strip/empty nếu có. |
| `hall_of_fame_create.html` | Form tạo HOF → form chuẩn, vars. |
| `daily_challenge.html` | Trang thử thách → strip/empty nếu có. |
| `kpi_evaluation.html` | Có empty "Không có dữ liệu chi tiết" → **empty-state + CTA**. |
| `kpi_manual_scoring.html` | Empty "Không có nhân sự nào" (JS) → **empty-state class + icon + CTA**. |
| `inventory_control.html` | Kiểm tra filter/table/empty. |
| `sales_backlog.html` | DataTables; empty qua `zeroRecords`/`infoEmpty` → có thể thêm block empty HTML với **icon + CTA** khi không có bản ghi. |

---

### 1.4. File không cần nâng cấp nội dung (base, component, bản sao)

| File | Lý do |
|------|--------|
| `base.html` | Layout gốc. |
| `base - Copy.html` | Bản sao, có thể bỏ hoặc chỉ dùng tham chiếu. |
| `index - Copy.html`, `index_redesign 2.html` | Bản sao. |
| `kpi_evaluation ban đầu.html` | Bản backup. |
| `components/_navbar.html` | Component. |
| `components/_flash_messages.html` | Component. |
| `components/_chatbot_widget.html` | Component. |
| `partials/task_card.html` | Partial. |
| `partials/_inventory_lazy_items.html` | Partial. |
| `quote_approval v2.html` | Bản v2, nếu còn dùng thì áp dụng tương tự `quote_approval.html`. |
| `delivery_card.html` | Thẻ/conponent nhỏ. |

---

## 2. Các điểm cải thiện chung

### 2.1. Empty state thống nhất

- **Đã có:** icon + text + nút CTA (Về Portal / Về Dashboard / Quay lại) ở: ar_aging, ar_aging_detail, budget_ytd_report, budget_payment_queue, audit_dashboard, sales_details, kpi_peer_review (welcome), …
- **Chưa đủ:** nhiều trang chỉ `text-center text-muted py-5` hoặc `py-4` không icon, không nút.
- **Đề xuất:** với mọi bảng/danh sách không có dữ liệu:
  - Dùng class kiểu `empty-state-*` (padding, text màu `var(--secondary)`).
  - Icon (vd: `fa-inbox`) kích thước ~2.5rem, opacity ~0.35.
  - Đoạn mô tả ngắn.
  - Nút CTA: `btn btn-outline-primary btn-sm rounded-pill` (Về Portal / trang trước / Dashboard tương ứng).

### 2.2. Hero / context strip

- Trang đã có: sales_dashboard, ar_aging, ar_aging_detail, budget_ytd_report, budget_payment_queue, audit_dashboard, sales_details, index_redesign, customer_profile, course_detail, realtime_dashboard, …
- Trang nên bổ sung strip ngắn (1 dòng tóm tắt ngữ cảnh): **dashboard.html** (số báo cáo / bộ lọc), **quote_approval** (số báo giá theo funnel), **profit_dashboard** (khoảng ngày + 1–2 số KPI), **ap_aging** (tổng nợ / nợ quá hạn), **delivery_dashboard** (tuần / trạng thái), **cross_sell_dashboard**, **budget_dashboard**, **budget_approval**.

### 2.3. Command bar / filter một dòng

- Đã gọn: ar_aging, ar_aging_detail, audit_dashboard, budget_payment_queue, sales_lookup_dashboard, sales_order_approval.
- Có thể gom lại 1 dòng (flex + wrap): **quote_approval** (Từ/Đến + Mức độ + Tìm + Lọc), **dashboard.html** (nếu nhiều ô filter), **profit_dashboard** (đã gọn, có thể đặt trong strip).

### 2.4. Màu hardcoded (#hex, rgb/rgba)

- Nên thay bằng `var(--primary)`, `var(--danger)`, `var(--success)`, `var(--warning)`, `var(--secondary)`, `var(--text-dark)`, `var(--input-bg)`, `var(--card-bg)`, `var(--border-color)` để đồng bộ theme (light/dark/fantasy/adorable).
- Số file còn nhiều hardcode (theo grep): **user_profile.html** (42), **report_detail_page.html** (29), **study_room.html** (24), **portal_dashboard.html** (17), **kpi_manual_scoring.html** (15), **customer_profile.html** (12), **ap_aging.html** (13), **inventory_aging.html** (13), **login.html** (12), **customer_profile** (12), **ar_aging.html** (9), **profit_dashboard** (gradient KPI), …
- **sales_lookup_dashboard.html**: `.lookup-empty-state` đang dùng `#fefce8`, `#facc15` → nên đổi sang `var(--input-bg)`, `var(--warning)` (hoặc màu vàng theme).
- **customer_profile.html**: `.hero-sales-low` đang `#ea580c` → có thể dùng `var(--warning)` hoặc màu cam trong theme.
- **profit_dashboard.html**: KPI cards dùng gradient `#4318FF`, `#FFB547`, `#05CD99`, `#E31A1A` → có thể giữ gradient nhưng đổi sang `var(--primary)`, `var(--warning)`, `var(--success)`, `var(--danger)`.

### 2.5. Sticky thead

- Đã có: sales_details, ar_aging_detail, audit_dashboard, budget_payment_queue, budget_ytd_report, ar_aging, customer_profile, sales_dashboard, sales_order_approval, dashboard, quote_approval, profit_dashboard, ap_aging, inventory_aging, customer_replenishment, total_replenishment, quote_table_input, user_management, ceo_cockpit.
- **sales_backlog.html**: dùng DataTables, thead chưa sticky → có thể thêm `position: sticky; top: 0; z-index: 10; background: var(--input-bg)` cho `table.dataTable thead th`.

### 2.6. Modal drill-down

- Nên có: breadcrumb ngữ cảnh (vd: "Tên trang → Chi tiết"), skeleton/spinner khi load, đóng bằng Esc (Bootstrap mặc định).
- Đã làm: budget_ytd_report (breadcrumb), audit_dashboard (breadcrumb), sales_order_approval (breadcrumb-dhb).
- **quote_approval.html** modal chi tiết: có thể thêm **breadcrumb** (vd: "Phê duyệt báo giá → Chi tiết [số]").

---

## 3. Ưu tiên đề xuất

| Mức | Việc | Trang ưu tiên |
|-----|------|----------------|
| **Cao** | Empty state: thêm icon + CTA (Về Portal / trước) | quote_approval, sales_order_approval, budget_approval, ap_aging, profit_dashboard, ar_aging_detail_single, dashboard (empty báo cáo) |
| **Cao** | Thay màu hardcode bằng CSS vars (theme) | user_profile, portal_dashboard, sales_lookup_dashboard (empty), customer_profile (hero-sales-low), profit_dashboard (KPI gradient) |
| **Trung bình** | Thêm hero strip 1 dòng | dashboard, quote_approval, profit_dashboard, ap_aging, delivery_dashboard, budget_dashboard, budget_approval, cross_sell_dashboard |
| **Trung bình** | Command bar gọn 1 dòng (nếu đang 2 dòng) | quote_approval, dashboard (nếu nhiều filter) |
| **Thấp** | Modal breadcrumb / skeleton | quote_approval modal |
| **Thấp** | Sticky thead cho DataTables | sales_backlog |
| **Thấp** | Dọn file: xóa hoặc gộp bản Copy/backup | base - Copy, index - Copy, index_redesign 2, kpi_evaluation ban đầu |

---

## 4. Tổng hợp số lượng

- **Templates (có extends base):** ~50 (không tính component/partial/bản sao).
- **Đã nâng cấp đủ pattern:** ~15 trang.
- **Có base blocks, cần bổ sung hero/empty/CTA/vars:** ~25 trang.
- **Trang đặc thù / ít chỉnh:** ~10.
- **File bỏ qua (base, component, copy):** ~12.

Nếu triển khai theo đúng báo cáo này, toàn bộ HTML frontend sẽ đồng bộ: strip ngữ cảnh, filter gọn, empty state có hướng dẫn và CTA, bảng dễ đọc (sticky header), và theme thống nhất qua CSS variables.
