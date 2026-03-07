# TITAN APP T3

Ứng dụng nội bộ **Titan OS**: Portal, CRM/Báo cáo, Duyệt (Chào giá, Đơn hàng bán, PO/DPO, Ngân sách), KPI/CEO Cockpit, Giao vận, Task, Đào tạo/Daily Challenge, Chatbot AI, Gamification, Quản lý user & phân quyền.

- **Stack:** Flask (Application Factory), SQL Server (SQLAlchemy + pyodbc), Redis (session + cache), Waitress, HTMX, Alpine.js, Bootstrap 5.
- **Python:** 3.10+ (khuyến nghị 3.11+).

---

## 1. Yêu cầu hệ thống

- **Python** 3.10 trở lên  
- **SQL Server** (hoặc tương thích) với database CRM_STDD và các SP đã deploy  
- **Redis** (cho session và cache)  
- **ODBC Driver 17 for SQL Server** (hoặc tương thích) đã cài trên máy  

---

## 2. Cài đặt

### 2.1 Clone và vào thư mục dự án

```bash
cd "TITAN APP T3"
```

### 2.2 Tạo môi trường ảo (khuyến nghị)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate      # Linux/macOS
```

### 2.3 Cài dependency

```bash
pip install -r requirements.txt
```

### 2.4 Biến môi trường

- Copy file mẫu:  
  `copy .env.example .env` (Windows) hoặc `cp .env.example .env` (Linux/macOS).
- Mở `.env` và điền giá trị thực (không commit `.env` lên git).

**Biến bắt buộc:**

| Biến | Mô tả |
|------|--------|
| `APP_SECRET_KEY` | Secret key Flask (tối thiểu 32 ký tự, random). |
| `DB_SERVER` | Địa chỉ SQL Server. |
| `DB_NAME` | Tên database (vd: CRM_STDD). |
| `DB_UID` | User kết nối DB. |
| `DB_PWD` | Mật khẩu DB. |
| `REDIS_HOST` | Host Redis (mặc định localhost). |
| `REDIS_PORT` | Port Redis (mặc định 6379). |
| `GEMINI_API_KEY` | API key Google Gemini (cho Chatbot / Daily Challenge). |

**Lưu ý:** Ứng dụng sẽ **không chạy** nếu thiếu `APP_SECRET_KEY` (config ném lỗi khi import).

---

## 3. Chạy ứng dụng

### 3.1 Chế độ development (Flask built-in)

```bash
set FLASK_APP=app.py
flask run
```

- Mặc định: http://127.0.0.1:5000  
- Có thể đổi port: `flask run --port 5050`

### 3.2 Chế độ production (Waitress + scheduler)

```bash
python server.py
```

- Server lắng nghe **http://0.0.0.0:5000** (threads=12).  
- Trên **máy production** (tên máy khớp `PROD_SERVER_NAME` trong `server.py`): APScheduler chạy các job Daily Challenge, chấm điểm AI, Gamification.  
- Trên máy dev (tên máy khác): cronjob **tắt** để tránh gửi trùng.

---

## 4. Cấu trúc thư mục (tóm tắt)

```
TITAN APP T3/
├── app.py              # Entry point, login/logout, global middleware
├── factory.py          # Application factory, đăng ký blueprints & services
├── server.py           # Production: Waitress + APScheduler
├── config.py           # Cấu hình (đọc từ os.getenv / .env)
├── db_manager.py      # Lớp DB (get_data, execute_non_query, execute_sp_multi)
├── utils.py            # login_required, permission_required, get_user_ip, ...
├── requirements.txt
├── .env.example
├── blueprints/         # Các blueprint (approval, kpi, portal, training, ...)
├── services/           # Logic nghiệp vụ (kpi_service, training_service, ...)
├── templates/         # Jinja2 templates
├── static/             # CSS, JS, assets
├── database/           # Stored procedures (procedures/)
└── docs/               # Tài liệu (README, RUNBOOK, API_REFERENCE, ...)
```

---

## 5. Tài liệu bổ sung

- **Biến môi trường chi tiết:** Xem `config.py` và `.env.example`.
- **Vận hành & sự cố:** `docs/RUNBOOK.md`.
- **Danh sách API:** `docs/API_REFERENCE.md`.
