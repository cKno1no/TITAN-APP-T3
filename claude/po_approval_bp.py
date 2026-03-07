# po_approval_bp.py
# Blueprint: Duyệt Đơn Mua Hàng (PO / DPO)
# Pattern: Clone từ approval_bp.py — giữ nguyên cấu trúc decorator + service injection
#
# Routes:
#   GET/POST  /po_approval                   → Dashboard (po_approval_dashboard.html)
#   GET       /api/po/check_result/<porder>  → Chạy 5 tầng, trả JSON cho modal Alpine
#   POST      /api/po/approve                → Gọi sp_ApprovePO, ghi history

from flask import Blueprint, render_template, request, session, jsonify, current_app
from utils import login_required, permission_required, get_user_ip, record_activity
from datetime import datetime, timedelta
import config

po_approval_bp = Blueprint('po_approval_bp', __name__)


# ════════════════════════════════════════════════════════════════
# API: Danh sách PO pending (JSON) — lấy từ ý tưởng Gemini
# Alpine gọi sau khi duyệt xong để refresh list không reload trang
# ════════════════════════════════════════════════════════════════
@po_approval_bp.route('/api/po/pending', methods=['GET'])
@login_required
def api_po_pending():
    """
    Trả JSON danh sách PO chờ duyệt — dùng cho Alpine fetchPending().
    Nhận query params: date_from, date_to, voucher_type (optional).
    """
    po_approval_service = current_app.po_approval_service
    user_code  = session.get('user_code')
    user_role  = session.get('user_role', '')

    from datetime import datetime, timedelta
    today           = datetime.now().strftime('%Y-%m-%d')
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

    date_from    = request.args.get('date_from', thirty_days_ago)
    date_to      = request.args.get('date_to',   today)
    voucher_type = request.args.get('voucher_type', '')

    try:
        orders = po_approval_service.get_orders_for_approval(
            user_code=user_code,
            user_role=user_role,
            date_from=date_from,
            date_to=date_to,
            voucher_type_filter=voucher_type,
        )
        return jsonify(orders)
    except Exception as e:
        current_app.logger.error(f'[api_po_pending]: {e}')
        return jsonify([]), 500


# ════════════════════════════════════════════════════════════════
# ROUTE: Dashboard
# ════════════════════════════════════════════════════════════════
@po_approval_bp.route('/po_approval', methods=['GET', 'POST'])
@login_required
@permission_required('APPROVE_PO')
def po_approval_dashboard():
    """
    Dashboard danh sách PO/DPO chờ duyệt.
    Gọi sp_GetPOPendingList với phân quyền theo UserRole.
    """
    po_approval_service = current_app.po_approval_service

    user_code = session.get('user_code')
    user_role = session.get('user_role', '')

    today           = datetime.now().strftime('%Y-%m-%d')
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

    date_from    = request.form.get('date_from')    or request.args.get('date_from')    or thirty_days_ago
    date_to      = request.form.get('date_to')      or request.args.get('date_to')      or today
    voucher_type = request.form.get('voucher_type') or request.args.get('voucher_type') or ''

    orders = po_approval_service.get_orders_for_approval(
        user_code=user_code,
        user_role=user_role,
        date_from=date_from,
        date_to=date_to,
        voucher_type_filter=voucher_type,
    )

    is_admin = (session.get('user_role') or '').upper() in ('ADMIN', 'GM')
    return render_template(
        'po_approval_dashboard.html',
        orders=orders,
        date_from=date_from,
        date_to=date_to,
        voucher_type_filter=voucher_type,
        is_admin=is_admin,
    )


