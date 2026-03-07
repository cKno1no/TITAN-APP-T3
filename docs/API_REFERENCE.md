# API Reference – TITAN APP T3

Tài liệu danh sách endpoint theo blueprint, dùng cho gọi API đúng, test/tích hợp và bảo trì. Ứng dụng dùng session (cookie); phần lớn API yêu cầu đăng nhập (và có thể phân quyền theo role).

**Base URL (ví dụ):** `http://localhost:5000`

---

## App (app.py) – Login, logout, đổi mật khẩu

| Method | Path | Mô tả |
|--------|------|--------|
| GET, POST | `/login` | Trang đăng nhập / xử lý login |
| GET | `/logout` | Đăng xuất |
| GET, POST | `/change_password` | Đổi mật khẩu |
| GET | `/` | Trang chủ (redirect sau login) |

---

## Approval (approval_bp) – Duyệt chào giá, đơn hàng bán

| Method | Path | Mô tả |
|--------|------|--------|
| GET, POST | `/quote_approval` | Duyệt chào giá |
| GET, POST | `/sales_order_approval` | Duyệt đơn hàng bán |
| GET | `/quick_approval` | Duyệt nhanh |
| POST | `/api/approve_quote` | API duyệt chào giá |
| POST | `/api/approve_order` | API duyệt đơn hàng |
| GET | `/api/get_quote_details/<path:quote_id>` | Chi tiết chào giá |
| GET | `/api/get_quote_cost_details/<path:quote_id>` | Chi tiết cost chào giá |
| GET | `/api/get_order_details/<string:sorder_id>` | Chi tiết đơn hàng |
| POST | `/api/quote/update_salesman` | Cập nhật salesman chào giá |
| POST | `/api/save_quote_cost_override` | Lưu override cost chào giá |
| GET, POST | `/quote_input_table` | Bảng nhập chào giá |
| POST | `/api/update_quote_status` | Cập nhật trạng thái chào giá |

---

## PO Approval (po_approval_bp) – Duyệt đơn mua (PO/DPO)

| Method | Path | Mô tả |
|--------|------|--------|
| GET | `/api/po/pending` | Danh sách PO chờ duyệt |
| GET, POST | `/po_approval` | Trang duyệt PO |
| GET | `/api/po/check_result/<string:porder_id>` | Kết quả kiểm tra PO |
| POST | `/api/po/approve` | Duyệt PO |
| GET | `/api/po/detail/<porder_id>` | Chi tiết PO |
| GET | `/api/po/risk_debug/<string:porder_id>` | Debug rủi ro PO |

---

## User (user_bp) – Quản lý user, phân quyền, profile, gamification

| Method | Path | Mô tả |
|--------|------|--------|
| GET | `/user_management` | Trang quản lý user |
| GET | `/api/users/list` | Danh sách user |
| GET | `/api/users/detail/<string:user_code>` | Chi tiết user |
| POST | `/api/users/update` | Cập nhật user |
| GET | `/api/permissions/matrix` | Ma trận quyền |
| POST | `/api/permissions/save` | Lưu quyền |
| POST | `/api/user/set_theme` | Đặt theme (sáng/tối) |
| GET | `/api/pet/status` | Trạng thái pet (gamification) |
| GET | `/profile` | Trang profile |
| POST | `/api/user/buy_item` | Mua item (shop) |
| POST | `/api/user/equip_item` | Trang bị item |
| POST | `/api/user/upload_avatar` | Upload avatar |
| POST | `/api/user/change_password` | Đổi mật khẩu (API) |
| GET | `/api/mailbox` | Hộp thư (gamification) |
| POST | `/api/mailbox/claim` | Nhận thưởng từ mailbox |
| POST | `/api/user/use_rename_card` | Dùng thẻ đổi tên |
| GET | `/admin/audit_logs` | Trang audit log (admin) |
| GET | `/api/admin/logs/stream` | Stream audit log |

---

## Budget (budget_bp) – Ngân sách, duyệt chi, thanh toán

| Method | Path | Mô tả |
|--------|------|--------|
| GET | `/budget/dashboard` | Dashboard ngân sách |
| GET | `/budget/approval` | Duyệt yêu cầu ngân sách |
| GET | `/api/budget/objects/<string:search_term>` | Tìm đối tượng ngân sách |
| POST | `/api/budget/check_balance` | Kiểm tra số dư |
| POST | `/api/budget/submit_request` | Gửi yêu cầu chi |
| POST | `/api/budget/approve` | Duyệt yêu cầu |
| GET | `/budget/print/<string:request_id>` | In phiếu yêu cầu |
| GET | `/budget/payment` | Trang thanh toán |
| POST | `/api/budget/pay` | Thực hiện thanh toán |
| GET | `/verify/request/<string:request_id>` | Xác minh yêu cầu (vd: link email) |
| GET | `/budget/report/ytd` | Báo cáo YTD |
| GET | `/api/budget/group_details` | Chi tiết nhóm ngân sách |

---

