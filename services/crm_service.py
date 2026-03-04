# services/crm_service.py

import config
from datetime import datetime, timedelta
from utils import truncate_content

class CRMService:
    def __init__(self, db_manager):
        self.db = db_manager

    # ==========================================
    # 1. DASHBOARD BÁO CÁO
    # ==========================================
    def get_dashboard_data(self, filters, page, per_page, current_user_role, current_user_code, user_ip):
        users_query = f"""
            SELECT [USERCODE], [USERNAME], [SHORTNAME] 
            FROM {config.TEN_BANG_NGUOI_DUNG} 
            WHERE [PHONG BAN] IS NOT NULL AND [PHONG BAN] NOT LIKE '9. DU HOC%'
            ORDER BY [SHORTNAME] 
        """ 
        users_data = self.db.get_data(users_query)

        where_conditions = []
        where_params = [] 
        
        # 1. Lọc Ngày
        where_conditions.append(f"T1.NGAY BETWEEN ? AND ?")
        where_params.extend([filters['date_from'], filters['date_to']])

        # 2. Lọc theo User (Phân quyền: Non-Admin không thấy báo cáo của Admin)
        if current_user_role != config.ROLE_ADMIN:
            query_admin = f"SELECT [USERCODE] FROM {config.TEN_BANG_NGUOI_DUNG} WHERE UPPER(RTRIM([ROLE])) = ?"
            admin_data = self.db.get_data(query_admin, (config.ROLE_ADMIN,))
            if admin_data:
                admin_codes = [u['USERCODE'] for u in admin_data if u['USERCODE']]
                if admin_codes:
                    admin_codes_str = ", ".join(f"'{code}'" for code in admin_codes)
                    where_conditions.append(f"T1.NGUOI NOT IN ({admin_codes_str})")

        # 3. Các bộ lọc khác
        if filters['selected_user']:
            where_conditions.append(f"T1.NGUOI = ?")
            where_params.append(filters['selected_user'])
            
        if filters['kh_search']:
            where_conditions.append(f"(T3.ShortObjectName LIKE ? OR T3.ObjectName LIKE ?)")
            where_params.extend([f"%{filters['kh_search']}%", f"%{filters['kh_search']}%"])
            
        if filters['text_search']:
            terms = [t.strip() for t in filters['text_search'].split(';') if t.strip()]
            if terms:
                or_conditions = []
                for term in terms:
                    or_conditions.append(f"(T1.[NOI DUNG 2] LIKE ? OR T1.[DANH GIA 2] LIKE ?)")
                    where_params.extend([f'%{term}%', f'%{term}%'])
                where_conditions.append("(" + " OR ".join(or_conditions) + ")")

        where_clause = " AND ".join(where_conditions)
        offset = (page - 1) * per_page
        
        # 4. Đếm tổng
        count_query = f"""
            SELECT COUNT(T1.STT) AS Total
            FROM {config.TEN_BANG_BAO_CAO} AS T1
            LEFT JOIN {config.TEN_BANG_NGUOI_DUNG} AS T2 ON T1.NGUOI = T2.USERCODE
            LEFT JOIN {config.ERP_IT1202} AS T3 ON T1.[KHACH HANG] = T3.ObjectID 
            WHERE {where_clause}
        """
        total_count_data = self.db.get_data(count_query, tuple(where_params))
        total_reports = total_count_data[0]['Total'] if total_count_data and total_count_data[0].get('Total') is not None else 0
        total_pages = (total_reports + per_page - 1) // per_page if total_reports > 0 else 1

        # 5. Lấy dữ liệu phân trang
        report_query = f"""
            SELECT 
                T1.STT AS ID_KEY, T1.NGAY, T2.SHORTNAME AS NV, 
                ISNULL(T3.ShortObjectName, T3.ObjectName) AS KH, 
                T1.[NOI DUNG 2] AS [NOI DUNG 1], T1.[DANH GIA 2] AS [DANH GIA 1],
                T1.ATTACHMENTS
            FROM {config.TEN_BANG_BAO_CAO} AS T1
            LEFT JOIN {config.TEN_BANG_NGUOI_DUNG} AS T2 ON T1.NGUOI = T2.USERCODE
            LEFT JOIN {config.ERP_IT1202} AS T3 ON T1.[KHACH HANG] = T3.ObjectID
            WHERE {where_clause}
            ORDER BY T1.STT DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """
        report_params = tuple(where_params) + (offset, per_page)
        report_data = self.db.get_data(report_query, report_params)
        
        if report_data:
            for row in report_data:
                row['NOI DUNG 1'] = truncate_content(row.get('NOI DUNG 1', ''))
                row['DANH GIA 1'] = truncate_content(row.get('DANH GIA 1', ''))
                atts = row.get('ATTACHMENTS')
                row['FILE_COUNT'] = len([f for f in atts.split(';') if f.strip()]) if atts else 0
                row['ID_KEY'] = str(row['ID_KEY'])
        
        # 6. Ghi log
        details = f"Xem Dashboard: User={filters['selected_user']}, KH={filters['kh_search']}, Page={page}"
        self.db.write_audit_log(current_user_code, 'VIEW_REPORT_DASHBOARD', 'INFO', details, user_ip)

        return users_data, report_data or [], total_reports, total_pages

    # ==========================================
    # 2. CHI TIẾT BÁO CÁO
    # ==========================================
    def get_report_detail(self, report_stt, current_user_role, current_user_code, user_ip):
        # Check quyền
        if current_user_role != config.ROLE_ADMIN:
            query_auth = f"""
                SELECT T1.NGUOI AS NguoiBaoCao, T2.[CAP TREN] AS CapTrenBaoCao
                FROM {config.TEN_BANG_BAO_CAO} AS T1
                LEFT JOIN {config.TEN_BANG_NGUOI_DUNG} AS T2 ON T1.NGUOI = T2.USERCODE
                WHERE T1.STT = ?
            """
            auth_data = self.db.get_data(query_auth, (report_stt,))
            if not auth_data:
                return False, "Lỗi truy vấn dữ liệu."
            
            owner = auth_data[0]['NguoiBaoCao'].strip().upper()
            supervisor = auth_data[0]['CapTrenBaoCao'].strip().upper()
            user_clean = current_user_code.strip().upper()

            if user_clean not in [owner, supervisor]:
                return False, "Bạn không có quyền xem báo cáo này."

        # Lấy chi tiết
        query = f"""
            SELECT TOP 1
                T1.STT, T1.NGAY, T1.LOAI, T1.[KHACH HANG] AS KH_Ma,
                T1.[NOI DUNG 1], T1.[NOI DUNG 2], T1.[NOI DUNG 3], T1.[NOI DUNG 4], T1.[NOI DUNG 5],
                T1.[DANH GIA 1], T1.[DANH GIA 2], T1.[DANH GIA 3], T1.[DANH GIA 4], T1.[DANH GIA 5],
                T1.ATTACHMENTS, T4.[DIEN GIAI] AS Loai_DienGiai,
                T2.USERNAME AS NV_Fullname, T3.[TEN DOI TUONG] AS KH_FullName
            FROM {config.TEN_BANG_BAO_CAO} AS T1
            LEFT JOIN {config.TEN_BANG_NGUOI_DUNG} AS T2 ON T1.NGUOI = T2.USERCODE
            LEFT JOIN {config.TEN_BANG_KHACH_HANG} AS T3 ON T1.[KHACH HANG] = T3.[MA DOI TUONG]
            LEFT JOIN {config.TEN_BANG_LOAI_BAO_CAO} AS T4 ON T1.LOAI = T4.LOAI
            WHERE T1.STT = ?
        """
        data = self.db.get_data(query, (report_stt,))
        if not data:
            return False, "Không tìm thấy báo cáo."

        report = data[0]
        atts_str = report.get('ATTACHMENTS')
        report['ATTACHMENT_LIST'] = [f for f in atts_str.split(';') if f.strip()] if atts_str else []
        
        self.db.write_audit_log(current_user_code, 'VIEW_REPORT_DETAIL', 'INFO', f"Xem chi tiết STT: {report_stt}", user_ip)
        return True, report

    # ==========================================
    # 3. TẠO BÁO CÁO MỚI
    # ==========================================
    def get_dropdowns_for_nhap_lieu(self):
        users = self.db.get_data(f"SELECT [USERCODE], [USERNAME], [SHORTNAME] FROM {config.TEN_BANG_NGUOI_DUNG} WHERE [PHONG BAN] IS NOT NULL AND [PHONG BAN] NOT LIKE '9. DU HOC%' ORDER BY [SHORTNAME]")
        loai = self.db.get_data(f"SELECT LOAI, [DIEN GIAI] FROM {config.TEN_BANG_LOAI_BAO_CAO} WHERE NHOM = 1 ORDER BY LOAI")
        return users, loai

    def create_report(self, form_data, attachments_str, current_user_code, user_ip):
        ngay = form_data.get('ngay_bao_cao') or datetime.now().strftime('%Y-%m-%d')
        loai = form_data.get('loai')
        nguoi = form_data.get('nv_bao_cao') or current_user_code
        khach_hang = form_data.get('ma_doi_tuong_kh')

        insert_query = f"""
            INSERT INTO {config.TEN_BANG_BAO_CAO} (
                NGAY, LOAI, NGUOI, [NGUOI LAM], 
                [NOI DUNG 1], [NOI DUNG 2], [NOI DUNG 3], [NOI DUNG 4], [NOI DUNG 5],
                [DANH GIA 1], [DANH GIA 2], [DANH GIA 3], [DANH GIA 4], [DANH GIA 5],
                [KHACH HANG], [HIEN DIEN TRUOC 1], [HIEN DIEN TRUOC 2], ATTACHMENTS
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            ngay, loai, nguoi, current_user_code,
            form_data.get('noi_dung_1'), form_data.get('noi_dung_2'), form_data.get('noi_dung_3'), form_data.get('noi_dung_4'), form_data.get('noi_dung_5'),
            form_data.get('danh_gia_1'), form_data.get('danh_gia_2'), form_data.get('danh_gia_3'), form_data.get('danh_gia_4'), form_data.get('danh_gia_5'),
            khach_hang, form_data.get('nhansu_hengap_1'), form_data.get('nhansu_hengap_2'), attachments_str
        )
        
        if self.db.execute_non_query(insert_query, params):
            self.db.write_audit_log(nguoi, 'REPORT_CREATE', 'INFO', f"Tạo báo cáo mới (Loại: {loai}, KH: {khach_hang})", user_ip)
            return True, "Lưu thành công!"
        return False, "Lỗi SQL khi lưu dữ liệu."

    # ==========================================
    # 4. NHÂN SỰ LIÊN HỆ (Đã fix lỗi INSERT)
    # ==========================================
    def get_customer_name(self, kh_code):
        res = self.db.get_data(f"SELECT [TEN DOI TUONG] FROM {config.TEN_BANG_KHACH_HANG} WHERE [MA DOI TUONG] = ?", (kh_code,))
        return res[0]['TEN DOI TUONG'] if res else None

    def create_contact(self, form_data, current_user_code, user_ip):
        cong_ty = form_data.get('ma_cong_ty_kh')
        ten_ho = form_data.get('ten_ho', '')
        ten_thuong_goi = form_data.get('ten_thuong_goi', '')
        chuc_vu = form_data.get('chuc_vu', '')
        so_dtdd = form_data.get('so_dtdd_1', '')
        email = form_data.get('dia_chi_email', '')
        que_quan = form_data.get('que_quan_ddl', '')
        ghi_chu = form_data.get('ghi_chu', '')
        gia_dinh = form_data.get('gia_dinh', '')

        if gia_dinh:
            ghi_chu += f" | Đặc điểm: {gia_dinh}"

        if not cong_ty or not ten_thuong_goi or not so_dtdd:
            return False, "Vui lòng nhập đủ thông tin bắt buộc (Công ty, Tên gọi, SĐT)."

        try:
            # 1. Tìm Mã nhân sự lớn nhất
            query_max = f"SELECT MAX([ma]) AS MaxMa FROM dbo.{config.TEN_BANG_NHAN_SU_LH} WHERE [CONG TY] = ?"
            max_data = self.db.get_data(query_max, (cong_ty,))
            
            stt = 1
            if max_data and max_data[0]['MaxMa']:
                max_ma_str = str(max_data[0]['MaxMa']).strip()
                parts = max_ma_str.rsplit('_', 1)
                if len(parts) == 2 and parts[1].isdigit():
                    stt = int(parts[1]) + 1
                else:
                    query_count = f"SELECT COUNT(*) AS Total FROM dbo.{config.TEN_BANG_NHAN_SU_LH} WHERE [CONG TY] = ?"
                    count_data = self.db.get_data(query_count, (cong_ty,))
                    if count_data:
                        stt = count_data[0]['Total'] + 1
            
            # 2. Ráp mã tự động
            ma_nhan_su = f"{cong_ty}_{stt:02d}"
            ngay_tao = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 3. LỆNH INSERT PHẢI CÓ CỘT [ma] Ở ĐẦU TIÊN
            insert_query = f"""
                INSERT INTO dbo.{config.TEN_BANG_NHAN_SU_LH} 
                ([ma], [CONG TY], [TEN HO], [TEN THUONG GOI], [CHUC VU], [SO DTDD 1], [DIA CHI EMAIL], [GHI CHU], [NGUOI TAO], [NGAY TAO])
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            # Phải có đủ 10 biến tương ứng
            params = (
                ma_nhan_su, cong_ty, ten_ho, ten_thuong_goi, chuc_vu, 
                so_dtdd, email, ghi_chu, current_user_code, ngay_tao
            )
            
            if self.db.execute_non_query(insert_query, params):
                self.db.write_audit_log(current_user_code, 'CONTACT_CREATE', 'INFO', f"Thêm NSLH mới: {ma_nhan_su}", user_ip)
                return True, "Thêm nhân sự liên hệ thành công!"
            return False, "Lỗi SQL khi lưu nhân sự."
            
        except Exception as e:
            self.db.logger.error(f"Lỗi tạo Contact: {e}")
            return False, f"Lỗi hệ thống: {e}"

    # ==========================================
    # 5. API AUTOCOMPLETE / THAM CHIẾU
    # ==========================================
    def get_contact_count(self, ma_doi_tuong):
        res = self.db.get_data(f"SELECT COUNT(ID) AS CountNLH FROM dbo.{config.TEN_BANG_NHAN_SU_LH} WHERE [CONG TY] = ?", (ma_doi_tuong,))
        return res[0]['CountNLH'] if res and res[0]['CountNLH'] is not None else 0

    def get_contact_dropdown(self, ma_doi_tuong):
        query = f"SELECT MA, [TEN THUONG GOI], [CHUC VU], [TEN HO] FROM dbo.{config.TEN_BANG_NHAN_SU_LH} WHERE [CONG TY] = ? ORDER BY [TEN HO]"
        return self.db.get_data(query, (ma_doi_tuong,))

    def get_defaults(self, loai_code):
        query = f"SELECT [LOAI], [MAC DINH], [TEN] FROM dbo.{config.TEN_BANG_NOI_DUNG_HD} WHERE [LOAI] LIKE ?"
        return self.db.get_data(query, (f"{loai_code}%",))

    def get_contact_list_basic(self, ma_doi_tuong):
        query = f"""
            SELECT MA AS ShortName, ISNULL([TEN HO], [TEN THUONG GOI]) AS FullName,
                   [CHUC VU] AS Title, [SO DTDD 1] AS Phone, [DIA CHI EMAIL] AS Email, [GHI CHU] AS Note
            FROM dbo.{config.TEN_BANG_NHAN_SU_LH} 
            WHERE [CONG TY] = ? ORDER BY [TEN HO]
        """
        return self.db.get_data(query, (ma_doi_tuong,))

    def get_contact_list_detailed(self, ma_doi_tuong):
        query = f"""
            SELECT MA AS ShortName, ([TEN HO] + ' ' + [TEN THUONG GOI]) AS FullName,
                   [CHUC VU] AS Title, [DIEN THOAI 1] AS Phone, [EMAIL] AS Email, [GHI CHU] AS Note
            FROM dbo.{config.TEN_BANG_NHAN_SU_LH} 
            WHERE [CONG TY] = ? ORDER BY [TEN HO]
        """
        return self.db.get_data(query, (ma_doi_tuong,))

    def get_so_inventory_control(self):
        import pandas as pd  # Import cục bộ thư viện pandas để dùng hàm quét lỗi
        try:
            data = self.db.get_data("EXEC Titan_Get_SO_InventoryControl")
            
            if not data:
                return []
                
            # =========================================================
            # [FIX LỖI CRASH API] LÀM SẠCH DỮ LIỆU TRƯỚC KHI TRẢ VỀ JSON
            # =========================================================
            for row in data:
                for key, value in row.items():
                    # 1. Nếu là rỗng (NaT của ngày tháng, hoặc NaN của số liệu) -> Đổi thành None
                    if pd.isna(value):
                        row[key] = None
                    # 2. Nếu là ngày tháng hợp lệ (Timestamp) -> Đổi thành chuỗi String cho an toàn
                    elif type(value).__name__ == 'Timestamp':
                        row[key] = value.strftime('%Y-%m-%d %H:%M:%S')
            # =========================================================

            return data
            
        except Exception as e:
            self.db.logger.error(f"Lỗi chạy SP Titan_Get_SO_InventoryControl: {e}")
            return []