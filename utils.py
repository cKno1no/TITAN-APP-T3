# utils.py
from flask import session, redirect, url_for, flash, request, current_app, jsonify, g  # <--- Đã thêm 'g' vào đây
from functools import wraps
import config
import os
from datetime import datetime
from werkzeug.utils import secure_filename
import magic 

# --- [BỔ SUNG HÀM NÀY] ---
def get_db_value(row, key_name):
    """Lấy giá trị từ dict row không phân biệt hoa thường"""
    if not row: return None
    if key_name in row: return row[key_name]
    for k, v in row.items():
        if k.upper() == key_name.upper():
            return v
    return None

# [FIX] Đã thêm hàm này để khắc phục lỗi 'get_user_ip not found'
def get_user_ip():
    """Lấy IP người dùng, hỗ trợ cả trường hợp qua Proxy/Load Balancer"""
    if request.headers.getlist("X-Forwarded-For"):
       return request.headers.getlist("X-Forwarded-For")[0]
    else:
       return request.remote_addr

# --- Decorator Login ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login', next=request.url))
            
        user_code = session.get('user_code')
        security_hash = session.get('security_hash')
        
        if user_code and security_hash:
            try:
                db = current_app.db_manager
                # Sử dụng tham số binding để tránh SQL Injection
                query = f"SELECT [PASSWORD] FROM {config.TEN_BANG_NGUOI_DUNG} WHERE USERCODE = ?"
                data = db.get_data(query, (user_code,))
                
                if not data or data[0]['PASSWORD'] != security_hash:
                    session.clear()
                    flash("Phiên đăng nhập hết hạn.", "warning")
                    return redirect(url_for('login'))
            except Exception:
                pass 
                
        return f(*args, **kwargs)
    return decorated_function

# --- Hàm Helper Xử lý Chuỗi ---
def truncate_content(text, max_lines=5):
    if not text: return ""
    lines = text.split('\n')
    if len(lines) <= max_lines: return text 
    return '\n'.join(lines[:max_lines]) + '...'

# --- Hàm Helper Xử lý File ---
# [Bổ sung vào import của utils.py]


def allowed_file(file_storage):
    """
    Kiểm tra file kép: 
    1. Kiểm tra đuôi file (nhanh)
    2. Kiểm tra nội dung thực tế (Magic Numbers)
    """
    filename = file_storage.filename
    # 1. Kiểm tra đuôi file như cũ để lọc nhanh
    is_ext_allowed = '.' in filename and \
                     filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS
    
    if not is_ext_allowed:
        return False

    # 2. Kiểm tra Magic Numbers (Nội dung thực sự)
    try:
        # Đọc 2048 bytes đầu tiên để nhận diện định dạng
        header = file_storage.read(2048)
        file_storage.seek(0) # Quan trọng: Reset con trỏ file về đầu để Flask lưu được file sau này
        
        mime = magic.from_buffer(header, mime=True)
        
        # Danh sách MimeType an toàn tương ứng với ALLOWED_EXTENSIONS
        # Sếp có thể bổ sung thêm vào config.py
        safe_mimes = [
            'application/pdf', 
            'image/jpeg', 
            'image/png', 
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', # excel mới (.xlsx)
            'application/vnd.ms-excel', # excel cũ (.xls)
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document', # word mới (.docx)
            'application/msword', # word cũ (.doc)
            'text/plain', 
            'text/csv',
        ]
        
        return mime in safe_mimes
    except Exception as e:
        current_app.logger.error(f"Lỗi kiểm tra Magic Number: {e}")
        return False

# Hàm save_uploaded_files sẽ tự động được hưởng lợi vì nó gọi allowed_file

def save_uploaded_files(files):
    """Xử lý lưu các file và trả về chuỗi tên file ngăn cách bởi dấu chấm phẩy."""
    saved_filenames = []
    
    # 1. Lấy đường dẫn chuẩn từ cấu hình hệ thống
    upload_folder = current_app.config.get('UPLOAD_FOLDER')
    if not upload_folder:
        return ""
        
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
        
    now_str = datetime.now().strftime("%Y%m%d%H%M%S")

    for file in files:
        # Bỏ qua nếu người dùng không chọn file (Form gửi lên object rỗng)
        if not file or not file.filename:
            continue
            
        # 2. Kiểm tra Magic Numbers và định dạng
        if allowed_file(file):
            filename_clean = secure_filename(file.filename)
            unique_filename = f"{now_str}_{filename_clean}"
            try:
                # Lưu file thành công
                file.save(os.path.join(upload_folder, unique_filename))
                saved_filenames.append(unique_filename)
            except Exception as e:
                current_app.logger.error(f"Lỗi hệ thống khi lưu file {filename_clean}: {e}")
                # [MỚI] Báo lỗi nếu server không thể ghi file (VD: đầy ổ cứng)
                flash(f"Lỗi hệ thống khi ghi file '{file.filename}' vào đĩa.", "danger")
        else:
            # [MỚI] TỪ CHỐI VÀ BÁO CÁO NGAY RA MÀN HÌNH
            flash(f"⚠️ BẢO MẬT: File '{file.filename}' bị từ chối! Định dạng thực tế không hợp lệ hoặc chứa nội dung không an toàn.", "warning")
                
    # Nối mảng thành chuỗi cách nhau bởi dấu chấm phẩy
    return ';'.join(saved_filenames)

