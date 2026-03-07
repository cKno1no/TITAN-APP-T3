# Báo cáo rà soát Services – Titan OS

*Bỏ qua vấn đề bảo mật (xử lý riêng). Tập trung: xung đột tiềm ẩn, cấu trúc/hiệu năng, logic cần nâng cấp, ý tưởng đột phá theo module.*

---

## 1. Lỗi xung đột tiềm ẩn

### 1.1. SQL sai cú pháp khi có `division` (user_service)

**File:** `services/user_service.py` – `get_all_users(division=None)`

- Query gốc kết thúc bằng `ORDER BY SHORTNAME`. Khi có `division`, code nối `" AND [Division] = ?"` **sau** `ORDER BY` → câu SQL thành `WHERE ... ORDER BY SHORTNAME AND [Division] = ? ORDER BY USERCODE` (sai cú pháp).
- **Cách xử lý:** Đưa điều kiện `division` vào mệnh đề WHERE, chỉ giữ một `ORDER BY` ở cuối (ví dụ `ORDER BY SHORTNAME` hoặc `ORDER BY USERCODE`).

### 1.2. Hai instance GamificationService

- **ChatbotService** tạo `self.gamification = GamificationService(db_manager)` trong `__init__`.
- **Factory** còn đăng ký `app.gamification_service = GamificationService(db_manager)`.
- Blueprint dùng `current_app.chatbot_service.gamification.log_activity(...)` (kpi_evaluation_bp) thay vì `current_app.gamification_service` → hai instance, dữ liệu XP/activity có thể không thống nhất nếu logic ghi khác nhau.
- **Đề xuất:** Dùng thống nhất `current_app.gamification_service` (inject vào ChatbotService từ factory nếu cần), tránh tạo GamificationService bên trong ChatbotService.

### 1.3. `current_app.task_service` trong TrainingService

- **File:** `services/training_service.py` – `request_teaching()` gọi `current_app.task_service.create_new_task(...)`.
- TrainingService không nhận `task_service` qua constructor → phụ thuộc ngầm vào app context và thứ tự khởi tạo.
- **Rủi ro:** Khi test hoặc gọi ngoài request (ví dụ scheduler), `current_app` có thể chưa có hoặc `task_service` chưa gắn → lỗi runtime.
- **Đề xuất:** Inject `task_service` vào constructor của TrainingService (từ factory) và dùng `self.task_service` thay vì `current_app.task_service`.

### 1.4. `execute_sp_multi` khi `params=None`

- **File:** `db_manager.py` – `execute_sp_multi(self, sp_name, params=None)`.
- Dòng `param_placeholders = ', '.join(['?' for _ in params]) if params else ''` sẽ lỗi nếu `params=()` (tuple rỗng), vì `if params` là False nhưng một số SP có thể được gọi với `params=()`.
- **Đề xuất:** Xử lý rõ: `if params is not None and len(params) > 0` để hỗ trợ cả `params=()` và `params=None`.

### 1.5. Portal_service dùng raw connection nhưng đôi chỗ thiếu `finally: conn.close()`

- **File:** `services/portal_service.py` – dùng `get_transaction_connection()`; ở cuối có `conn.close()` nhưng nếu giữa đường ném exception, một số nhánh có thể không đóng connection.
- **Đề xuất:** Bọc toàn bộ block dùng `conn` trong `try/finally` và gọi `conn.close()` trong `finally` (hoặc dùng context manager nếu DBManager hỗ trợ).

---

## 2. Cấu trúc code & hiệu năng yếu

### 2.1. Bare `except:` / `except: pass`

- Nhiều file dùng `except:` hoặc `except: pass` → nuốt mọi exception (kể cả KeyboardInterrupt, SystemExit), khó debug.
- **Vị trí điển hình:**  
  `training_service.py` (332, 545), `user_service.py` (198, 205), `user_bp.py` (106, 203), `budget_bp.py` (416), `task_service.py` (390, 412), `task_bp.py` (125), `chatbot_service.py` (91, 225, 239, 375, 525), `portal_service.py` (21), `commission_service.py` (123, 186), `library_service.py` (61), `delivery_service.py` (353), `sales_lookup_service.py` (172), `customer_analysis_service.py` (104, 135, 143), `executive_service.py` (388), `quotation_approval_service.py` (23), `budget_service.py` (522), `chatbot_ui_helper.py` (61), `db_manager.py` (106), `app.py` (86, 100, 111).
- **Đề xuất:** Chỉ bắt `Exception` (ví dụ `except Exception as e:`), log `e` và xử lý hoặc re-raise nếu cần; tránh bare `except`.

