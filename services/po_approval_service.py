# po_approval_service.py
# Service: Duyệt Đơn Mua Hàng (PO / DPO)
# Pattern: Clone từ sales_order_approval_service.py
#
# Public methods:
#   get_orders_for_approval()   → Gọi sp_GetPOPendingList
#   run_full_check()            → Chạy Tầng 1 + 2 + 3, trả dict cho modal
#   approve_purchase_order()    → Re-verify server-side, gọi sp_ApprovePO, ghi history
#   record_dhb_risk()           → Gọi từ sales_order_approval_service, ghi CRM_DHB_Risk_History
#
# CURSOR — Thêm vào sales_order_approval_service.approve_sales_order() sau khi DHB pass:
#   try:
#       current_app.po_approval_service.record_dhb_risk(
#           sorder_id=sorder_id, voucher_no=sorder_no,
#           voucher_type_id=voucher_type_id, employee_id=employee_id,
#           client_id=object_id, total_value=float(total_value or 0),
#       )
#   except Exception:
#       pass  # Không ảnh hưởng luồng DHB
#
# Internal methods (prefixed _):
#   _check_all_lines()          → Tầng 1: gọi sp_CheckPOLines
#   _check_price_history()      → Tầng 2: gọi sp_CheckPOPriceHistory
#   _calc_risk_score()          → Tầng 3: gọi sp_GetInventoryRiskContext + PORiskScorer
#   _determine_permissions()    → Tầng 4: logic phân quyền

import json
import logging
from typing import Any

import config

logger = logging.getLogger(__name__)


