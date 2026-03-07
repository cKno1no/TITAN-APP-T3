# Runbook – Vận hành & Xử lý sự cố TITAN APP T3

Tài liệu quy trình vận hành: backup DB, restart ứng dụng, cron/scheduler, kiểm tra health. Giúp xử lý sự cố và vận hành ổn định khi tăng user.

---

## 1. Backup cơ sở dữ liệu (SQL Server)

- **Mục đích:** Phục hồi khi lỗi dữ liệu hoặc sau sự cố.
- **Tần suất gợi ý:** Hàng ngày (full), có thể thêm differential/transaction log theo chính sách IT.
- **Công cụ:** SQL Server Management Studio, `sqlcmd`, hoặc script backup của DBA.
- **Lưu ý:**
  - Database chính: tên trong biến `DB_NAME` (vd: CRM_STDD).
  - Backup nên lưu ra ổ khác với ổ chứa app; giữ retention theo quy định (vd: 7–30 ngày).
- **Ví dụ (SSMS):** Chuột phải database → Tasks → Back Up… → Full, chọn destination.

*Chi tiết lệnh cụ thể (path, tên file, retention) nên do DBA/IT quy định và cập nhật vào runbook nội bộ.*

---

## 2. Restart ứng dụng

- **Khi nào:** Sau khi cập nhật code/config, khi app treo hoặc bộ nhớ cao, theo lịch bảo trì.
- **Cách thực hiện:**

  1. **Dừng process hiện tại**
     - Trên Windows: Task Manager → tìm process `python` chạy `server.py` (hoặc `python.exe` tương ứng) → End task.
     - Hoặc dùng CMD/PowerShell tại thư mục app:  
       `taskkill /F /IM python.exe` (cẩn thận nếu nhiều app Python chạy cùng lúc — nên kill theo PID).
  2. **Vào thư mục dự án**
     - `cd "E:\...\TITAN APP T3"` (đường dẫn thực tế trên server).
  3. **Kích hoạt môi trường ảo (nếu dùng)**
     - `.venv\Scripts\activate`
  4. **Chạy lại production**
     - `python server.py`
   - Ứng dụng lắng nghe **http://0.0.0.0:5000** (Waitress, 12 threads).

- **Lưu ý:** Trên máy production, sau khi restart, APScheduler sẽ tự chạy lại và lên lịch các job (chỉ khi `socket.gethostname() == PROD_SERVER_NAME` trong `server.py`).

---

## 3. Cron / Scheduler (APScheduler trong server.py)

Các job chạy **chỉ khi** tên máy khớp `PROD_SERVER_NAME` trong `server.py`; trên máy dev cron **tắt** để tránh gửi trùng.

| Job | Giờ chạy (cron) | Mô tả |
|-----|------------------|--------|
| **Daily Challenge** (phân phối câu hỏi) | 08:30, 13:30, 16:45 | Gọi `chatbot_service.training_service.distribute_daily_questions()`; in log số user nhận câu hỏi. |
| **AI Grading** (chấm điểm Daily Challenge) | 09:30, 15:44, 17:45 | Gọi `training_service.process_pending_grading()`. |
| **Gamification** (tổng kết điểm/ quà hàng ngày) | 20:00 | Gọi `gamification_service.process_daily_rewards()`. |

- **Log:** Log file ghi trong thư mục `logs/`, tên dạng `titan_server_YYYYMMDD.log`.
- **Sự cố:** Nếu job lỗi, xem log hoặc console; đảm bảo Redis và DB đang chạy, `GEMINI_API_KEY` hợp lệ (cho grading).

---

## 4. Health check

- **Hiện trạng:** Ứng dụng **chưa có** endpoint `/health` hoặc `/ping` chuyên dụng.
- **Cách kiểm tra nhanh:** Mở trình duyệt hoặc `curl` đến trang đăng nhập:
  - `http://<host>:5000/login`  
  Nếu trả về HTML trang login (200) thì app đang phản hồi.
- **Gợi ý sau:** Nên bổ sung endpoint GET `/health` hoặc `/ping` trả về 200 + JSON `{"status":"ok"}` để load balancer hoặc monitoring gọi.

---

## 5. Kiểm tra nhanh khi sự cố

| Triệu chứng | Hướng xử lý |
|-------------|-------------|
| App không mở được (500 / không kết nối) | Kiểm tra: (1) process `server.py` còn chạy không, (2) Redis có chạy không, (3) SQL Server và chuỗi kết nối (DB_SERVER, DB_NAME, DB_UID, DB_PWD), (4) log trong `logs/`. |
| Đăng nhập lỗi / session mất nhanh | Kiểm tra Redis (REDIS_HOST, REDIS_PORT); APP_SECRET_KEY không đổi giữa các lần restart. |
| Chatbot / Daily Challenge không hoạt động | Kiểm tra GEMINI_API_KEY; xem log job Daily Challenge / Grading. |
| Upload file lỗi | Kiểm tra thư mục `attachments` (hoặc UPLOAD_FOLDER_PATH) có tồn tại và quyền ghi. |

---

*Cập nhật lần cuối theo cấu trúc app và `server.py` hiện tại. Khi thay đổi cron hoặc thêm job, cần cập nhật lại bảng trong mục 3.*