## Task (task_bp) – Công việc, tiến độ, duyệt

| Method | Path | Mô tả |
|--------|------|--------|
| GET, POST | `/task_dashboard` | Dashboard task |
| POST | `/api/task/log_progress` | Ghi nhận tiến độ |
| GET | `/api/task/history/<int:task_id>` | Lịch sử task |
| POST | `/api/task/add_feedback` | Thêm phản hồi |
| POST | `/api/task/toggle_priority/<int:task_id>` | Bật/tắt ưu tiên |
| GET | `/api/get_eligible_helpers` | Danh sách người hỗ trợ hợp lệ |
| GET | `/api/task/recent_updates` | Cập nhật gần đây |
| POST | `/api/task/approve` | Duyệt task |

---

## KPI (kpi_bp) – Báo cáo bán hàng, tồn kho, công nợ

| Method | Path | Mô tả |
|--------|------|--------|
| GET, POST | `/sales_dashboard` | Dashboard bán hàng |
| GET | `/sales_detail/<string:employee_id>` | Chi tiết bán theo nhân viên |
| GET, POST | `/realtime_dashboard` | Dashboard realtime |
| GET, POST | `/inventory_aging` | Tồn kho theo tuổi |
| GET | `/api/inventory/group_detail/<string:group_id>` | Chi tiết nhóm tồn |
| GET, POST | `/ar_aging` | Công nợ phải thu (aging) |
| GET, POST | `/ar_aging_detail` | Chi tiết AR aging |
| GET | `/ar_aging_detail_single` | Chi tiết AR đơn lẻ |
| GET, POST | `/sales/profit_analysis` | Phân tích lợi nhuận |

---

## KPI Evaluation (kpi_evaluation_bp) – Đánh giá KPI, chấm tay, peer review

| Method | Path | Mô tả |
|--------|------|--------|
| GET | `/dashboard` | Dashboard đánh giá (context: evaluation) |
| POST | `/api/evaluate` | Gửi đánh giá (AI/tự động) |
| GET | `/manual-scoring` | Trang chấm điểm tay |
| POST | `/api/save-manual-scores` | Lưu điểm chấm tay |
| GET | `/peer-review` | Trang peer review |
| GET | `/api/get-users-by-dept` | User theo phòng ban |
| POST | `/api/submit-peer-review` | Gửi peer review |
| GET | `/api/kpi-detail` | Chi tiết KPI (query params) |

---

## Executive (executive_bp) – CEO Cockpit, so sánh, drill-down

| Method | Path | Mô tả |
|--------|------|--------|
| GET | `/ceo_cockpit` | Trang CEO Cockpit |
| GET | `/api/executive/dashboard_data` | Dữ liệu dashboard executive |
| GET | `/analysis/comparison` | Trang so sánh |
| GET | `/api/executive/drilldown` | Drill-down (query params) |

---

## CRM (crm_bp) – Dashboard CRM, nhập liệu, backlog, tồn kho

| Method | Path | Mô tả |
|--------|------|--------|
| GET, POST | `/dashboard` | Dashboard CRM |
| GET | `/report_detail_page/<string:report_stt>` | Trang chi tiết báo cáo |
| GET, POST | `/nhaplieu` | Nhập liệu |
| GET, POST | `/nhansu_nhaplieu` | Nhập liệu nhân sự |
| GET | `/api/khachhang/ref/<string:ma_doi_tuong>` | Tham chiếu khách hàng |
| GET | `/api/nhansu_ddl_by_khachhang/<string:ma_doi_tuong>` | Dropdown nhân sự theo khách hàng |
| GET | `/api/defaults/<string:loai_code>` | Giá trị mặc định theo loại |
| GET | `/api/nhansu/list/<string:ma_doi_tuong>` | Danh sách nhân sự |
| GET | `/api/nhansu_by_khachhang/<string:ma_doi_tuong>` | Nhân sự theo khách hàng |
| GET, POST | `/sales/backlog` | Backlog bán hàng |
| GET | `/inventory_control` | Trang kiểm soát tồn kho |
| GET | `/api/inventory_control/data` | Dữ liệu kiểm soát tồn kho |

---

## Training (training_bp) – Đào tạo, thư viện, quiz, daily challenge

| Method | Path | Mô tả |
|--------|------|--------|
| GET | `/training` | Trang đào tạo |
| GET | `/api/training/dashboard_v2` | Dashboard đào tạo (v2) |
| GET | `/training/course/<int:course_id>` | Chi tiết khóa học |
| GET | `/training/study-room/<int:material_id>` | Phòng học tài liệu |
| POST | `/api/library/chat` | Chat với tài liệu (RAG) |
| POST | `/api/training/progress` | Cập nhật tiến độ học |
| POST | `/api/quiz/get` | Lấy câu hỏi quiz |
| POST | `/api/quiz/submit` | Nộp bài quiz |
| GET | `/training/daily-challenge` | Trang Daily Challenge |
| GET | `/api/challenge/status` | Trạng thái challenge |
| GET | `/api/training/daily_challenge/history` | Lịch sử daily challenge |
| POST | `/api/challenge/submit` | Nộp câu trả lời challenge |
| GET | `/api/training/search` | Tìm kiếm tài liệu |
| GET | `/training/category/<path:category_name>` | Tài liệu theo danh mục |
| POST | `/api/training/request-teaching` | Yêu cầu giảng dạy |

