# services/budget_service.py

from flask import current_app
from db_manager import DBManager, safe_float
from datetime import datetime
import config

# [NEW] Import hàm gửi mail từ utils (Cần đảm bảo file utils.py đã có hàm này)
# Nếu chưa có, bạn cần thêm hàm send_notification_email vào utils.py trước
try:
    from utils import send_notification_email
except ImportError:
    # Fallback nếu chưa cấu hình utils để tránh lỗi crash app
    def send_notification_email(*args, **kwargs):
        current_app.logger.info("WARNING: send_notification_email not found in utils.py")

class BudgetService:
    def __init__(self, db_manager: DBManager):
        self.db = db_manager

    def get_budget_status(self, budget_code, department_code, month, year):
        """
        [LOGIC TẠO PHIẾU]: Kiểm tra Ngân sách THÁNG (Month) theo ParentCode.
        Công thức: Còn lại = Plan Tháng - Actual Tháng (ERP).
        """
        # 1. Lấy ParentCode từ BudgetCode được chọn
        query_master = f"SELECT ParentCode, ControlLevel FROM {config.TABLE_BUDGET_MASTER} WHERE BudgetCode = ?"
        master_data = self.db.get_data(query_master, (budget_code,))
        
        if not master_data:
            return {'Remaining': 0, 'Status': 'ERROR', 'Message': 'Mã chi phí không hợp lệ'}
            
        parent_code = master_data[0]['ParentCode']
        control_level = master_data[0]['ControlLevel']
        
        # 2. Tính NGÂN SÁCH THÁNG (Plan) của cả nhóm ParentCode
        query_plan = f"""
            SELECT SUM(P.BudgetAmount) as TotalPlan
            FROM {config.TABLE_BUDGET_PLAN} P
            INNER JOIN {config.TABLE_BUDGET_MASTER} M ON P.BudgetCode = M.BudgetCode
            WHERE M.ParentCode = ? AND P.[Month] = ? AND P.FiscalYear = ?
        """
        plan_data = self.db.get_data(query_plan, (parent_code, month, year))
        month_plan = safe_float(plan_data[0]['TotalPlan']) if plan_data else 0

        # 3. Tính THỰC CHI THÁNG (Actual) từ ERP
        # Logic: Ana03ID trong GT9000 chính là ParentCode
        query_actual = f"""
            SELECT SUM(ConvertedAmount) as TotalActual
            FROM {config.ERP_GIAO_DICH}
            WHERE Ana03ID = ? 
              AND TranMonth = ? AND TranYear = ? 
              AND (DebitAccountID LIKE '64%' OR DebitAccountID LIKE '811%')
        """
        actual_data = self.db.get_data(query_actual, (parent_code, month, year))
        month_actual = safe_float(actual_data[0]['TotalActual']) if actual_data else 0

        # 4. Tính dư ngân sách tháng (Không tính Pending)
        remaining = month_plan - month_actual
        
        return {
            'BudgetCode': budget_code,
            'ParentCode': parent_code,
            'Month_Plan': month_plan,
            'Month_Actual': month_actual,
            'Remaining': remaining,
            'ControlLevel': control_level
        }

    def check_budget_for_approval(self, budget_code, request_amount):
        """
        [LOGIC PHÊ DUYỆT]: Kiểm tra Ngân sách LŨY KẾ (YTD) theo ParentCode.
        So sánh: (Thực chi YTD + Số tiền phiếu này) vs (Ngân sách YTD)
        """
        request_amount = safe_float(request_amount)
        now = datetime.now()
        current_month = now.month
        year = now.year
        
        # 1. Lấy thông tin ParentCode
        query_master = f"SELECT ParentCode, ControlLevel FROM {config.TABLE_BUDGET_MASTER} WHERE BudgetCode = ?"
        master_data = self.db.get_data(query_master, (budget_code,))
        if not master_data:
            return {'status': 'ERROR', 'message': 'Mã lỗi'}
            
        parent_code = master_data[0]['ParentCode']
        control_level = master_data[0]['ControlLevel']
        
        # 2. Tính PLAN LŨY KẾ (YTD Plan)
        # Tổng ngân sách từ tháng 1 đến tháng hiện tại
        query_plan_ytd = f"""
            SELECT SUM(P.BudgetAmount) as TotalPlan
            FROM {config.TABLE_BUDGET_PLAN} P
            INNER JOIN {config.TABLE_BUDGET_MASTER} M ON P.BudgetCode = M.BudgetCode
            WHERE M.ParentCode = ? 
              AND P.FiscalYear = ? 
              AND P.[Month] <= ?
        """
        plan_data = self.db.get_data(query_plan_ytd, (parent_code, year, current_month))
        ytd_plan = safe_float(plan_data[0]['TotalPlan']) if plan_data else 0
        
        # 3. Tính ACTUAL LŨY KẾ (YTD Actual)
        query_actual_ytd = f"""
            SELECT SUM(ConvertedAmount) as TotalActual
            FROM {config.ERP_GIAO_DICH}
            WHERE Ana03ID = ? 
              AND TranYear = ? 
              AND TranMonth <= ?
              AND (DebitAccountID LIKE '64%' OR DebitAccountID LIKE '811%')
        """
        actual_data = self.db.get_data(query_actual_ytd, (parent_code, year, current_month))
        ytd_actual = safe_float(actual_data[0]['TotalActual']) if actual_data else 0
        
        # 4. So sánh
        total_usage_after_approval = ytd_actual + request_amount
        is_over_budget = total_usage_after_approval > ytd_plan
        shortage = total_usage_after_approval - ytd_plan
        
        result = {
            'ParentCode': parent_code,
            'YTD_Plan': ytd_plan,
            'YTD_Actual': ytd_actual,
            'Request_Amount': request_amount,
            'Total_After': total_usage_after_approval,
            'IsWarning': False,
            'Message': 'Trong hạn mức ngân sách lũy kế.',
            'Status': 'PASS'
        }
        
        if is_over_budget:
            msg = f"Nhóm '{parent_code}' vượt ngân sách lũy kế {shortage:,.0f} đ."
            result['IsWarning'] = True
            result['Message'] = msg
            if control_level == 'HARD':
                result['Status'] = 'BLOCK'
            else:
                result['Status'] = 'WARN'
                
        return result

    def create_expense_request(self, user_code, dept_code, budget_code, amount, reason, object_id=None, attachments=None):
        """
        [UPDATED] Tạo đề nghị thanh toán mới (Có đính kèm file + Gửi Email Notification).
        """
        now = datetime.now()
        
        # 1. Lấy thông tin Control Level & Approver
        master_query = f"SELECT ControlLevel, DefaultApprover FROM {config.TABLE_BUDGET_MASTER} WHERE BudgetCode = ?"
        master_data = self.db.get_data(master_query, (budget_code,))
        if not master_data:
            return {'success': False, 'message': 'Mã ngân sách không tồn tại.'}
        
        control_level = master_data[0]['ControlLevel']
        default_approver = master_data[0]['DefaultApprover']

        # 2. Kiểm tra số dư ngân sách THÁNG
        status = self.get_budget_status(budget_code, dept_code, now.month, now.year)
        
        if amount > status['Remaining']:
            if control_level == 'HARD':
                return {'success': False, 'message': f"Bị chặn: Vượt ngân sách tháng ({status['Remaining']:,.0f})."}
            else:
                reason = f"[CẢNH BÁO VƯỢT THÁNG] {reason}"

        # 3. Xác định người duyệt
        approver = default_approver
        if not approver or approver == user_code:
            user_query = f"SELECT [CAP TREN] FROM {config.TEN_BANG_NGUOI_DUNG} WHERE USERCODE = ?"
            user_data = self.db.get_data(user_query, (user_code,))
            parent_approver = user_data[0]['CAP TREN'] if user_data else None
            
            if parent_approver == user_code:
                approver = config.ROLE_ADMIN
            else:
                approver = parent_approver or config.ROLE_ADMIN

        # 4. Lưu vào DB
        req_id = f"REQ-{now.strftime('%y%m')}-{int(datetime.now().timestamp())}"
        
        insert_query = f"""
            INSERT INTO {config.TABLE_EXPENSE_REQUEST} 
            (RequestID, UserCode, DepartmentCode, BudgetCode, Amount, Reason, CurrentApprover, Status, ObjectID, Attachments)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, ?)
        """
        
        success = self.db.execute_non_query(insert_query, (req_id, user_code, dept_code, budget_code, amount, reason, approver, object_id, attachments))

        # 5. [NEW] Gửi Email Thông báo nếu lưu thành công
        if success:
            try:
                # 5.1 Lấy Email của Người duyệt
                email_query = f"SELECT Email, SHORTNAME FROM {config.TEN_BANG_NGUOI_DUNG} WHERE USERCODE = ?"
                approver_data = self.db.get_data(email_query, (approver,))
                
                if approver_data and approver_data[0]['Email']:
                    to_email = approver_data[0]['Email']
                    approver_name = approver_data[0]['SHORTNAME'] or approver
                    
                    # 5.2 Nội dung Email
                    subject = f"[DUYỆT CHI] Đề nghị #{req_id} từ {user_code}"
                    body_html = f"""
                    <div style="font-family: Arial, sans-serif; line-height: 1.6;">
                        <h3 style="color: #4318FF;">Kính gửi anh/chị {approver_name},</h3>
                        <p>Hệ thống vừa nhận được đề nghị thanh toán mới:</p>
                        <table style="border-collapse: collapse; width: 100%; max-width: 600px;">
                            <tr style="background-color: #f8f9fa;">
                                <td style="padding: 10px; border: 1px solid #ddd;"><b>Người đề nghị:</b></td>
                                <td style="padding: 10px; border: 1px solid #ddd;">{user_code}</td>
                            </tr>
                            <tr>
                                <td style="padding: 10px; border: 1px solid #ddd;"><b>Số tiền:</b></td>
                                <td style="padding: 10px; border: 1px solid #ddd; color: #dc3545; font-weight: bold;">{amount:,.0f} VNĐ</td>
                            </tr>
                            <tr style="background-color: #f8f9fa;">
                                <td style="padding: 10px; border: 1px solid #ddd;"><b>Lý do:</b></td>
                                <td style="padding: 10px; border: 1px solid #ddd;">{reason}</td>
                            </tr>
                        </table>
                        <br>
                        <p>Vui lòng truy cập hệ thống để phê duyệt.</p>
                        <hr>
                        <small style="color: gray;">Email tự động từ Titan OS.</small>
                    </div>
                    """
                    
                    # 5.3 Gửi (Chạy ngầm không đợi)
                    send_notification_email(to_email, subject, body_html)
                    current_app.logger.info(f"📧 Notification sent to {to_email}")
            except Exception as e:
                current_app.logger.error(f"⚠️ Failed to send email: {e}")

            return {'success': True, 'message': 'Đã gửi đề nghị thành công.', 'request_id': req_id}
            
        return {'success': False, 'message': 'Lỗi CSDL khi lưu đề nghị.'}

    def get_requests_for_approval(self, approver_code, user_role=''):
        """
        Lấy danh sách phiếu chờ duyệt (kèm thông tin kiểm tra YTD).
        Cột CurrentApproverName được lấy ở đây để hiển thị lên Dashboard.
        """
        query_params = []
        role_check = str(user_role).strip().upper()
        
        # Admin/GM thấy hết, còn lại thấy phiếu của mình duyệt
        if role_check in [config.ROLE_ADMIN, config.ROLE_GM]:
            where_clause = "R.Status = 'PENDING'"
        else:
            where_clause = "R.CurrentApprover = ? AND R.Status = 'PENDING'"
            query_params.append(approver_code)

        query = f"""
            SELECT 
                R.*, 
                M.BudgetName, M.ParentCode,
                U.SHORTNAME as RequesterName,
                U2.SHORTNAME as CurrentApproverName,
                
                -- [MỚI] Lấy thêm Tên đối tượng thụ hưởng
                ISNULL(O.ShortObjectName, O.ObjectName) AS ObjectName
                
            FROM {config.TABLE_EXPENSE_REQUEST} R
            LEFT JOIN {config.TABLE_BUDGET_MASTER} M ON R.BudgetCode = M.BudgetCode
            LEFT JOIN {config.TEN_BANG_NGUOI_DUNG} U ON R.UserCode = U.USERCODE
            LEFT JOIN {config.TEN_BANG_NGUOI_DUNG} U2 ON R.CurrentApprover = U2.USERCODE
            
            -- [MỚI] Join với bảng IT1202 để lấy tên đối tượng
            LEFT JOIN {config.ERP_IT1202} O ON R.ObjectID = O.ObjectID
            
            WHERE {where_clause}
            ORDER BY R.RequestDate DESC
        """
        
        requests = self.db.get_data(query, tuple(query_params))
        
        # Tính toán trạng thái YTD cho từng phiếu (cache theo BudgetCode+Amount để tránh N+1)
        cache = {}
        for req in requests:
            req['Amount'] = safe_float(req.get('Amount'))
            key = (req['BudgetCode'], req['Amount'])
            if key not in cache:
                cache[key] = self.check_budget_for_approval(req['BudgetCode'], req['Amount'])
            check = cache[key]
            req['YTD_Plan'] = check['YTD_Plan']
            req['YTD_Actual'] = check['YTD_Actual']
            req['IsWarning'] = check['IsWarning']
            req['WarningMsg'] = check['Message']
            
        return requests

    def approve_request(self, request_id, approver_code, action, note):
        """Xử lý Duyệt hoặc Từ chối."""
        new_status = 'APPROVED' if action == 'APPROVE' else 'REJECTED'
        query = f"""
            UPDATE {config.TABLE_EXPENSE_REQUEST}
            SET Status = ?, 
                ApprovalDate = GETDATE(), 
                ApprovalNote = ?,
                CurrentApprover = ?
            WHERE RequestID = ? AND Status = 'PENDING'
        """
        return self.db.execute_non_query(query, (new_status, note, approver_code, request_id))

    def get_request_detail_for_print(self, request_id):
        """Lấy chi tiết phiếu để in."""
        query = f"""
            SELECT R.*, M.BudgetName, 
                   U1.SHORTNAME AS RequesterName, U1.[BO PHAN] AS RequesterDept,
                   U2.SHORTNAME AS ApproverName
            FROM {config.TABLE_EXPENSE_REQUEST} R
            LEFT JOIN {config.TABLE_BUDGET_MASTER} M ON R.BudgetCode = M.BudgetCode
            LEFT JOIN {config.TEN_BANG_NGUOI_DUNG} U1 ON R.UserCode = U1.USERCODE
            LEFT JOIN {config.TEN_BANG_NGUOI_DUNG} U2 ON R.CurrentApprover = U2.USERCODE
            WHERE R.RequestID = ?
        """
        data = self.db.get_data(query, (request_id,))
        return data[0] if data else None

    def get_payment_queue(self, from_date, to_date):
        """
        Lấy danh sách phiếu Chờ chi & Đã chi.
        """
        query = f"""
            SELECT 
                R.*, 
                U.SHORTNAME as RequesterName,
                M.ParentCode,
                M.BudgetName
            FROM {config.TABLE_EXPENSE_REQUEST} R
            LEFT JOIN {config.TEN_BANG_NGUOI_DUNG} U ON R.UserCode = U.USERCODE
            LEFT JOIN {config.TABLE_BUDGET_MASTER} M ON R.BudgetCode = M.BudgetCode
            WHERE R.Status IN ('APPROVED', 'PAID')
              AND CAST(R.ApprovalDate AS DATE) >= ? 
              AND CAST(R.ApprovalDate AS DATE) <= ?
            ORDER BY 
                CASE WHEN R.Status = 'APPROVED' THEN 0 ELSE 1 END,
                R.ApprovalDate DESC
        """
        data = self.db.get_data(query, (from_date, to_date))
        
        if data:
            for row in data:
                row['Amount'] = safe_float(row.get('Amount'))
                
        return data

    def process_payment(self, request_id, user_code, payment_ref, payment_date):
        """Xác nhận ĐÃ CHI."""
        query = f"""
            UPDATE {config.TABLE_EXPENSE_REQUEST}
            SET Status = 'PAID', 
                PaymentRef = ?, 
                PaymentDate = ?,
                PayerCode = ?
            WHERE RequestID = ? AND Status = 'APPROVED'
        """
        return self.db.execute_non_query(query, (payment_ref, payment_date, user_code, request_id))

    def get_ytd_budget_report(self, department_code, year):
        """
        [FIXED] Báo cáo YTD theo logic:
        1. Plan: Sum từ BudgetPlan (Detail) -> Join Master -> Group by ReportGroup.
        2. Actual: Sum từ GT9000 (Ana03ID) -> Map Ana03ID = ParentCode -> Group by ReportGroup.
        3. Loại trừ mã kết chuyển CP2014 để số liệu không bị sai lệch.
        """
        # --- BƯỚC 1: TẠO MAPPING (Ana03ID/ParentCode -> ReportGroup) ---
        # Lấy danh sách ParentCode và ReportGroup tương ứng từ bảng Master
        query_map = f"""
            SELECT DISTINCT ParentCode, ReportGroup 
            FROM {config.TABLE_BUDGET_MASTER} 
            WHERE ParentCode IS NOT NULL AND ParentCode <> ''
        """
        mapping_data = self.db.get_data(query_map)
        
        # Tạo Dictionary: Key=ParentCode (tức Ana03ID), Value=ReportGroup
        # Ví dụ: {'CP_BH': 'Chi phí Bán Hàng', 'CP_QL': 'Chi phí Quản lý'}
        ana03_to_group = {row['ParentCode']: (row['ReportGroup'] or 'Khác') for row in mapping_data}

        # --- BƯỚC 2: LẤY SỐ LIỆU PLAN (NGÂN SÁCH) ---
        # Logic: Ngân sách được lập chi tiết (BudgetCode), ta cần sum lên theo ReportGroup
        query_plan = f"""
            SELECT 
                M.ReportGroup, 
                P.[Month], 
                SUM(P.BudgetAmount) as PlanAmount
            FROM {config.TABLE_BUDGET_PLAN} P
            INNER JOIN {config.TABLE_BUDGET_MASTER} M ON P.BudgetCode = M.BudgetCode
            WHERE P.FiscalYear = ?
            GROUP BY M.ReportGroup, P.[Month]
        """
        plan_raw = self.db.get_data(query_plan, (year,))

        # --- BƯỚC 3: LẤY SỐ LIỆU ACTUAL (THỰC TẾ) ---
        # Logic: Lấy từ GT9000 theo Ana03ID.
        # [QUAN TRỌNG]: Phải loại trừ mã kết chuyển (CP2014) và chỉ lấy TK chi phí (6*, 8*)
        query_actual = f"""
            SELECT 
                Ana03ID, 
                TranMonth, 
                SUM(ConvertedAmount) as ActualAmount
            FROM {config.ERP_GIAO_DICH}
            WHERE TranYear = ? 
              AND Ana03ID IS NOT NULL 
              AND Ana03ID <> ''
              AND Ana03ID <> '{config.EXCLUDE_ANA03_CP2014}' -- Loại bỏ bút toán kết chuyển
              AND (DebitAccountID LIKE '6%' OR DebitAccountID LIKE '8%') -- Chỉ lấy các đầu tài khoản chi phí
            GROUP BY Ana03ID, TranMonth
        """
        actual_raw = self.db.get_data(query_actual, (year,))

        # --- BƯỚC 4: TỔNG HỢP DỮ LIỆU (AGGREGATION) ---
        groups_data = {}

        # Helper để khởi tạo cấu trúc dữ liệu cho 1 nhóm
        def get_group_entry(g_name):
            if g_name not in groups_data: 
                groups_data[g_name] = {
                    'GroupName': g_name, 
                    'Plan_Month': {},   # {1: 100, 2: 200...}
                    'Actual_Month': {}  # {1: 90, 2: 210...}
                }
            return groups_data[g_name]

        # 4.1. Đổ dữ liệu Plan vào
        if plan_raw:
            for p in plan_raw:
                g_name = p['ReportGroup'] or 'Chưa phân nhóm'
                month = p['Month']
                amount = safe_float(p['PlanAmount'])
                
                entry = get_group_entry(g_name)
                entry['Plan_Month'][month] = entry['Plan_Month'].get(month, 0) + amount

        # 4.2. Đổ dữ liệu Actual vào (Có Mapping)
        if actual_raw:
            for a in actual_raw:
                ana03_id = a['Ana03ID']
                month = a['TranMonth']
                amount = safe_float(a['ActualAmount'])
                
                # Tìm ReportGroup tương ứng với Ana03ID này
                # Nếu không tìm thấy trong mapping -> Cho vào nhóm "Chi phí khác (ERP)"
                g_name = ana03_to_group.get(ana03_id, 'Chi phí khác (Chưa mapping)')
                
                entry = get_group_entry(g_name)
                entry['Actual_Month'][month] = entry['Actual_Month'].get(month, 0) + amount

        # --- BƯỚC 5: TÍNH TOÁN YTD & FORMAT BÁO CÁO ---
        current_month = datetime.now().month
        # Nếu đang xem năm cũ, YTD là full 12 tháng. Nếu năm nay, YTD là đến tháng hiện tại.
        ytd_limit = 12 if year < datetime.now().year else current_month
        
        final_report = []
        
        for g_name, data in groups_data.items():
            row = {
                'GroupName': g_name,
                'Month_Plan': 0, 'Month_Actual': 0, 'Month_Diff': 0,
                'YTD_Plan': 0, 'YTD_Actual': 0, 'YTD_Diff': 0,
                'Year_Plan': 0, 'UsagePercent': 0
            }
            
            # Duyệt qua 12 tháng để cộng dồn
            for m in range(1, 13):
                p_val = data['Plan_Month'].get(m, 0)
                a_val = data['Actual_Month'].get(m, 0)
                
                # Tổng Plan cả năm
                row['Year_Plan'] += p_val
                
                # Tính YTD (Lũy kế)
                if m <= ytd_limit:
                    row['YTD_Plan'] += p_val
                    row['YTD_Actual'] += a_val
                
                # Tính tháng hiện tại (Current Month)
                if m == current_month:
                    row['Month_Plan'] = p_val
                    row['Month_Actual'] = a_val

            # Tính chênh lệch
            row['Month_Diff'] = row['Month_Plan'] - row['Month_Actual']
            row['YTD_Diff'] = row['YTD_Plan'] - row['YTD_Actual']
            
            # Tính % sử dụng YTD
            if row['YTD_Plan'] > 0:
                row['UsagePercent'] = (row['YTD_Actual'] / row['YTD_Plan']) * 100
            else:
                row['UsagePercent'] = 0 if row['YTD_Actual'] == 0 else 100 # Nếu không có plan mà có chi -> 100% (hoặc cảnh báo đỏ)

            final_report.append(row)

        # Sắp xếp: Nhóm nào Plan năm cao nhất lên đầu
        final_report.sort(key=lambda x: x['Year_Plan'], reverse=True)
        
        return final_report
    
    def get_expense_details_by_group(self, report_group, year):
        """Lấy chi tiết phiếu chi theo ReportGroup."""
        ana_query = f"SELECT DISTINCT ParentCode FROM {config.TABLE_BUDGET_MASTER} WHERE ReportGroup = ?"
        ana_data = self.db.get_data(ana_query, (report_group,))
        
        if not ana_data: return []
        ana_codes = [row['ParentCode'] for row in ana_data if row['ParentCode']]
        if not ana_codes: return []
        ana_str = "', '".join(ana_codes)
        
        query = f"""
            SELECT TOP 100 T1.VoucherNo, T1.VoucherDate, T1.VDescription, T1.ObjectID, 
                   ISNULL(T2.ShortObjectName, T2.ObjectName) as ObjectName, T1.Ana03ID, SUM(T1.ConvertedAmount) as TotalAmount
            FROM {config.ERP_GIAO_DICH} T1
            LEFT JOIN {config.ERP_IT1202} T2 ON T1.ObjectID = T2.ObjectID
            WHERE T1.TranYear = ? AND T1.Ana03ID IN ('{ana_str}')
            GROUP BY T1.VoucherNo, T1.VoucherDate, T1.VDescription, T1.ObjectID, T2.ShortObjectName, T2.ObjectName, T1.Ana03ID
            ORDER BY TotalAmount DESC
        """
        details = self.db.get_data(query, (year,))
        if details:
            for row in details:
                row['TotalAmount'] = safe_float(row['TotalAmount'])
                if row['VoucherDate']:
                    try:
                        row['VoucherDate'] = row['VoucherDate'].strftime('%d/%m/%Y')
                    except Exception:
                        pass
        return details or []