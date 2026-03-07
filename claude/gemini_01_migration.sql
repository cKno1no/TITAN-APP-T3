-- ============================================================
-- GEMINI TASK 1/4 — CREATE TABLES (Migration)
-- Database: CRM_STDD
-- Chạy 1 lần khi deploy. Idempotent (có IF NOT EXISTS).
-- ============================================================

USE [CRM_STDD]
GO

-- ────────────────────────────────────────────────────────────
-- TABLE 1: CRM_PO_Approval_History
-- Ghi lại mọi quyết định duyệt / từ chối PO và DPO.
-- Titan INSERT vào đây sau mỗi lần approve_purchase_order().
-- ────────────────────────────────────────────────────────────
IF NOT EXISTS (
    SELECT 1 FROM sys.objects
    WHERE object_id = OBJECT_ID(N'[dbo].[CRM_PO_Approval_History]')
      AND type = N'U'
)
BEGIN
    CREATE TABLE [dbo].[CRM_PO_Approval_History] (
        [ApprovalID]        INT             IDENTITY(1,1)   NOT NULL,
        [POrderID]          NVARCHAR(20)    NOT NULL,           -- FK → PT3001.POrderID (VD: PO20250000003256)
        [VoucherNo]         NVARCHAR(20)    NOT NULL,           -- Mã hiển thị (VD: PO/2026/03/001)
        [VoucherTypeID]     NVARCHAR(20)    NOT NULL,           -- 'PO' hoặc 'DPO'
        [Action]            NVARCHAR(20)    NOT NULL,           -- 'APPROVED' | 'REJECTED'
        [ApproverCode]      NVARCHAR(20)    NOT NULL,           -- UserCode người duyệt
        [ApproverNote]      NVARCHAR(500)   NULL,               -- Lý do duyệt/từ chối
        [RiskScore]         DECIMAL(6,2)    NOT NULL DEFAULT 0, -- Weighted score tại thời điểm duyệt
        [RiskVerdict]       NVARCHAR(20)    NULL,               -- 'SAFE'|'WARN'|'HIGH'|'CRITICAL'
        [FraudFlags]        NVARCHAR(MAX)   NULL,               -- JSON: [{inventory_id, case, months_of_stock, reason, score}]
        [IsSelfApproved]    BIT             NOT NULL DEFAULT 0, -- 1 = NV tự duyệt (không qua Manager)
        [Tier2PriceFlag]    BIT             NOT NULL DEFAULT 0, -- 1 = có cảnh báo giá vượt 15%
        [CreatedAt]         DATETIME        NOT NULL DEFAULT GETDATE(),
        [CreatedBy]         NVARCHAR(20)    NOT NULL,           -- UserCode người thao tác (= ApproverCode)

        CONSTRAINT [PK_CRM_PO_Approval_History]
            PRIMARY KEY CLUSTERED ([ApprovalID] ASC)
    )

    -- Index tra cứu theo PO
    CREATE NONCLUSTERED INDEX [IX_POApprovalHistory_POrderID]
        ON [dbo].[CRM_PO_Approval_History] ([POrderID] ASC)

    -- Index tra cứu theo người duyệt + thời gian (dùng cho báo cáo tháng)
    CREATE NONCLUSTERED INDEX [IX_POApprovalHistory_Approver_Date]
        ON [dbo].[CRM_PO_Approval_History] ([ApproverCode] ASC, [CreatedAt] DESC)

    PRINT 'Created: CRM_PO_Approval_History'
END
ELSE
    PRINT 'Skip: CRM_PO_Approval_History already exists'
GO


-- ────────────────────────────────────────────────────────────
-- TABLE 2: CRM_PO_Violation_History
-- Ghi vi phạm khi Manager từ chối DPO và đánh dấu vi phạm,
-- hoặc khi Tầng 1 Hard-block bắt được vi phạm nghiêm trọng.
-- ────────────────────────────────────────────────────────────
IF NOT EXISTS (
    SELECT 1 FROM sys.objects
    WHERE object_id = OBJECT_ID(N'[dbo].[CRM_PO_Violation_History]')
      AND type = N'U'
)
BEGIN
    CREATE TABLE [dbo].[CRM_PO_Violation_History] (
        [ViolationID]       INT             IDENTITY(1,1)   NOT NULL,
        [POrderID]          NVARCHAR(20)    NOT NULL,           -- FK → PT3001.POrderID
        [VoucherNo]         NVARCHAR(20)    NOT NULL,           -- Mã hiển thị
        [VoucherTypeID]     NVARCHAR(20)    NOT NULL,           -- 'PO' | 'DPO'
        [EmployeeID]        NVARCHAR(20)    NOT NULL,           -- NV tạo PO (PT3001.EmployeeID)
        [ViolationType]     NVARCHAR(50)    NOT NULL,
            -- 'UNLINKED_LINE'     : Tầng 1A - dòng không kế thừa
            -- 'QTY_EXCEED_DHB'    : Tầng 1B - SL vượt DHB
            -- 'SHIPDATE_LATE'     : Tầng 1C - ShipDate > Date01
            -- 'PRICE_SPIKE'       : Tầng 2  - Giá vượt 15%
            -- 'RISK_HIGH'         : Tầng 3  - Risk score cao, Manager từ chối
            -- 'RISK_CRITICAL'     : Tầng 3  - Risk score critical, GM từ chối
        [PatternDescription] NVARCHAR(200)  NULL,              -- Mô tả ngắn vi phạm
        [Evidence]          NVARCHAR(MAX)   NULL,              -- JSON: bằng chứng số liệu
        [RecordedBy]        NVARCHAR(20)    NOT NULL,          -- Manager/GM ghi vi phạm
        [CreatedAt]         DATETIME        NOT NULL DEFAULT GETDATE(),

        CONSTRAINT [PK_CRM_PO_Violation_History]
            PRIMARY KEY CLUSTERED ([ViolationID] ASC)
    )

    -- Index tra cứu vi phạm theo NV (dùng cho Employee Risk Score)
    CREATE NONCLUSTERED INDEX [IX_POViolation_Employee_Date]
        ON [dbo].[CRM_PO_Violation_History] ([EmployeeID] ASC, [CreatedAt] DESC)

    PRINT 'Created: CRM_PO_Violation_History'
