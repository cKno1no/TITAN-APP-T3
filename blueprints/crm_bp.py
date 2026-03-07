# blueprints/crm_bp.py

from flask import current_app, Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from utils import login_required, save_uploaded_files, permission_required, get_user_ip
from datetime import datetime, timedelta
import config 

crm_bp = Blueprint('crm_bp', __name__)

@crm_bp.route('/dashboard', methods=['GET', 'POST'])
@login_required
@permission_required('VIEW_REPORT_LIST') 
def dashboard_reports():
    today = datetime.now()
    filters = {
        'date_from': request.form.get('date_from') or request.args.get('date_from') or (today - timedelta(days=30)).strftime('%Y-%m-%d'),
        'date_to': request.form.get('date_to') or request.args.get('date_to') or today.strftime('%Y-%m-%d'),
        'selected_user': request.form.get('nv_bao_cao') or request.args.get('nv_bao_cao') or '',
        'kh_search': request.form.get('kh_search') or request.args.get('kh_search') or '',
        'text_search': request.form.get('text_search') or request.args.get('text_search') or '',
        'saved_view': request.form.get('saved_view') or request.args.get('saved_view') or ''
    }
    
    page = int(request.args.get('page', 1))
    role = session.get('user_role', '').strip().upper()
    code = session.get('user_code')

    result = current_app.crm_service.get_dashboard_data(
        filters, page, 20, role, code, get_user_ip()
    )
    # Chấp nhận cả 4 hoặc 5 giá trị (service cũ có thể chỉ trả 4)
    if len(result) == 5:
        users_data, report_data, total_reports, total_pages, status_metrics = result
    else:
        users_data, report_data, total_reports, total_pages = result
        status_metrics = {'today_count': 0, 'distinct_customers': 0}

    success_message = request.args.get('success_message', '')
    report_id = request.args.get('report_id', '')
    return render_template(
        'dashboard.html',
        users=users_data, reports=report_data, page=page,
        total_reports=total_reports, total_pages=total_pages,
        success_message=success_message, report_id=report_id,
        status_today_count=status_metrics.get('today_count', 0),
        status_distinct_customers=status_metrics.get('distinct_customers', 0),
        current_user_code=code or '',
        **filters
    )

@crm_bp.route('/report_detail_page/<string:report_stt>', methods=['GET'])
@login_required 
def report_detail_page(report_stt):
    success, result = current_app.crm_service.get_report_detail(
        report_stt, 
        session.get('user_role', '').strip().upper(), 
        session.get('user_code'), 
        get_user_ip()
    )
    if not success:
        flash(result, 'danger')
        return redirect(url_for('crm_bp.dashboard_reports'))
    return render_template('report_detail_page.html', report=result)

@crm_bp.route('/nhaplieu', methods=['GET', 'POST'])
@login_required
def nhap_lieu():
    if request.method == 'POST':
        attachments_str = save_uploaded_files(request.files.getlist('attachment_file')) 
        result = current_app.crm_service.create_report(
            request.form, attachments_str, session.get('user_code'), get_user_ip()
        )
        success = result[0]
        message = result[1]
        report_stt = result[2] if len(result) > 2 else None
        if success:
            # Ghi nhận Gamification
            try:
                nguoi_bao_cao = request.form.get('nv_bao_cao') or session.get('user_code')
                current_app.gamification_service.log_activity(nguoi_bao_cao, 'CREATE_REPORT')
            except Exception as e:
                current_app.logger.error(f"Gamification Error: {e}")
            q = {'success_message': message}
            if report_stt:
                q['report_id'] = report_stt
            return redirect(url_for('crm_bp.dashboard_reports', **q))
        else:
            flash(message, "danger")

    users_data, loai_data = current_app.crm_service.get_dropdowns_for_nhap_lieu()
    return render_template('nhap_lieu.html', users=users_data, loai_bao_cao=loai_data, now_date=datetime.now(), default_usercode=session.get('user_code'))