# ════════════════════════════════════════════════════════════════
# API: Chạy toàn bộ 5 tầng kiểm tra — Modal gọi khi user click
# ════════════════════════════════════════════════════════════════
@po_approval_bp.route('/api/po/check_result/<string:porder_id>', methods=['GET'])
@login_required
def api_po_check_result(porder_id):
    """
    Chạy 5 tầng validation cho 1 PO và trả về JSON đầy đủ cho Alpine modal.

    Response schema:
    {
        "porder_id": "PO20250000003256",
        "voucher_type_id": "PO",

        # Tầng 1 — Hard-block
        "has_block": false,
        "block_reason": "",          # Nếu has_block=True
        "tier1_checks": [
            {
                "label": "1A — 100% dòng kế thừa",
                "passed": true,
                "detail": "",
                "lines": []          # Danh sách dòng vi phạm (nếu có)
            },
            { "label": "1B — SL PO ≤ SL DHB", ... },
            { "label": "1C — ShipDate ≤ Date01", ... },  # Chỉ có nếu PO
        ],

        # Tầng 2 — Giá
        "tier2_price_flags": [
            { "InventoryID": "MAT-001", "CurrentPrice": 125000, "AvgPrice": 105000, "PctOver": 19.05 }
        ],

        # Tầng 3 — Risk Score
        "risk_score": 71.9,
        "risk_verdict": "CRITICAL",
        "risk_flags": [
            {
                "inventory_id": "MAT-001",
                "case": "G",
                "current_months": 4.0,
                "future_months": 31.0,
                "weight": 0.75,
                "line_value": 90000000,
                "case_score": 90,
                "weighted_score": 67.5,
                "reason": "Tồn kho đang dư. Sau khi nhập sẽ đủ 31 tháng."
            }
        ],

        # Tầng 4 — Phân quyền
        "can_self_approve": false,    # PO + Score < 50 + không NeedsOverride
        "needs_override": false,       # Giá cảnh báo hoặc Score 1-49
        "requires_gm": true,           # Score >= 80
        "can_manager_approve": false,
    }
    """
    po_approval_service = current_app.po_approval_service

    try:
        result = po_approval_service.run_full_check(porder_id)
        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f'[PO CHECK] {porder_id}: {e}')
        return jsonify({'error': str(e)}), 500


# ════════════════════════════════════════════════════════════════
# API: Ghi quyết định duyệt / từ chối
# ════════════════════════════════════════════════════════════════
@po_approval_bp.route('/api/po/approve', methods=['POST'])
@login_required
@permission_required('APPROVE_PO')
@record_activity('APPROVE_PO')
def api_po_approve():
    """
    Gọi po_approval_service.approve_purchase_order()
    Service sẽ gọi sp_ApprovePO và INSERT CRM_PO_Approval_History.

    Body JSON:
        porder_id, voucher_no, voucher_type_id, employee_id
        action: 'APPROVED' | 'REJECTED'
        approver_note
        is_self_approved: 0 | 1
        risk_score, risk_verdict, fraud_flags_json
        tier2_price_flag: 0 | 1
        is_violation: 0 | 1
        violation_type, violation_evidence
    """
    po_approval_service = current_app.po_approval_service
    db_manager          = current_app.db_manager

    data = request.json
    required = ['porder_id', 'voucher_no', 'voucher_type_id', 'employee_id', 'action']
    for f in required:
        if not data.get(f):
            return jsonify({'success': False, 'message': f'Thiếu trường bắt buộc: {f}'}), 400

    current_user_code = session.get('user_code')
    user_role         = session.get('user_role', '')
    user_ip           = get_user_ip()

    # Guard: DPO chỉ Manager/GM duyệt
    if data['voucher_type_id'] == 'DPO' \
            and user_role not in [config.ROLE_GM, config.ROLE_MANAGER, config.ROLE_ADMIN]:
        return jsonify({'success': False, 'message': 'DPO cần Manager hoặc GM duyệt.'}), 403

    # Guard: Score >= 80 chỉ GM
    risk_score = float(data.get('risk_score', 0))
    if risk_score >= config.PO_RISK_SCORE_ESCALATE_GM \
            and user_role not in [config.ROLE_GM, config.ROLE_ADMIN]:
        return jsonify({'success': False, 'message': f'Risk Score {risk_score:.1f} ≥ {config.PO_RISK_SCORE_ESCALATE_GM} — Chỉ GM duyệt.'}), 403

    try:
        result = po_approval_service.approve_purchase_order(
            porder_id        = data['porder_id'],
            voucher_no       = data['voucher_no'],
            voucher_type_id  = data['voucher_type_id'],
            employee_id      = data['employee_id'],
            action           = data['action'],
            approver_code    = current_user_code,
            approver_note    = data.get('approver_note', ''),
            is_self_approved = int(data.get('is_self_approved', 0)),
            risk_score       = risk_score,
            risk_verdict     = data.get('risk_verdict', ''),
            fraud_flags_json = data.get('fraud_flags_json', '[]'),
            tier2_price_flag = int(data.get('tier2_price_flag', 0)),
            is_violation     = int(data.get('is_violation', 0)),
            violation_type   = data.get('violation_type', ''),
            violation_evidence = data.get('violation_evidence', '{}'),
        )

        if result['success']:
            db_manager.write_audit_log(
                user_code   = current_user_code,
                action_type = f"PO_{data['action']}",
                severity    = 'CRITICAL' if data['action'] == 'APPROVED' else 'WARNING',
                details     = f"{data['action']} {data['voucher_no']} (Risk: {risk_score:.1f} {data.get('risk_verdict','')})",
                ip_address  = user_ip,
            )
            return jsonify({'success': True, 'message': result['message']})
        else:
            return jsonify({'success': False, 'message': result['message']}), 400

    except Exception as e:
        current_app.logger.error(f'[PO APPROVE] {data.get("porder_id")}: {e}')
        return jsonify({'success': False, 'message': f'Lỗi hệ thống: {e}'}), 500


