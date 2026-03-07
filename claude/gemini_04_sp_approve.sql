-- ============================================================
-- GEMINI TASK 4/4 — sp_GetPOPendingList + sp_ApprovePO
-- Database: CRM_STDD (cross-db sang OMEGA_STDD)
--
-- SP C: sp_GetPOPendingList  — Dashboard: danh sách PO chờ duyệt
-- SP D: sp_ApprovePO         — Ghi duyệt: UPDATE PT3001 + INSERT history
-- ============================================================

USE [CRM_STDD]
GO


-- ────────────────────────────────────────────────────────────
-- SP C: sp_GetPOPendingList
-- Gọi bởi: po_approval_service.get_orders_for_approval()
-- Logic phân quyền:
--   Admin/GM → thấy tất cả
--   Manager  → thấy tất cả (để duyệt DPO và PO escalate)
--   NV       → chỉ thấy PO của chính mình (EmployeeID = @UserCode)
--              và chỉ PO (không thấy DPO — DPO do Manager quản lý)
-- Output: Header PO + thông tin Employee + tổng giá trị
-- ────────────────────────────────────────────────────────────
IF OBJECT_ID(N'[dbo].[sp_GetPOPendingList]', N'P') IS NOT NULL
    DROP PROCEDURE [dbo].[sp_GetPOPendingList]
GO

CREATE PROCEDURE [dbo].[sp_GetPOPendingList]
    @UserCode       NVARCHAR(20),
    @UserRole       NVARCHAR(20),       -- 'ADMIN'|'GM'|'MANAGER'|'SALES'
    @DateFrom       DATE        = NULL, -- NULL → đầu tháng hiện tại
    @DateTo         DATE        = NULL  -- NULL → cuối tháng hiện tại
AS
BEGIN
    SET NOCOUNT ON;

    -- Default date range: tháng hiện tại
    IF @DateFrom IS NULL
        SET @DateFrom = DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1)
    IF @DateTo IS NULL
        SET @DateTo = EOMONTH(GETDATE())

    -- Flag: có quyền xem tất cả không
    DECLARE @IsPrivileged BIT = 0
    IF UPPER(@UserRole) IN ('ADMIN', 'GM', 'MANAGER')
        SET @IsPrivileged = 1

    SELECT
        -- Header PO
        T1.POrderID,
        T1.VoucherNo                            AS VoucherDisplay,  -- PO/2026/03/001
        T1.VoucherTypeID,                                           -- 'PO' hoặc 'DPO'
        T1.OrderDate,
        T1.ObjectID                             AS SupplierID,
        ISNULL(SUP.ShortObjectName, T1.ObjectID) AS SupplierName,

        -- NV tạo PO
        T1.EmployeeID,
        ISNULL(USR.SHORTNAME, T1.EmployeeID)    AS EmployeeName,

        -- Tổng giá trị PO (từ PT3002)
        ISNULL(SUM(T2.PurchasePrice * T2.OrderQuantity), 0) AS TotalPOValue,
        COUNT(T2.TransactionID)                 AS LineCount,

        -- Thông tin kế thừa
        MIN(CASE
            WHEN T2.RefTransactionID IS NULL
              OR LTRIM(RTRIM(T2.RefTransactionID)) = ''
            THEN 0 ELSE 1
        END)                                    AS AllLinesLinked,  -- 0 = có dòng chưa link

        -- Notes từ PT3001 (để hiển thị nhanh trên dashboard)
        T1.Notes,

        -- Ngày tạo để sort
        T1.OrderDate                            AS SortDate

    FROM [OMEGA_STDD].[dbo].[PT3001] AS T1
    LEFT JOIN [OMEGA_STDD].[dbo].[PT3002] AS T2
        ON T1.POrderID = T2.POrderID
    LEFT JOIN [OMEGA_STDD].[dbo].[IT1202] AS SUP
        ON T1.ObjectID = SUP.ObjectID
    LEFT JOIN [GD - NGUOI DUNG] AS USR
        ON T1.EmployeeID = USR.USERCODE

    WHERE
        T1.OrderStatus = 0                      -- Chỉ lấy PO chưa duyệt
        AND T1.OrderDate BETWEEN @DateFrom AND @DateTo
        AND (
            @IsPrivileged = 1                   -- Admin/GM/Manager: thấy tất cả
            OR (
                T1.EmployeeID = @UserCode       -- NV thường: chỉ thấy của mình
                AND T1.VoucherTypeID = 'PO'     -- và chỉ thấy PO (không thấy DPO)
            )
        )

    GROUP BY
        T1.POrderID, T1.VoucherNo, T1.VoucherTypeID, T1.OrderDate,
        T1.ObjectID, SUP.ShortObjectName,
        T1.EmployeeID, USR.SHORTNAME, T1.Notes

    ORDER BY
        -- DPO lên trước (cần Manager duyệt), sau đó PO
        CASE WHEN T1.VoucherTypeID = 'DPO' THEN 0 ELSE 1 END ASC,
        T1.OrderDate DESC;

    SET NOCOUNT OFF;