class POApprovalService:

    def __init__(self, db_manager):
        self.db = db_manager

    # ════════════════════════════════════════════════════════════
    # PUBLIC: Danh sách PO chờ duyệt
    # ════════════════════════════════════════════════════════════
    def get_orders_for_approval(
        self,
        user_code: str,
        user_role: str,
        date_from: str,
        date_to: str,
        voucher_type_filter: str = '',
    ) -> list[dict]:
        """
        Gọi sp_GetPOPendingList.
        Mỗi order được tính sẵn ApprovalResult cơ bản để render dashboard
        (chỉ dùng data từ SP — không chạy full 5 tầng ở đây để tránh chậm).
        """
        rows = self.db.get_data(
            f"EXEC {config.SP_PO_PENDING_LIST} ?,?,?,?",
            (user_code, user_role, date_from, date_to),
        ) or []

        orders = []
        for r in rows:
            order = dict(r)
            # SP trả về VoucherDisplay; template dùng VoucherNo
            order['VoucherNo'] = order.get('VoucherDisplay', order.get('VoucherNo', ''))

            # Filter voucher type nếu cần
            if voucher_type_filter and order.get('VoucherTypeID') != voucher_type_filter:
                continue

            # Build lightweight CheckResult từ data có sẵn
            # (Không chạy Risk Score ở đây — chờ modal gọi /api/po/check_result)
            all_linked = bool(order.get('AllLinesLinked', 0))
            is_dpo     = order.get('VoucherTypeID') == 'DPO'

            order['CheckResult'] = {
                'HasBlock':          not all_linked,
                'BlockReason':       '' if all_linked else 'Có dòng hàng chưa kế thừa',
                'NeedsOverride':     False,
                'CanSelfApprove':    all_linked and not is_dpo,
                'RequiresGM':        False,
                'RiskScore':         0.0,
                'RiskVerdict':       '',
                'Tier2PriceFlag':    False,
                'PriceFlagCount':    0,
            }
            orders.append(order)

        return orders

    # ════════════════════════════════════════════════════════════
    # PUBLIC: Chạy đầy đủ 5 tầng — cho modal
    # ════════════════════════════════════════════════════════════
    def run_full_check(self, porder_id: str) -> dict:
        """
        Chạy Tầng 1 → 2 → 3 → 4, trả về dict đầy đủ cho Alpine modal.
        Nhanh: Tầng 1 block thì không cần chạy 2, 3.
        """
        # Lấy header PO để biết VoucherTypeID
        header = self._get_po_header(porder_id)
        if not header:
            raise ValueError(f'Không tìm thấy PO: {porder_id}')

        voucher_type = header.get('VoucherTypeID', 'PO')
        total_value  = float(header.get('TotalPOValue', 0) or 0)

        result = {
            'porder_id':          porder_id,
            'voucher_type_id':    voucher_type,
            'has_block':          False,
            'block_reason':       '',
            'tier1_checks':       [],
            'tier2_price_flags':  [],
            'risk_score':         0.0,
            'risk_verdict':       'SAFE',
            'risk_flags':         [],
            'can_self_approve':   False,
            'needs_override':     False,
            'requires_gm':        False,
            'can_manager_approve': False,
        }

        # ── Tầng 1 ────────────────────────────────────────────
        tier1_result = self._check_all_lines(porder_id, voucher_type)
        result['tier1_checks'] = tier1_result['checks']

        if tier1_result['has_block']:
            result['has_block']    = True
            result['block_reason'] = tier1_result['block_reason']
            return result   # Stop early — không cần check 2, 3

        # ── Tầng 2 ────────────────────────────────────────────
        tier2_result = self._check_price_history(porder_id)
        result['tier2_price_flags'] = tier2_result['flags']
        needs_override_t2 = tier2_result['has_flag']

        # ── Tầng 3 ────────────────────────────────────────────
        tier3_result = self._calc_risk_score(porder_id, total_value)
        result['risk_score']   = tier3_result['total_score']
        result['risk_verdict'] = tier3_result['verdict']
        result['risk_flags']   = tier3_result['flags']

        # ── Tầng 4 ────────────────────────────────────────────
        perms = self._determine_permissions(
            voucher_type   = voucher_type,
            risk_score     = tier3_result['total_score'],
            needs_override = needs_override_t2,
        )
        result.update(perms)

        return result

    # ════════════════════════════════════════════════════════════
    # PUBLIC: Ghi quyết định duyệt
    # ════════════════════════════════════════════════════════════
    def approve_purchase_order(
        self,
        porder_id: str,
        voucher_no: str,
        voucher_type_id: str,
        employee_id: str,
        action: str,            # 'APPROVED' | 'REJECTED'
        approver_code: str,
        approver_note: str      = '',
        is_self_approved: int   = 0,
        risk_score: float       = 0.0,      # Score do client gửi lên — chỉ dùng để ghi log
        risk_verdict: str       = '',
        fraud_flags_json: str   = '[]',
        tier2_price_flag: int   = 0,
        is_violation: int       = 0,
        violation_type: str     = '',
        violation_evidence: str = '{}',
    ) -> dict:
        """
        SERVER-SIDE RE-VERIFY trước khi ghi DB:
          1. Re-chạy run_full_check() độc lập — không tin score từ client.
          2. Nếu server tính được score cao hơn client gửi → dùng server score.
          3. Nếu server phát hiện Tầng 1 block mà client không báo → từ chối ghi.
          Lý do: client có thể bị tamper, hoặc dữ liệu DB thay đổi giữa lúc
          user mở modal và lúc user bấm duyệt (race condition).

        APPROVED → OrderStatus 0→1.
        REJECTED → Giữ OrderStatus=0, chỉ ghi history.
        """
        try:
            # ── Bước 1: Re-verify độc lập ───────────────────────────
            try:
                server_check = self.run_full_check(porder_id)
            except Exception as e:
                logger.warning(f'[approve_purchase_order] re-verify failed for {porder_id}: {e}')
                server_check = None

            if server_check is None:
                return {
                    'success': False,
                    'message': 'Không thể kiểm tra lại phiếu. Vui lòng đóng modal, chạy lại "Kiểm tra" rồi thử duyệt.',
                }

            if server_check:
                # 1a. Tầng 1 block → từ chối tuyệt đối dù client gửi APPROVED
                if server_check.get('has_block') and action == 'APPROVED':
                    reason = server_check.get('block_reason', 'Vi phạm Tầng 1.')
                    logger.warning(
                        f'[approve_purchase_order] BLOCKED server-side: {porder_id} — {reason}'
                    )
                    return {
                        'success': False,
                        'message': f'Server phát hiện vi phạm Tầng 1: {reason} — Không thể duyệt.',
                    }

                # 1b. Dùng score server nếu cao hơn client (tránh client gửi thấp để qua guard)
                server_score   = server_check.get('risk_score', 0.0)
                server_verdict = server_check.get('risk_verdict', risk_verdict)
                server_flags   = server_check.get('risk_flags', [])

                if server_score > risk_score:
                    logger.warning(
                        f'[approve_purchase_order] Score mismatch {porder_id}: '
                        f'client={risk_score} server={server_score} — dùng server score'
                    )
                    risk_score       = server_score
                    risk_verdict     = server_verdict
                    fraud_flags_json = json.dumps(server_flags, ensure_ascii=False)

                # 1c. Re-check quyền với server score
                if action == 'APPROVED':
                    if risk_score >= config.PO_RISK_SCORE_ESCALATE_GM:
                        # Blueprint đã guard, nhưng double-check ở service layer
                        logger.info(
                            f'[approve_purchase_order] CRITICAL score {risk_score:.1f} '
                            f'ghi lại bởi {approver_code} — cần xác nhận GM ở blueprint'
                        )

            # ── Bước 2: Gọi sp_ApprovePO ────────────────────────────
            rows = self.db.get_data(
                f"EXEC {config.SP_PO_APPROVE} ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?",
                (
                    porder_id,
                    voucher_no,
                    voucher_type_id,
                    employee_id,
                    action,
                    approver_code,
                    approver_note,
                    round(risk_score, 2),
                    risk_verdict,
                    fraud_flags_json,
                    is_self_approved,
                    tier2_price_flag,
                    is_violation,
                    violation_type or None,
                    violation_evidence or None,
                ),
            )

            # SP trả về { Success, POrderID, Action, ProcessedAt }
            if rows and rows[0].get('Success') == 1:
                action_vn = 'Đã duyệt' if action == 'APPROVED' else 'Đã từ chối'
                return {
                    'success': True,
                    'message': f'{action_vn} {voucher_no} thành công.',
                }
            else:
                return {'success': False, 'message': 'SP không trả về kết quả thành công.'}

        except Exception as e:
            logger.error(f'[approve_purchase_order] {porder_id}: {e}')
            return {'success': False, 'message': str(e)}

    # ════════════════════════════════════════════════════════════
    # PUBLIC: Ghi Risk Score tại thời điểm tạo DHB
    # Gọi từ sales_order_approval_service sau khi DHB pass validation.
    # KHÔNG block DHB — chỉ INSERT CRM_DHB_Risk_History để phân tích sau.
    # ════════════════════════════════════════════════════════════
    def record_dhb_risk(
        self,
        sorder_id: str,
        voucher_no: str,
        voucher_type_id: str,
        employee_id: str,
        client_id: str,
        total_value: float,
    ) -> None:
        """
        Tính Risk Score cho DHB và lưu vào CRM_DHB_Risk_History.
        Mục đích: sau 6–12 tháng query được pattern NV nào liên tục
        tạo DHB có RiskScore cao → bằng chứng khách quan cố tình lách DPO.

        Gọi bất đồng bộ (try/except nuốt lỗi) — không ảnh hưởng luồng DHB.
        """
        try:
            # Lấy InventoryIDs từ OT2002
            sql_lines = """
                SELECT InventoryID,
                       OrderQuantity,
                       ISNULL(ConvertedAmount, UnitPrice * OrderQuantity) AS ConvertedAmount
                FROM [OMEGA_STDD].[dbo].[OT2002]
                WHERE SOrderID = ?
            """
            raw_lines = self.db.get_data(sql_lines, (sorder_id,)) or []
            if not raw_lines:
                return

            po_lines = [dict(r) for r in raw_lines]
            inventory_csv = ','.join(str(ln['InventoryID']) for ln in po_lines)

            risk_rows = self.db.get_data(
                f"EXEC {config.SP_PO_RISK_CONTEXT} ?",
                (inventory_csv,),
            ) or []
            risk_ctx = {r['InventoryID']: dict(r) for r in risk_rows}

            scorer = PORiskScorer()
            scored = scorer.score_po(po_lines, risk_ctx, total_value)

            sql_insert = f"""
                INSERT INTO {config.TABLE_DHB_RISK_HISTORY}
                    (SOrderID, VoucherNo, VoucherTypeID, EmployeeID, ClientID,
                     TotalPOValue, RiskScore, RiskVerdict, Flags, CreatedAt)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE())
            """
            self.db.execute_non_query(sql_insert, (
                sorder_id,
                voucher_no,
                voucher_type_id,
                employee_id,
                client_id,
                round(total_value, 2),
                round(scored['total_score'], 2),
                scored['verdict'],
                json.dumps(scored['flags'], ensure_ascii=False),
            ))

            logger.info(
                f'[record_dhb_risk] {sorder_id} — Score={scored["total_score"]:.1f} '
                f'Verdict={scored["verdict"]}'
            )

        except Exception as e:
            # Nuốt lỗi có chủ ý — DHB không bị ảnh hưởng
            logger.error(f'[record_dhb_risk] {sorder_id}: {e}')

    # ════════════════════════════════════════════════════════════
    # PRIVATE: Lấy PO header
    # ════════════════════════════════════════════════════════════
    def _get_po_header(self, porder_id: str) -> dict | None:
        """Lấy thông tin cơ bản từ PT3001 — dùng để biết VoucherTypeID và TotalPOValue."""
        sql = f"""
            SELECT
                T1.POrderID,
                T1.VoucherNo,
                T1.VoucherTypeID,
                T1.EmployeeID,
                T1.ObjectID AS SupplierID,
                ISNULL(SUM(T2.PurchasePrice * T2.OrderQuantity), 0) AS TotalPOValue
            FROM [OMEGA_STDD].[dbo].[PT3001] T1
            LEFT JOIN [OMEGA_STDD].[dbo].[PT3002] T2 ON T1.POrderID = T2.POrderID
            WHERE T1.POrderID = ?
            GROUP BY T1.POrderID, T1.VoucherNo, T1.VoucherTypeID, T1.EmployeeID, T1.ObjectID
        """
        rows = self.db.get_data(sql, (porder_id,)) or []
        return dict(rows[0]) if rows else None

    # ════════════════════════════════════════════════════════════
    # PRIVATE: Tầng 1 — sp_CheckPOLines
    # ════════════════════════════════════════════════════════════
    def _check_all_lines(self, porder_id: str, voucher_type: str) -> dict:
        """
        Gọi sp_CheckPOLines — nhận 2 result sets.
        RS1: summary counts (UnlinkedLines, QtyExceedLines, ShipDateLateLines)
        RS2: chi tiết từng dòng vi phạm
        """
        result_sets = self.db.execute_sp_multi(
            config.SP_PO_CHECK_LINES,
            (porder_id, voucher_type),
        )

        summary  = dict(result_sets[0][0]) if result_sets[0] else {}
        vio_rows = [dict(r) for r in result_sets[1]] if len(result_sets) > 1 else []

        unlinked   = int(summary.get('UnlinkedLines', 0))
        qty_exceed = int(summary.get('QtyExceedLines', 0))
        late_ship  = int(summary.get('ShipDateLateLines', 0))

        checks = []

        # 1A — Kế thừa
        unlinked_lines = [v for v in vio_rows if v.get('ViolationType') == 'UNLINKED_LINE']
        checks.append({
            'label':  '1A — 100% dòng kế thừa từ DDH/DTK',
            'passed': unlinked == 0,
            'detail': '' if unlinked == 0
                      else f'{unlinked} dòng chưa có RefTransactionID — xóa hoặc kế thừa trước khi duyệt.',
            'lines':  unlinked_lines,
        })

        # 1B — Số lượng
        qty_lines = [v for v in vio_rows
                     if v.get('ViolationType') in ('QTY_EXCEED_DHB', 'QTY_EXCEED_AND_LATE')]
        checks.append({
            'label':  '1B — Số lượng PO ≤ Số lượng DHB kế thừa',
            'passed': qty_exceed == 0,
            'detail': '' if qty_exceed == 0
                      else f'{qty_exceed} dòng vượt SL đã đặt của khách.',
            'lines':  qty_lines,
        })

        # 1C — ShipDate (chỉ PO)
        if voucher_type == 'PO':
            late_lines = [v for v in vio_rows
                          if v.get('ViolationType') in ('SHIPDATE_LATE', 'QTY_EXCEED_AND_LATE')]
            checks.append({
                'label':  '1C — ShipDate ≤ Ngày KH cần (Date01)',
                'passed': late_ship == 0,
                'detail': '' if late_ship == 0
                          else f'{late_ship} dòng hàng về trễ hơn ngày khách cần.',
                'lines':  late_lines,
            })

        has_block    = (unlinked > 0 or qty_exceed > 0 or late_ship > 0)
        block_reason = ''
        if unlinked > 0:
            block_reason = f'{unlinked} dòng chưa kế thừa DHB/DTK.'
        elif qty_exceed > 0:
            block_reason = f'{qty_exceed} dòng SL vượt DHB.'
        elif late_ship > 0:
            block_reason = f'{late_ship} dòng ShipDate trễ hơn KH cần.'

        return {'has_block': has_block, 'block_reason': block_reason, 'checks': checks}

    # ════════════════════════════════════════════════════════════
    # PRIVATE: Tầng 2 — sp_CheckPOPriceHistory
    # ════════════════════════════════════════════════════════════
    def _check_price_history(self, porder_id: str) -> dict:
        """
        Gọi sp_CheckPOPriceHistory với ngưỡng từ config.
        Trả về danh sách flag và bool has_flag.
        """
        result_sets = self.db.execute_sp_multi(
            config.SP_PO_CHECK_PRICE,
            (
                porder_id,
                config.PO_RISK_PRICE_THRESHOLD_PCT,
                config.PO_RISK_PRICE_HISTORY_DAYS,
            ),
        )

        summary   = dict(result_sets[0][0]) if result_sets[0] else {}
        flag_rows = [dict(r) for r in result_sets[1]] if len(result_sets) > 1 else []

        has_flag = bool(int(summary.get('HasPriceFlag', 0)))

        return {
            'has_flag': has_flag,
            'flags':    flag_rows,
        }

    # ════════════════════════════════════════════════════════════
    # PRIVATE: Tầng 3 — PORiskScorer (weighted)
    # ════════════════════════════════════════════════════════════
    def _calc_risk_score(self, porder_id: str, total_po_value: float) -> dict:
        """
        1. Lấy danh sách dòng hàng từ PT3002 (InventoryID + OrderQuantity + ConvertedAmount)
        2. Gọi sp_GetInventoryRiskContext để lấy TonKho, TieuHaoThang, ROP, LuongThieuDu
        3. Chạy PORiskScorer.score_po() → weighted score
        """
        # Bước 1: Lấy lines từ PT3002
        sql_lines = """
            SELECT
                InventoryID,
                OrderQuantity,
                PurchasePrice,
                ISNULL(ConvertedAmount, PurchasePrice * OrderQuantity) AS ConvertedAmount
            FROM [OMEGA_STDD].[dbo].[PT3002]
            WHERE POrderID = ?
        """
        raw_lines = self.db.get_data(sql_lines, (porder_id,)) or []
        if not raw_lines:
            return {'total_score': 0.0, 'verdict': 'SAFE', 'flags': []}

        po_lines = [dict(r) for r in raw_lines]

        # Bước 2: Gọi SP Risk Context
        inventory_csv = ','.join(str(ln['InventoryID']) for ln in po_lines)
        risk_rows = self.db.get_data(
            f"EXEC {config.SP_PO_RISK_CONTEXT} ?",
            (inventory_csv,),
        ) or []
        risk_ctx = {r['InventoryID']: dict(r) for r in risk_rows}

        # Bước 3: Chạy PORiskScorer
        scorer = PORiskScorer()
        return scorer.score_po(po_lines, risk_ctx, total_po_value)

    # ════════════════════════════════════════════════════════════
    # PRIVATE: Tầng 4 — Phân quyền
    # ════════════════════════════════════════════════════════════
    def _determine_permissions(
        self,
        voucher_type: str,
        risk_score: float,
        needs_override: bool,
    ) -> dict:
        """
        Trả về dict các flag quyền để frontend render đúng nút.
        DPO luôn cần Manager — không bao giờ can_self_approve.
        """
        requires_gm      = risk_score >= config.PO_RISK_SCORE_ESCALATE_GM
        requires_manager = risk_score >= config.PO_RISK_SCORE_ESCALATE_MGR
        is_dpo           = (voucher_type == 'DPO')

        can_self_approve     = (not is_dpo
                                and not requires_manager
                                and not requires_gm
                                and not needs_override)
        needs_override_final = (needs_override
                                or (not is_dpo and requires_manager and not requires_gm))
        can_manager_approve  = (is_dpo or requires_manager or needs_override)

        return {
            'can_self_approve':    can_self_approve,
            'needs_override':      needs_override_final,
            'requires_gm':         requires_gm,
            'can_manager_approve': can_manager_approve,
        }