### 2.2. `get_data` trả về `[]` khi lỗi (db_manager)

- **File:** `db_manager.py` – `get_data()` khi exception trả về `[]`.
- Caller không phân biệt được “không có bản ghi” và “lỗi DB” → dễ đưa ra trạng thái sai (ví dụ coi như “empty” trong khi thực tế lỗi).
- **Đề xuất:** Re-raise sau khi log, hoặc trả về structure có dạng `(data, error)` / raise custom exception để tầng trên xử lý đúng.

### 2.3. N+1 / vòng lặp gọi DB

- **crm_service.get_dashboard_data:** Đã gom WHERE và một lần query; ổn.
- **task_service:** `_enrich_tasks_with_client_name` / `_enrich_tasks_with_user_info` dùng 1 query theo list ID → ổn.
- **kpi_service.evaluate_monthly_kpi:** Vòng lặp profile, mỗi tiêu chí có thể gọi `get_actual_value_for_criteria` (không gọi DB) và `cursor.execute(insert_query, ...)` trong một transaction → chấp nhận được; cần đảm bảo transaction đóng đúng (đã có commit/rollback/close).
- **user_service.update_user_permissions:** Xóa rồi insert từng permission trong vòng lặp → nhiều round-trip. Có thể dùng `executemany` hoặc một lần DELETE + nhiều INSERT trong một transaction.

### 2.4. Duplicate logic / copy-paste

- **delivery_service.get_planning_board_data:** Hai dòng gán giống nhau:  
  `row['VoucherDate_str'] = self._format_date_safe(voucher_date_obj)` và `row['EarliestRequestDate_str'] = ...` lặp hai lần (khoảng 147–150) → xóa bản trùng.
- **kpi_service.get_kpi_results_for_view:** Docstring lặp hai lần giống nhau → giữ một dòng.

### 2.5. Import / dependency

- **crm_service.get_so_inventory_control:** `import pandas as pd` bên trong hàm → nên đưa lên đầu file.
- **training_service._check_ai_rate_limit:** `from flask import session` trong hàm → có thể đưa lên đầu (session đã dùng ở nhiều chỗ).

### 2.6. Ghi log bằng `print` trong production

- **training_service.process_pending_grading:** Dùng `print(...)` cho trạng thái chấm bài. Trong production nên dùng `current_app.logger.info(...)` hoặc logger của service để dễ tắt/bật và gom log.

---

## 3. Logic cần nâng cấp / cải tiến

### 3.1. Training

- **search_knowledge:** TOP 50 + scoring trong Python; với kho câu hỏi lớn nên cân nhắc full-text search (SQL Server Full-Text) hoặc giới hạn điều kiện (ví dụ TOP 20) và tối ưu lại điều kiện LIKE.
- **distribute_daily_questions:** Shuffle user rồi chunk theo số câu hỏi; nếu số user không chia đều cho 3 câu, nhóm cuối có thể ít người hơn. Có thể làm rõ trong comment hoặc chuẩn hóa (ví dụ luôn 3 câu nhưng gán đều user hơn).
- **get_current_challenge_status:** Hai block SQL `sql_latest` giống hệt trong try/except → chỉ cần một query; except chỉ để fallback khi thiếu cột (ví dụ EarnedXP). Có thể tách “fallback schema” rõ ràng thay vì duplicate query.
- **request_teaching:** CourseID trong log/request đang dùng `material_id` (MaterialID) → tên biến và comment nên thống nhất (MaterialID vs CourseID) để tránh nhầm sau này.

### 3.2. KPI

- **evaluate_monthly_kpi:** Transaction dùng `get_transaction_connection()` + cursor; sau khi commit đợt 1 lại gọi `_calculate_and_update_final_peer_score` (bên trong dùng `get_data`/`execute_non_query` riêng). Nếu muốn “chốt KPI” hoàn toàn nguyên tử, có thể đưa toàn bộ (kể cả peer score) vào cùng một connection/transaction.
- **get_actual_value_for_criteria:** Nhiều nhánh `if criteria_id == ...`; khi thêm tiêu chí mới dễ sót. Có thể chuyển sang dict/cấu hình (criteria_id → field hoặc hàm con) để dễ mở rộng.
- **_calculate_and_update_final_peer_score:** Khi `not reviews` thì `return` (None). Caller `fetch_all_actuals` dùng `safe_float(...)` nên không lỗi; nên chủ động trả về `0.0` hoặc document rõ “returns None when no reviews” để người đọc không bối rối.

### 3.3. CRM / Dashboard