@crm_bp.route('/nhansu_nhaplieu', methods=['GET', 'POST'])
@login_required
def nhansu_nhaplieu():
    if request.method == 'POST':
        # 1. CHỈ GỌI SANG SERVICE (Không viết SQL ở đây)
        success, msg = current_app.crm_service.create_contact(request.form, session.get('user_code'), get_user_ip())
        
        if success:
            try:
                current_app.gamification_service.log_activity(session.get('user_code'), 'CREATE_CONTACT')
            except Exception as e:
                current_app.logger.error(f"Gamification Error (Create Contact): {e}")

            flash(msg, "success")
            return "<script>window.opener.postMessage('RELOAD_CONTACTS', '*'); window.close();</script>"
            
        flash(msg, "danger")

    # Xử lý khi load form
    kh_code = request.args.get('kh_code', '').strip()
    ten_kh = current_app.crm_service.get_customer_name(kh_code) if kh_code else None
    return render_template('nhansu_nhaplieu.html', default_ma_khachhang=kh_code, default_ten_khachhang=ten_kh)

# --- APIs ---
@crm_bp.route('/api/khachhang/ref/<string:ma_doi_tuong>', methods=['GET'])
@login_required
def api_get_reference_data(ma_doi_tuong):
    return jsonify({'CountNLH': current_app.crm_service.get_contact_count(ma_doi_tuong)})

@crm_bp.route('/api/nhansu_ddl_by_khachhang/<string:ma_doi_tuong>', methods=['GET'])
@login_required
def api_nhansu_ddl_by_khachhang(ma_doi_tuong):
    data = current_app.crm_service.get_contact_dropdown(ma_doi_tuong)
    return jsonify([{'id': r['MA'], 'text': f"{r['TEN THUONG GOI'].strip() or r['TEN HO'].strip()} ({r['CHUC VU'].strip() or 'N/A'})"} for r in data])

@crm_bp.route('/api/defaults/<string:loai_code>', methods=['GET'])
@login_required
def api_defaults(loai_code):
    data = current_app.crm_service.get_defaults(loai_code)
    defaults = {r['LOAI']: r['TEN'] if r['LOAI'].endswith('H') else r['MAC DINH'] for r in data} if data else {}
    return jsonify(defaults)

@crm_bp.route('/api/nhansu/list/<string:ma_doi_tuong>', methods=['GET'])
@login_required
def api_nhansu_list(ma_doi_tuong):
    return jsonify(current_app.crm_service.get_contact_list_detailed(ma_doi_tuong) or [])

@crm_bp.route('/api/nhansu_by_khachhang/<string:ma_doi_tuong>', methods=['GET'])
@login_required
def api_get_nhansu_list(ma_doi_tuong):
    return jsonify(current_app.crm_service.get_contact_list_basic(ma_doi_tuong) or [])

@crm_bp.route('/sales/backlog', methods=['GET', 'POST'])
@login_required
def sales_backlog_page():
    user_role = session.get('user_role', '').strip().upper()
    date_from = request.form.get('date_from') or request.args.get('date_from') or (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    date_to = request.form.get('date_to') or request.args.get('date_to') or datetime.now().strftime('%Y-%m-%d')
    
    salesman_list = current_app.task_service.get_eligible_helpers(division=None) if user_role == config.ROLE_ADMIN else []
    selected_salesman = request.form.get('salesman_id') or request.args.get('salesman_id') or '' if user_role == config.ROLE_ADMIN else session.get('user_code')

    result = current_app.sales_service.get_sales_backlog(date_from, date_to, selected_salesman)
    return render_template('sales_backlog.html', data=result['details'], summary=result['summary'], date_from=date_from, date_to=date_to, salesman_list=salesman_list, selected_salesman=selected_salesman, is_admin=(user_role == config.ROLE_ADMIN))

@crm_bp.route('/inventory_control', methods=['GET'])
@login_required
def inventory_control_page():
    """Trang thanh tra đơn hàng"""
    if session.get('user_role') not in ['ADMIN', 'MANAGER']:
        flash("Bạn không có quyền truy cập trang này.", "danger")
        return redirect(url_for('portal_bp.dashboard'))
    return render_template('inventory_control.html')

@crm_bp.route('/api/inventory_control/data', methods=['GET'])
@login_required
def api_inventory_control_data():
    data = current_app.crm_service.get_so_inventory_control()
    return jsonify(data if data else [])