END
ELSE
    PRINT 'Skip: CRM_PO_Violation_History already exists'
GO


-- ────────────────────────────────────────────────────────────
-- TABLE 3: CRM_DHB_Risk_History
-- Ghi Risk Score tại thời điểm NV tạo DHB (Sales Order).
-- Không block DHB. Chỉ lưu để phân tích pattern sau 6-12 tháng.
-- ────────────────────────────────────────────────────────────
IF NOT EXISTS (
    SELECT 1 FROM sys.objects
    WHERE object_id = OBJECT_ID(N'[dbo].[CRM_DHB_Risk_History]')
      AND type = N'U'
)
BEGIN
    CREATE TABLE [dbo].[CRM_DHB_Risk_History] (
        [RiskID]            INT             IDENTITY(1,1)   NOT NULL,
        [SOrderID]          NVARCHAR(20)    NOT NULL,           -- FK → OT2001.SOrderID
        [VoucherNo]         NVARCHAR(20)    NOT NULL,           -- Mã DHB hiển thị (DDH/...)
        [VoucherTypeID]     NVARCHAR(20)    NOT NULL,           -- 'DDH' | 'DTK' | v.v.
        [EmployeeID]        NVARCHAR(20)    NOT NULL,           -- NV tạo DHB
        [ClientID]          NVARCHAR(20)    NULL,               -- ObjectID khách hàng
        [TotalPOValue]      DECIMAL(18,2)   NULL,               -- Tổng giá trị DHB
        [RiskScore]         DECIMAL(6,2)    NOT NULL DEFAULT 0, -- Weighted score
        [RiskVerdict]       NVARCHAR(20)    NULL,               -- 'SAFE'|'WARN'|'HIGH'|'CRITICAL'
        [Flags]             NVARCHAR(MAX)   NULL,               -- JSON flags từng dòng hàng
        [CreatedAt]         DATETIME        NOT NULL DEFAULT GETDATE(),

        CONSTRAINT [PK_CRM_DHB_Risk_History]
            PRIMARY KEY CLUSTERED ([RiskID] ASC)
    )

    -- Index cho báo cáo theo NV và thời gian
    CREATE NONCLUSTERED INDEX [IX_DHBRisk_Employee_Date]
        ON [dbo].[CRM_DHB_Risk_History] ([EmployeeID] ASC, [CreatedAt] DESC)

    -- Index để tránh duplicate: 1 SOrderID chỉ có 1 risk record
    CREATE UNIQUE NONCLUSTERED INDEX [UX_DHBRisk_SOrderID]
        ON [dbo].[CRM_DHB_Risk_History] ([SOrderID] ASC)

    PRINT 'Created: CRM_DHB_Risk_History'
END
ELSE
    PRINT 'Skip: CRM_DHB_Risk_History already exists'
GO


-- ────────────────────────────────────────────────────────────
-- TABLE 4: CRM_Employee_Risk_Score
-- Bảng tổng hợp rủi ro theo NV. Cập nhật hàng tuần bằng job.
-- Dùng để cộng thêm score vào PO/DPO của NV có lịch sử vi phạm.
-- Sprint 3 mới dùng — tạo sẵn ở đây để migration đầy đủ.
-- ────────────────────────────────────────────────────────────
IF NOT EXISTS (
    SELECT 1 FROM sys.objects
    WHERE object_id = OBJECT_ID(N'[dbo].[CRM_Employee_Risk_Score]')
      AND type = N'U'
)
BEGIN
    CREATE TABLE [dbo].[CRM_Employee_Risk_Score] (
        [EmployeeID]        NVARCHAR(20)    NOT NULL,
        [TotalPO_6M]        INT             NOT NULL DEFAULT 0,  -- Tổng PO tạo trong 6 tháng
        [ViolationCount_6M] INT             NOT NULL DEFAULT 0,  -- Số vi phạm trong 6 tháng
        [RejectionRate]     DECIMAL(5,2)    NOT NULL DEFAULT 0,  -- % PO bị từ chối
        [LastViolationDate] DATETIME        NULL,
        [RiskLevel]         NVARCHAR(10)    NOT NULL DEFAULT 'LOW',
            -- 'LOW': 0-1 vi phạm / 'MEDIUM': 2-3 vi phạm / 'HIGH': ≥4 vi phạm
        [ScoreBonus]        INT             NOT NULL DEFAULT 0,
            -- Cộng thêm vào mọi PO/DPO của NV này:
            -- LOW=0, MEDIUM=15, HIGH=30
        [UpdatedAt]         DATETIME        NOT NULL DEFAULT GETDATE(),

        CONSTRAINT [PK_CRM_Employee_Risk_Score]
            PRIMARY KEY CLUSTERED ([EmployeeID] ASC)
    )

    PRINT 'Created: CRM_Employee_Risk_Score'
END
ELSE
    PRINT 'Skip: CRM_Employee_Risk_Score already exists'
GO

PRINT '=== Migration hoàn tất: 4 tables trong CRM_STDD ==='
GO