- **get_dashboard_data:** Đếm tổng và metrics (today_count, distinct_customers) bằng hai query riêng với cùng WHERE. Có thể gộp một query dùng COUNT và COUNT(DISTINCT ...) / SUM(CASE...) để giảm round-trip (nếu DB hỗ trợ).
- **create_report:** Sau INSERT không lấy STT bằng SCOPE_IDENTITY()/OUTPUT mà query lại theo NGUOI + NGAY; trong môi trường concurent có thể lấy nhầm bản ghi khác. Nên dùng OUTPUT INSERTED.STT hoặc SCOPE_IDENTITY() ngay trong INSERT.

### 3.4. Budget

- **create_expense_request:** Gửi email sau khi lưu DB; nếu gửi mail lỗi, phiếu vẫn đã tạo. Có thể ghi log lỗi gửi mail và (tùy nghiệp vụ) đánh dấu “chưa gửi thông báo” để retry.
- **get_budget_status / check_budget_for_approval:** Nhiều query nhỏ (master → plan → actual). Có thể gộp trong một SP hoặc một query (CTE/subquery) để giảm số lần gọi DB.

### 3.5. AR/AP Aging

- **get_ar_aging_summary:** `params = [current_year]` rồi `query_params` riêng; `final_params = [current_year] + query_params` → ổn nhưng dễ nhầm vì có hai biến tham số. Comment rõ “năm cho JOIN” và “tham số WHERE” để người sửa sau không đảo thứ tự.
- **get_ar_aging_details_by_voucher:** Lọc theo `customer_name` trong Python sau khi gọi SP. Nếu SP hỗ trợ tham số tìm kiếm tên, nên đẩy xuống SP để tận dụng index và giảm dữ liệu trả về.

### 3.6. Delivery

- **get_planning_board_data:** Query lấy “7 ngày gần nhất” bằng chuỗi ngày trong SQL; nên dùng tham số (?) thay vì f-string để tránh lỗi locale và SQL injection (dù đã bỏ qua bảo mật, vẫn nên chuẩn hóa).
- **_get_planned_date_info:** Map ngày trong tuần cố định (Thứ 2–7); nếu sau này có “tuần lẻ/chẵn” hoặc ngày lễ, cần mở rộng.

### 3.7. Sales / Quotation

- **quotation_approval_service.safe_numeric:** Logic “chia 100000 nếu giá trị rất lớn và chia hết cho 100000” là heuristic, dễ sai với số khác. Nên xác định rõ nguồn dữ liệu (đã nhân 100k chưa) và chuẩn hóa ở tầng lấy dữ liệu.
- **sales_service.get_sales_performance_data:** Gọi SP rồi gọi thêm get_sales_backlog; hai nguồn. Đảm bảo backlog và SP dùng cùng định nghĩa “kỳ” và “salesman” để số liệu đồng bộ.

### 3.8. User

- **get_all_users:** Ngoài lỗi SQL khi có division (mục 1.1), khi không có division vẫn có hai ORDER BY (SHORTNAME rồi USERCODE). Nên chọn một thứ tự sắp xếp chuẩn (ví dụ ORDER BY SHORTNAME hoặc USERCODE) và bỏ bớt.

### 3.9. Task

- **_enrich_tasks_with_client_name:** Build `object_ids_str` bằng nối chuỗi `'id1','id2'` từ set; nếu object_ids rỗng đã xử lý. Cần đảm bảo không có ký tự đặc biệt trong ObjectID (hoặc escape) để tránh lỗi cú pháp SQL; parameterized IN (nhiều ?) an toàn hơn nếu driver hỗ trợ.

---

## 4. Ý tưởng đột phá / tạo ấn tượng theo module

### 4.1. training_service (Đào tạo & Daily Challenge)

- **Gợi ý:** “Thử thách tuần” / “Bảng xếp hạng Daily”: mỗi tuần tổng hợp điểm/XP theo user, trả về top 5 + phần thưởng ảo (badge, title) qua gamification; hiển thị trên portal hoặc email tuần.
- **AI Tutor:** Cho phép “hỏi theo trang” (chỉ gửi nội dung trang hiện tại lên AI) để giảm token và câu trả lời sát ngữ cảnh hơn.
- **Study room:** Thống kê “thời gian đọc trung bình” và “trang dừng nhiều nhất” để đề xuất “bài khó” hoặc tóm tắt ngắn cho từng material.

### 4.2. crm_service (Báo cáo & Nhân sự liên hệ)