END
GO

-- ── Quick test ───────────────────────────────────────────────
-- EXEC [dbo].[sp_GetPOPendingList] 'HANG', 'SALES', '2026-03-01', '2026-03-31'
-- EXEC [dbo].[sp_GetPOPendingList] 'MANAGER01', 'MANAGER', NULL, NULL
GO


-- ────────────────────────────────────────────────────────────
-- SP D: sp_ApprovePO
-- Gọi bởi: po_approval_service.approve_purchase_order()
-- Thực hiện trong 1 transaction:
--   1. Kiểm tra PO vẫn còn OrderStatus = 0 (tránh double-approve)
--   2. UPDATE PT3001: OrderStatus = 1, ghi ApproverID, ApproverNotes
--   3. INSERT CRM_PO_Approval_History
--   4. INSERT CRM_PO_Violation_History nếu @IsViolation = 1
--      (Manager từ chối và đánh dấu vi phạm → dùng khi Action = 'REJECTED')
--
-- LƯU Ý QUAN TRỌNG:
--   OrderStatus chỉ có 0 (chờ) và 1 (đã duyệt).
--   PO không duyệt → NV tự xử lý trên Omega. SP này KHÔNG set OrderStatus = 3.
--   Khi Action = 'REJECTED': SP chỉ INSERT history, KHÔNG UPDATE PT3001.
-- ────────────────────────────────────────────────────────────
IF OBJECT_ID(N'[dbo].[sp_ApprovePO]', N'P') IS NOT NULL
    DROP PROCEDURE [dbo].[sp_ApprovePO]
GO

CREATE PROCEDURE [dbo].[sp_ApprovePO]
    -- Định danh PO
    @POrderID           NVARCHAR(20),
    @VoucherNo          NVARCHAR(20),       -- Mã hiển thị (PO/...) để ghi log
    @VoucherTypeID      NVARCHAR(20),       -- 'PO' | 'DPO'
    @EmployeeID         NVARCHAR(20),       -- NV tạo PO (từ PT3001)

    -- Quyết định
    @Action             NVARCHAR(20),       -- 'APPROVED' | 'REJECTED'
    @ApproverCode       NVARCHAR(20),
    @ApproverNote       NVARCHAR(500)  = NULL,

    -- Risk Score (từ PORiskScorer)
    @RiskScore          DECIMAL(6,2)   = 0,
    @RiskVerdict        NVARCHAR(20)   = NULL,
    @FraudFlagsJson     NVARCHAR(MAX)  = NULL,  -- JSON string
    @IsSelfApproved     BIT            = 0,
    @Tier2PriceFlag     BIT            = 0,

    -- Vi phạm (chỉ dùng khi Action = 'REJECTED' và Manager muốn ghi vi phạm)
    @IsViolation        BIT            = 0,
    @ViolationType      NVARCHAR(50)   = NULL,
    @ViolationEvidence  NVARCHAR(MAX)  = NULL   -- JSON bằng chứng

AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    BEGIN TRANSACTION;
    BEGIN TRY

        -- ── Guard: Kiểm tra PO vẫn còn OrderStatus = 0 ──────
        DECLARE @CurrentStatus TINYINT
        SELECT @CurrentStatus = OrderStatus
        FROM [OMEGA_STDD].[dbo].[PT3001]
        WHERE POrderID = @POrderID

        IF @CurrentStatus IS NULL
        BEGIN
            ROLLBACK TRANSACTION;
            RAISERROR(N'Không tìm thấy PO: %s', 16, 1, @POrderID);
            RETURN;
        END

        IF @CurrentStatus <> 0
        BEGIN
            ROLLBACK TRANSACTION;
            RAISERROR(N'PO %s đã được xử lý (OrderStatus = %d). Không thể thao tác lại.', 16, 1, @POrderID, @CurrentStatus);
            RETURN;
        END

        -- ── Bước 1: Nếu APPROVED → UPDATE PT3001 ────────────
        -- Nếu REJECTED → KHÔNG update PT3001 (OrderStatus giữ nguyên = 0)
        -- NV tự xử lý PO bị từ chối trên Omega.
        IF @Action = 'APPROVED'
        BEGIN
            UPDATE [OMEGA_STDD].[dbo].[PT3001]
            SET
                OrderStatus         = 1,            -- 0 → 1: Đã duyệt
                -- Ghi thông tin người duyệt vào các cột Titan được phép viết
                -- (Xác nhận tên cột ApproverID với team Omega trước khi dùng)
                LastModifyUserID    = @ApproverCode,
                LastModifyDate      = GETDATE()
                -- ApproverNotes ghi vào PT3001.Varchar02 nếu có
                -- hoặc chỉ lưu trong CRM_PO_Approval_History
            WHERE POrderID = @POrderID
              AND OrderStatus = 0                   -- Double-check tránh race condition
        END

        -- ── Bước 2: INSERT CRM_PO_Approval_History ──────────
        -- Ghi lại mọi quyết định (cả APPROVED lẫn REJECTED)
        INSERT INTO [dbo].[CRM_PO_Approval_History] (
            POrderID, VoucherNo, VoucherTypeID, Action,
            ApproverCode, ApproverNote,
            RiskScore, RiskVerdict, FraudFlags,
            IsSelfApproved, Tier2PriceFlag,
            CreatedAt, CreatedBy
        )
        VALUES (
            @POrderID, @VoucherNo, @VoucherTypeID, @Action,
            @ApproverCode, @ApproverNote,
            @RiskScore, @RiskVerdict, @FraudFlagsJson,
            @IsSelfApproved, @Tier2PriceFlag,
            GETDATE(), @ApproverCode
        )

        -- ── Bước 3: INSERT CRM_PO_Violation_History ─────────
        -- Chỉ khi Manager chủ động đánh dấu đây là vi phạm
        IF @IsViolation = 1 AND @Action = 'REJECTED' AND @ViolationType IS NOT NULL
        BEGIN
            INSERT INTO [dbo].[CRM_PO_Violation_History] (
                POrderID, VoucherNo, VoucherTypeID, EmployeeID,
                ViolationType, PatternDescription,
                Evidence, RecordedBy, CreatedAt
            )
            VALUES (
                @POrderID, @VoucherNo, @VoucherTypeID, @EmployeeID,
                @ViolationType,
                -- PatternDescription: tóm tắt từ ApproverNote
                LEFT(ISNULL(@ApproverNote, ''), 200),
                @ViolationEvidence, @ApproverCode, GETDATE()
            )
        END

        COMMIT TRANSACTION;

        -- ── Output: Trả về kết quả để Python log ─────────────
        SELECT
            1                   AS Success,
            @POrderID           AS POrderID,
            @VoucherNo          AS VoucherNo,
            @Action             AS Action,
            GETDATE()           AS ProcessedAt

    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;

        -- Re-throw để Python catch và log
        DECLARE @ErrMsg  NVARCHAR(4000) = ERROR_MESSAGE()
        DECLARE @ErrSev  INT            = ERROR_SEVERITY()
        RAISERROR(@ErrMsg, @ErrSev, 1);
    END CATCH

    SET NOCOUNT OFF;
END
GO

-- ── Quick test APPROVED ──────────────────────────────────────
-- EXEC [dbo].[sp_ApprovePO]
--     @POrderID       = 'PO20250000003256',
--     @VoucherNo      = 'PO/2026/03/001',
--     @VoucherTypeID  = 'PO',
--     @EmployeeID     = 'HANG',
--     @Action         = 'APPROVED',
--     @ApproverCode   = 'HANG',
--     @ApproverNote   = 'PO hợp lệ, đã xác nhận PO khách.',
--     @RiskScore      = 0.0,
--     @RiskVerdict    = 'SAFE',
--     @IsSelfApproved = 1

-- ── Quick test REJECTED với vi phạm ─────────────────────────
-- EXEC [dbo].[sp_ApprovePO]
--     @POrderID       = 'DPO20250000001234',
--     @VoucherNo      = 'DPO/2026/03/005',
--     @VoucherTypeID  = 'DPO',
--     @EmployeeID     = 'HUNG',
--     @Action         = 'REJECTED',
--     @ApproverCode   = 'MANAGER01',
--     @ApproverNote   = 'Tồn kho đang dư 450 đơn vị, không cần đặt thêm.',
--     @RiskScore      = 75.5,
--     @RiskVerdict    = 'CRITICAL',
--     @IsViolation    = 1,
--     @ViolationType  = 'RISK_CRITICAL',
--     @ViolationEvidence = '{"inventory_id":"MAT-001","future_months":28,"ton_kho":450}'
GO