---

## Chat (chat_bp) – Chatbot, kiểm tra daily challenge

| Method | Path | Mô tả |
|--------|------|--------|
| POST | `/api/chatbot_query` | Gửi câu hỏi chatbot (body: message/session) |
| GET | `/assistant` | Trang trợ lý ảo |
| GET | `/api/check_daily_challenge` | Kiểm tra trạng thái daily challenge |

---

## Portal (portal_bp) – Portal chính, Hall of Fame

| Method | Path | Mô tả |
|--------|------|--------|
| GET | `/portal` | Trang portal |
| GET | `/portal/refresh` | Refresh dữ liệu portal |
| GET, POST | `/hall-of-fame/share` | Chia sẻ Hall of Fame |

---

## Lookup (lookup_bp) – Tra cứu bán hàng, replenishment

| Method | Path | Mô tả |
|--------|------|--------|
| GET, POST | `/sales_lookup` | Tra cứu bán hàng |
| GET | `/total_replenishment` | Tổng replenishment |
| GET | `/export_total_replenishment` | Export tổng replenishment |
| GET | `/customer_replenishment` | Replenishment theo khách |
| GET | `/api/khachhang/<string:ten_tat>` | Tra cứu khách hàng |
| POST | `/api/multi_lookup` | Tra cứu đa điều kiện |
| GET | `/api/get_order_detail_drilldown/<path:voucher_no>` | Chi tiết đơn drill-down |
| GET | `/api/backorder_details/<string:inventory_id>` | Chi tiết backorder |
| GET | `/api/replenishment_details/<path:group_code>` | Chi tiết replenishment theo nhóm |
| GET | `/api/customer_replenishment/<string:customer_id>` | Replenishment theo khách (API) |

---

## Delivery (delivery_bp) – Giao vận

| Method | Path | Mô tả |
|--------|------|--------|
| GET | `/delivery_dashboard` | Dashboard giao vận |
| POST | `/api/delivery/set_day` | Đặt ngày xem |
| POST | `/api/delivery/set_status` | Cập nhật trạng thái giao |
| GET | `/api/delivery/get_items/<string:voucher_id>` | Chi tiết items phiếu giao |

---

## Customer 360 (customer_analysis_bp)

| Method | Path | Mô tả |
|--------|------|--------|
| GET | `/customer_360/<string:object_id>` | Trang Customer 360 |
| GET | `/api/customer_360/charts/<string:object_id>` | Dữ liệu chart Customer 360 |
| POST | `/api/customer_360/drilldown` | Drill-down Customer 360 |

---

## Commission (commission_bp) – Hoa hồng

| Method | Path | Mô tả |
|--------|------|--------|
| GET | `/commission/request` | Trang yêu cầu hoa hồng |
| POST | `/api/commission/create` | Tạo yêu cầu hoa hồng |
| POST | `/api/commission/toggle_item` | Bật/tắt item |
| POST | `/api/commission/add_contact` | Thêm liên hệ |
| POST | `/api/commission/submit` | Gửi yêu cầu hoa hồng |

---

## AP (ap_bp) – Công nợ phải trả (Aging)

| Method | Path | Mô tả |
|--------|------|--------|
| GET, POST | `/ap_aging` | Trang AP aging |
| GET | `/api/ap_detail/<string:vendor_id>` | Chi tiết theo nhà cung cấp |

---

## Cross-sell (cross_sell_bp)

| Method | Path | Mô tả |
|--------|------|--------|
| GET | `/cross_sell_dashboard` | Dashboard cross-sell |
| GET | `/api/cross_sell/detail/<string:client_id>` | Chi tiết cross-sell theo client |

---

## Factory (factory.py) – Static / file

| Method | Path | Mô tả |
|--------|------|--------|
| GET | `/attachments/<path:filename>` | Tải file đính kèm (trong thư mục cấu hình) |

---

## Ghi chú chung

- **Xác thực:** Hầu hết route yêu cầu đăng nhập (session). Một số route kiểm tra thêm quyền (vd: admin, manager).
- **Body/Query:** Các API POST thường nhận JSON; một số GET có query (filter, date, page). Chi tiết request/response từng endpoint có thể bổ sung dần hoặc xuất từ OpenAPI/Swagger nếu sau này thêm.
- **Prefix blueprint:** URL có thể có prefix (vd: một số blueprint đăng ký với `url_prefix`); danh sách trên đã ghi path đầy đủ như trong code (không lặp prefix ở đây để tránh nhầm).

*Cập nhật theo code tại thư mục `blueprints/` và `app.py`. Khi thêm/sửa route nên cập nhật lại file này.*