- **Gợi ý:** “Báo cáo nhanh tuần”: một API/trang tóm tắt số báo cáo theo NV, số KH xuất hiện, số file đính kèm trong tuần → một card dashboard “Tuần này CRM”.
- **Autocomplete KH:** Cache (Redis/in-memory) danh sách ShortObjectName/ObjectID cho ô tìm kiếm, refresh định kỳ hoặc khi có cập nhật danh mục.
- **Liên hệ:** Gợi ý “người liên hệ thường gặp” theo ObjectID khi mở form báo cáo (dựa trên lịch sử báo cáo gần đây).

### 4.3. kpi_service (KPI & Đánh giá chéo)

- **Gợi ý:** “KPI dự báo tháng”: từ vài tháng gần nhất, tính xu hướng (linear/trung bình) và hiển thị “dự kiến đạt X% chỉ tiêu” cho tháng hiện tại.
- **Drill-down:** Export chi tiết KPI (get_criteria_detail) ra Excel/CSV từ nút trên modal.
- **Đánh giá chéo:** Cho phép “gửi lời mời nhắc đánh giá” (notification/mail) cho người chưa chấm trong tháng; đếm % đã chấm và hiển thị trên màn hình đánh giá.

### 4.4. user_service (User & Gamification)

- **Gợi ý:** “Cột mốc Level”: khi user lên level mới, ghi event và hiển thị toast/modal chúc mừng + mở khóa theme/pet mới (nếu có cấu hình).
- **Profile:** Cho phép “so sánh với đồng nghiệp” (ẩn danh): so Level/XP trong cùng bộ phận (chỉ hiển thị bậc xếp hạng, không tên) để tăng tương tác.
- **Shop:** “Deal ngày” / “Vật phẩm giới hạn theo mùa” (ItemCode theo tháng) để tăng lượt vào trang Shop.

### 4.5. budget_service (Ngân sách & Chi tiêu)

- **Gợi ý:** “Dự báo hết hạn mức”: từ tốc độ chi YTD, ước tính tháng nào nhóm nào sẽ chạm trần; cảnh báo sớm trên dashboard.
- **Phiếu đề nghị:** Trạng thái “Đang chờ người duyệt X” + countdown (ví dụ “Còn 2 ngày làm việc”) dựa trên ngày tạo và SLA nội quy.
- **Báo cáo YTD:** Cho phép “so sánh năm nay vs năm ngoái” (cùng kỳ) ngay trên một view để thấy xu hướng.

### 4.6. ar_aging_service / ap_aging_service (Công nợ)

- **Gợi ý:** “Khách nợ cần gọi hôm nay”: mỗi sáng trích top N khách theo số tiền quá hạn hoặc ngày quá hạn; gửi danh sách ngắn qua mail/notification cho NVKD/Kế toán.
- **AR:** “Dự báo thu” đơn giản: tổng nợ trong hạn + ước tính % thu được theo lịch sử → số tiền có thể thu trong tháng.
- **AP:** Cảnh báo “khoản sắp đến hạn” (7 ngày tới) để chuẩn bị thanh toán.

### 4.7. delivery_service (Giao vận)

- **Gợi ý:** “Bản đồ ngày giao”: nhóm đơn theo khu vực/ tỉnh thành (nếu có địa chỉ); hiển thị dạng bản đồ tĩnh hoặc danh sách nhóm theo vùng để tối ưu tuyến.
- **Trạng thái thực tế:** Cho phép cập nhật “Đã giao” từ app/mobile (một form đơn giản) để ActualDeliveryDate và trạng thái cập nhật ngay.
- **Thống kê:** “Tuần giao đúng hạn %” theo NV/ theo KH → KPI nhỏ cho giao vận.

### 4.8. sales_service / sales_lookup_service (Bán hàng & Tra cứu)

- **Gợi ý:** “Gợi ý đặt hàng”: từ lịch sử mua và tồn kho (nếu có), gợi ý “Khách X thường mua vào tháng này” hoặc “Mặt hàng Y sắp hết”.
- **Lookup:** Lưu lịch sử tìm kiếm (session/user) và hiển thị “Tìm gần đây” để giảm nhập lại.
- **Sales performance:** “So sánh với tháng trước” (%, tăng/giảm) ngay trên card KPI.

### 4.9. task_service (Đầu việc)

- **Gợi ý:** “Nhiệm vụ ưu tiên hôm nay”: thuật toán đơn giản (due date, % hoàn thành, loại) để gợi ý 3–5 task nên làm trước.
- **Nhắc nhở:** Notification/email khi task sắp đến hạn (1 ngày) hoặc khi có “cần hỗ trợ” mới.
- **Báo cáo:** “Số task hoàn thành trong tuần” theo user/ theo nhóm → bảng tóm tắt cho sếp.