# ════════════════════════════════════════════════════════════════
# PORiskScorer — Weighted scoring engine
# ════════════════════════════════════════════════════════════════
class PORiskScorer:
    """
    Chấm điểm rủi ro theo tỷ trọng giá trị đơn hàng.
    FutureMonths = (Ton + OrderQty) / TieuHaoThang — đo ngâm vốn tương lai.
    8 Cases: kết hợp LuongThieuDu × FutureMonths.
    """

    # Case score table (không phụ thuộc weight)
    CASE_SCORES = {
        '0':  40,   # No velocity
        'ok': 0,    # Safe
        'A':  20,   # Thiếu + future 6–12 tháng
        'B':  50,   # Thiếu + future 12–24 tháng
        'C':  80,   # Thiếu + future ≥ 24 tháng
        'D':  25,   # Đủ/dư + future < 6 tháng
        'E':  55,   # Đủ/dư + future 6–12 tháng
        'F':  75,   # Đủ/dư + future 12–24 tháng
        'G':  90,   # Đủ/dư + future ≥ 24 tháng
    }

    def score_po(
        self,
        po_lines: list[dict],
        risk_ctx: dict[str, dict],
        total_po_value: float,
    ) -> dict:
        """
        po_lines : List[{InventoryID, OrderQuantity, ConvertedAmount, ...}]
        risk_ctx : {InventoryID → {TonKho, TieuHaoThang, ROP_Goc, LuongThieuDu, CurrentMonthsOfStock, ...}}
        total_po_value : Σ ConvertedAmount — dùng để tính weight

        Returns:
            {
                total_score: float,       # Không cap
                verdict: str,             # 'SAFE'|'WARN'|'HIGH'|'CRITICAL'
                flags: List[dict]         # Chỉ dòng có score > 0
            }
        """
        # Tính total value nếu không truyền
        if not total_po_value or total_po_value <= 0:
            total_po_value = sum(
                float(ln.get('ConvertedAmount') or 0) for ln in po_lines
            )
        if total_po_value <= 0:
            total_po_value = 1.0  # tránh chia 0

        total_score = 0.0
        flags       = []

        for line in po_lines:
            inv_id   = str(line['InventoryID'])
            order_qty= float(line.get('OrderQuantity', 0) or 0)
            line_val = float(line.get('ConvertedAmount') or 0)
            weight   = line_val / total_po_value

            ctx = risk_ctx.get(inv_id)

            # ── Case 0: Không có velocity ──
            if not ctx or not ctx.get('HasVelocityData') or not ctx.get('TieuHaoThang'):
                case_score = self.CASE_SCORES['0']
                ws = case_score * weight
                total_score += ws
                flags.append({
                    'inventory_id':   inv_id,
                    'inventory_name': ctx.get('InventoryName', '') if ctx else '',
                    'case':           '0',
                    'current_months': None,
                    'future_months':  None,
                    'weight':         weight,
                    'line_value':     line_val,
                    'case_score':     case_score,
                    'weighted_score': round(ws, 2),
                    'reason':         'Không có lịch sử bán (velocity = 0). Không thể ước tính thời gian tiêu thụ.',
                    'ton_kho':        round(float(ctx.get('TonKho', 0) or 0), 2) if ctx else 0,
                    'hang_dang_ve':   round(float(ctx.get('HangDangVe', 0) or 0), 2) if ctx else 0,
                    'velocity':       None,
                    'rop':            None,
                    'luong_thieu_du': None,
                    'order_qty':      order_qty,
                })
                continue

            ton_kho     = float(ctx.get('TonKho', 0) or 0)
            velocity    = float(ctx['TieuHaoThang'])
            luong_thieu = float(ctx.get('LuongThieuDu') or 0)
            cur_months  = float(ctx['CurrentMonthsOfStock']) if ctx.get('CurrentMonthsOfStock') is not None else None

            # FutureMonths: tính trong Python vì cần OrderQty
            future_months = (ton_kho + order_qty) / velocity if velocity > 0 else None

            # ── Phân case ──
            case_key  = self._classify(luong_thieu, future_months)
            case_score= self.CASE_SCORES[case_key]
            ws        = case_score * weight
            total_score += ws

            # Luôn append TẤT CẢ dòng — kể cả 'ok' (score=0)
            # Người duyệt cần thấy đủ context cho mọi mã hàng trong PO
            flags.append({
                'inventory_id':   inv_id,
                'inventory_name': ctx.get('InventoryName', '') if ctx else '',
                'case':           case_key,
                'current_months': round(cur_months, 1) if cur_months is not None else None,
                'future_months':  round(future_months, 1) if future_months is not None else None,
                'weight':         round(weight, 4),
                'line_value':     line_val,
                'case_score':     case_score,
                'weighted_score': round(ws, 2),
                'reason':         self._reason(case_key, ton_kho, order_qty, future_months, velocity, luong_thieu),
                # Thêm các tham số thô để hiển thị trong bảng
                'ton_kho':        round(ton_kho, 2),
                'hang_dang_ve':   round(float(ctx.get('HangDangVe', 0) or 0), 2),
                'velocity':       round(velocity, 4),
                'rop':            round(float(ctx.get('ROP_Goc') or 0), 3) if ctx.get('ROP_Goc') is not None else None,
                'luong_thieu_du': round(luong_thieu, 3),
                'order_qty':      order_qty,
            })

        verdict = self._verdict(total_score)
        return {
            'total_score': round(total_score, 2),
            'verdict':     verdict,
            'flags':       sorted(flags, key=lambda x: x['weighted_score'], reverse=True),
        }

    # ── Phân loại case ──
    def _classify(self, luong_thieu_du: float, future_months: float | None) -> str:
        if future_months is None:
            return '0'

        m_warn = config.PO_RISK_MONTHS_WARN       # 6
        m_high = config.PO_RISK_MONTHS_HIGH        # 12
        m_crit = config.PO_RISK_MONTHS_CRITICAL    # 24

        if luong_thieu_du > 0:
            # Kho đang thiếu theo ROP
            if future_months < m_warn:   return 'ok'
            if future_months < m_high:   return 'A'
            if future_months < m_crit:   return 'B'
            return 'C'
        else:
            # Kho đang đủ hoặc dư
            if future_months < m_warn:   return 'D'
            if future_months < m_high:   return 'E'
            if future_months < m_crit:   return 'F'
            return 'G'

    # ── Reason text ──
    def _reason(
        self,
        case: str,
        ton_kho: float,
        order_qty: float,
        future_months: float | None,
        velocity: float,
        luong_thieu_du: float,
    ) -> str:
        fm = f'{future_months:.0f} tháng' if future_months is not None else 'N/A'
        status = 'Tồn kho đang thiếu theo ROP.' if luong_thieu_du > 0 else 'Tồn kho đang đủ/dư theo ROP.'

        reasons = {
            'A': f'{status} Đặt {order_qty:.0f} đv. Sau khi nhập sẽ đủ {fm} — hơi nhiều (6–12 tháng).',
            'B': f'{status} Sau khi nhập sẽ đủ {fm} — rủi ro ngâm vốn (12–24 tháng).',
            'C': f'{status} Sau khi nhập sẽ đủ {fm} — bất thường, ngâm vốn >2 năm.',
            'D': f'{status} Đặt ít ({order_qty:.0f} đv) nhưng kho vẫn đang đủ. FutureMonths={fm}.',
            'E': f'{status} Sau khi nhập sẽ đủ {fm} — rủi ro ngâm vốn thực tế.',
            'F': f'{status} Sau khi nhập sẽ ngâm {fm} — bằng chứng vi phạm DTK/DDH.',
            'G': f'{status} Sau khi nhập sẽ ngâm {fm} (>2 năm). Bằng chứng rõ ràng nhất.',
        }
        return reasons.get(case, f'Case {case}: FutureMonths={fm}.')

    # ── Verdict ──
    def _verdict(self, score: float) -> str:
        if score == 0:   return 'SAFE'
        if score < config.PO_RISK_SCORE_ESCALATE_MGR: return 'WARN'
        if score < config.PO_RISK_SCORE_ESCALATE_GM:  return 'HIGH'
        return 'CRITICAL'