# ═══════════════════════════════════════════════════════════════
# API: Lấy chi tiết dòng hàng PO (Tab Chi tiết trong modal)
# ═══════════════════════════════════════════════════════════════
@po_approval_bp.route('/api/po/detail/<porder_id>', methods=['GET'])
@login_required
@permission_required('APPROVE_PO')
def api_po_detail(porder_id):
    """
    Trả về header + danh sách dòng hàng PT3002 cho modal tab Chi tiết.
    """
    try:
        db = current_app.db_manager

        # Header
        sql_header = """
            SELECT
                T1.POrderID,
                T1.VoucherNo,
                T1.VoucherTypeID,
                T1.ObjectID                        AS SupplierID,
                ISNULL(OBJ.ShortObjectName, T1.ObjectID) AS SupplierName,
                CONVERT(varchar(10), T1.OrderDate, 120)  AS OrderDate,
                T1.Notes
            FROM [OMEGA_STDD].[dbo].[PT3001] T1
            LEFT JOIN [OMEGA_STDD].[dbo].[IT1202] OBJ WITH (NOLOCK)
                   ON T1.ObjectID = OBJ.ObjectID
            WHERE T1.POrderID = ?
        """
        header_rows = db.get_data(sql_header, (porder_id,)) or []
        if not header_rows:
            return jsonify({'error': 'Không tìm thấy PO.'}), 404

        header = dict(header_rows[0])

        # Dòng hàng
        sql_lines = """
            SELECT
                T2.TransactionID,
                T2.InventoryID,
                INV.InventoryName,
                T2.OrderQuantity,
                T2.PurchasePrice,
                T2.ConvertedAmount                            AS LineTotal,
                CONVERT(varchar(10), T2.ShipDate, 120)       AS ShipDate,
                T2.RefTransactionID
            FROM [OMEGA_STDD].[dbo].[PT3002] T2
            LEFT JOIN [OMEGA_STDD].[dbo].[IT1302] INV
                   ON T2.InventoryID = INV.InventoryID
            WHERE T2.POrderID = ?
            ORDER BY T2.TransactionID
        """
        line_rows = db.get_data(sql_lines, (porder_id,)) or []
        lines = [dict(r) for r in line_rows]

        total_value = sum(float(ln.get('LineTotal') or 0) for ln in lines)

        return jsonify({
            'porder_id':     header.get('POrderID'),
            'voucher_no':    header.get('VoucherNo'),
            'supplier_name': header.get('SupplierName') or header.get('SupplierID'),
            'order_date':    header.get('OrderDate'),
            'notes':         header.get('Notes'),
            'total_value':   round(total_value, 2),
            'lines':         lines,
        })

    except Exception as e:
        current_app.logger.error(f'[PO DETAIL] {porder_id}: {e}')
        return jsonify({'error': str(e)}), 500