### 4.10. portal_service (Portal & CEO Cockpit)

- **Gợi ý:** “Một trang tổng quan CEO”: KPI tài chính, KPI bán hàng, KPI kho, cảnh báo công nợ, tin tức nội bộ trong một layout dashboard; có thể dùng iframe hoặc API gom từ nhiều service.
- **Cá nhân hóa:** User chọn “widget” hiển thị trên portal (báo cáo của tôi, task của tôi, công nợ của tôi) và lưu cấu hình.
- **Thông báo nổi bật:** Một strip “Tin quan trọng” (từ bảng tin hoặc mail hệ thống) ngay dưới header.

### 4.11. chatbot_service (Chatbot & AI)

- **Gợi ý:** “Kỹ năng mới theo role”: kỹ năng “Tra cứu ngân sách còn lại” cho Kế toán, “Xem đơn hàng chờ giao” cho Sale; cấu hình tool theo role.
- **RAG:** Lưu lịch sử hội thoại theo session và tóm tắt ngắn cuối phiên (“Hôm nay bạn đã hỏi: …”) để gửi mail hoặc hiển thị lần sau.
- **Điểm danh bằng giọng nói / ảnh:** (Dài hạn) Cho phép “check-in” bằng một câu thoại hoặc ảnh selfie để ghi nhận tham gia Daily Challenge / training.

### 4.12. commission_service / quotation_approval_service / sales_order_approval_service

- **Gợi ý:** “Luồng duyệt thống nhất”: một màn “Tổng đơn chờ tôi duyệt” (báo giá + đơn bán + ngân sách) với filter theo loại và ngày; một nút “Duyệt nhanh” mở từng loại.
- **Báo giá:** “Mẫu báo giá thường dùng” (template) theo nhóm KH hoặc nhóm hàng để tạo nhanh.
- **Đơn bán:** Sau khi duyệt, gửi thông báo cho người tạo đơn “Đơn #XXX đã được duyệt” (mail/notification).

### 4.13. customer_analysis_service (Phân tích khách hàng)

- **Gợi ý:** “Khách hàng có nguy cơ rời bỏ”: điểm rủi ro đơn giản (giảm doanh số, tăng nợ quá hạn, ít tương tác) và danh sách “Cần chăm sóc” để Sale ưu tiên.
- **360 view:** Export PDF/Word một trang tóm tắt KH (DS, nợ, lịch sử báo cáo, task liên quan) để in hoặc gửi.

### 4.14. executive_service (CEO / Cockpit)

- **Gợi ý:** “Cảnh báo bất thường”: so sánh số liệu hiện tại với trung bình 3 tháng; nếu lệch quá ngưỡng (ví dụ ±20%) thì highlight và ghi lý do gợi ý (ví dụ “Doanh số tháng cao do đơn lớn KH X”).
- **Trend sparkline:** Mỗi KPI không chỉ số tuyệt đối mà có đồ thị nhỏ (sparkline) 6–12 tháng để xem xu hướng nhanh.

### 4.15. gamification_service

- **Gợi ý:** “Sự kiện theo mùa”: nhân dịp Tết/30-4, nhân đôi XP hoặc thêm badge đặc biệt khi hoàn thành task/ báo cáo/ đánh giá chéo trong khoảng thời gian.
- **Bảng xếp hạng công khai:** Top XP theo tháng (ẩn danh hoặc hiển thị tên) trong từng bộ phận để tạo động lực.

---

## 5. Tóm tắt ưu tiên

| Ưu tiên | Hạng mục | Hành động |
|--------|----------|-----------|
| Cao | Lỗi SQL user_service.get_all_users | Sửa WHERE/ORDER BY khi có division. |
| Cao | Gamification hai instance | Dùng thống nhất app.gamification_service; inject vào ChatbotService. |
| Cao | TrainingService gọi current_app.task_service | Inject task_service qua constructor. |
| Trung bình | Bare except | Thay bằng except Exception, log rõ. |
| Trung bình | get_data trả về [] khi lỗi | Log + re-raise hoặc (data, error). |
| Trung bình | Duplicate code (delivery, kpi) | Xóa dòng trùng, gom docstring. |
| Thấp | CRM create_report lấy STT | Dùng OUTPUT INSERTED / SCOPE_IDENTITY. |
| Thấp | Portal_service connection | Đảm bảo finally close connection. |

Phần “ý tưởng đột phá” có thể triển khai từng bước theo thứ tự ưu tiên nghiệp vụ và nguồn lực (backend + frontend).