def permission_required(feature_code):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 1. Check Login cơ bản
            if not session.get('logged_in'):
                return redirect(url_for('login'))
            
            # 2. Xác định Role hiện tại một cách chắc chắn nhất
            user = getattr(g, 'user', None)
            user_role = None

            # Cách 1: Lấy từ g.user (Object)
            if user and hasattr(user, 'role'):
                user_role = user.role
            
            # Cách 2: Lấy từ g.user (Dict - nếu DB trả về dict)
            elif user and isinstance(user, dict):
                # Thử tìm các tên cột phổ biến
                user_role = get_db_value(user, 'ROLE') or \
                            get_db_value(user, 'USERROLE') or \
                            get_db_value(user, 'GROUPID')

            # Cách 3: Fallback lấy từ Session (Lưới an toàn cuối cùng)
            if not user_role:
                user_role = session.get('user_role')

            # 3. Chuẩn hóa Role để so sánh (Tránh lỗi Admin vs ADMIN)
            # Chuyển hết về chữ in hoa và xóa khoảng trắng thừa
            current_role_str = str(user_role).strip().upper() if user_role else ''
            admin_role_str = str(config.ROLE_ADMIN).strip().upper()

            # --- DEBUG LOG (Giúp bạn nhìn thấy server đang hiểu role là gì) ---
            # print(f"DEBUG AUTH: User={session.get('user_code')} | Role Found={user_role} | Normalized={current_role_str} vs Admin={admin_role_str}")
            # ----------------------------------------------------------------

            # 4. QUYỀN TỐI CAO: Nếu là ADMIN -> Luôn cho qua
            if current_role_str == admin_role_str:
                return f(*args, **kwargs)

            # 5. Check quyền chi tiết (Nếu không phải Admin)
            has_permission = False
            
            # Ưu tiên dùng hàm .can() của object User
            if user and hasattr(user, 'can'):
                has_permission = user.can(feature_code)
            else:
                # Fallback về session list
                perms = session.get('permissions', [])
                # Đảm bảo permissions là list
                if isinstance(perms, str): 
                    perms = [perms] 
                has_permission = feature_code in perms

            # 6. Xử lý khi KHÔNG có quyền
            if not has_permission:
                msg = f"Bạn không có quyền truy cập chức năng này ({feature_code})."
                
                # Nếu là gọi API (như biểu đồ CEO Cockpit) -> Trả JSON lỗi
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'success': False, 'message': msg}), 403
                
                # Nếu là trang thường -> Flash lỗi và đẩy về trang trước
                flash(msg, "danger")
                return redirect(request.referrer or url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def record_activity(activity_code):
    """
    Decorator để tự động ghi điểm XP khi thực hiện hành động thành công.
    Chỉ ghi nhận khi Request là POST (thao tác dữ liệu) và không có lỗi xảy ra.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 1. Chạy hàm gốc (VD: Tạo báo cáo, Lưu đơn hàng...)
            response = f(*args, **kwargs)
            
            # 2. Sau khi chạy xong, kiểm tra nếu là POST và thành công (không lỗi)
            # (Thường các hàm POST thành công sẽ trả về Redirect 302 hoặc JSON 200)
            if request.method == 'POST':
                try:
                    # Lấy user hiện tại
                    user_code = session.get('user_code')
                    if user_code:
                        # Gọi Service ghi log (Lazy import để tránh vòng lặp)
                        from flask import current_app
                        if hasattr(current_app, 'gamification_service'):
                            current_app.gamification_service.log_activity(user_code, activity_code)
                except Exception as e:
                    # Nếu lỗi ghi điểm thì bỏ qua, không làm crash app chính
                    print(f"⚠️ Gamification Error: {e}")
            
            return response
        return decorated_function
    return decorator