# ═══════════════════════════════════════════════════════════════
# API: Risk Debug — chỉ ADMIN
# Trả về toàn bộ context dùng để tính Risk Score:
#   - Từng InventoryID: Varchar05, TonKho, HangDangVe,
#     TieuHaoThang, LeadTime, ROP, LuongThieuDu, FutureMonths
#   - OrderQuantity từ PT3002
#   - IsDefaultLead (1 = dùng 30 ngày mặc định)
# ═══════════════════════════════════════════════════════════════
@po_approval_bp.route('/api/po/risk_debug/<string:porder_id>', methods=['GET'])
@login_required
def api_po_risk_debug(porder_id):
    user_role = session.get('user_role', '')
    if str(user_role).strip().upper() != str(config.ROLE_ADMIN).strip().upper():
        return jsonify({'error': 'Chỉ Admin mới có thể xem Risk Debug.'}), 403

    try:
        svc = current_app.po_approval_service
        db  = current_app.db_manager

        # Lấy danh sách InventoryID + OrderQuantity từ PT3002
        sql_lines = """
            SELECT T2.InventoryID, T2.OrderQuantity, T2.PurchasePrice,
                   T2.ConvertedAmount AS LineTotal
            FROM [OMEGA_STDD].[dbo].[PT3002] T2
            WHERE T2.POrderID = ?
            ORDER BY T2.TransactionID
        """
        line_rows = db.get_data(sql_lines, (porder_id,)) or []
        if not line_rows:
            return jsonify({'error': 'Không tìm thấy dòng hàng.'}), 404

        lines_map = {}
        for r in line_rows:
            inv_id = r['InventoryID']
            lines_map[inv_id] = {
                'order_qty':   float(r.get('OrderQuantity') or 0),
                'unit_price':  float(r.get('PurchasePrice') or 0),
                'line_total':  float(r.get('LineTotal') or 0),
            }

        inv_list = ','.join(lines_map.keys())

        # Gọi SP Risk Context để lấy toàn bộ dữ liệu tính score
        from config import config as cfg
        ctx_rows = db.get_data(
            f"EXEC {cfg.SP_PO_RISK_CONTEXT} ?",
            (inv_list,)
        ) or []

        total_po_value = sum(v['line_total'] for v in lines_map.values())

        debug_rows = []
        for r in ctx_rows:
            inv_id    = r.get('InventoryID', '')
            ln        = lines_map.get(inv_id, {})
            order_qty = ln.get('order_qty', 0)
            line_val  = ln.get('line_total', 0)
            velocity  = float(r.get('TieuHaoThang') or 0)
            ton_kho   = float(r.get('TonKho') or 0)
            hang_ve   = float(r.get('HangDangVe') or 0)
            rop       = float(r.get('ROP_Goc') or 0) if r.get('ROP_Goc') is not None else None
            ltd       = float(r.get('LuongThieuDu') or 0) if r.get('LuongThieuDu') is not None else None
            cur_m     = float(r.get('CurrentMonthsOfStock') or 0) if r.get('CurrentMonthsOfStock') is not None else None
            fut_m     = round((ton_kho + order_qty) / velocity, 2) if velocity > 0 else None
            weight    = round(line_val / total_po_value, 4) if total_po_value > 0 else 0

            debug_rows.append({
                'inventory_id':    inv_id,
                'inventory_name':  r.get('InventoryName', ''),
                'varchar05':       r.get('Varchar05', ''),
                'order_qty':       order_qty,
                'unit_price':      ln.get('unit_price', 0),
                'line_total':      line_val,
                'weight_pct':      round(weight * 100, 2),
                'ton_kho':         ton_kho,
                'hang_dang_ve':    hang_ve,
                'tieu_hao_thang':  velocity if velocity > 0 else None,
                'lead_time_days':  float(r.get('LeadTime_Days') or 0) if r.get('LeadTime_Days') is not None else None,
                'is_default_lead': int(r.get('IsDefaultLead') or 0),
                'safety_stock':    float(r.get('SafetyStock_Qty') or 0),
                'rop':             rop,
                'luong_thieu_du':  ltd,
                'current_months':  cur_m,
                'future_months':   fut_m,
                'has_velocity':    int(r.get('HasVelocityData') or 0),
                'has_stock':       int(r.get('HasStockData') or 0),
            })

        return jsonify({
            'porder_id':       porder_id,
            'total_po_value':  round(total_po_value, 2),
            'item_count':      len(debug_rows),
            'rows':            debug_rows,
        })

    except Exception as e:
        current_app.logger.error(f'[RISK DEBUG] {porder_id}: {e}')
        return jsonify({'error': str(e)}), 500