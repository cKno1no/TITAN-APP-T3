-- ============================================================
-- sp_GetInventoryRiskContext  (v7 — final)
-- LeadTime = Amount04 của InventoryID cụ thể trong IT1302
--            nếu NULL/0 → dùng mặc định 30 ngày
-- SafetyStock = Amount05, mặc định 0
-- ROP luôn được tính (không bao giờ NULL)
-- TonKho = chỉ InventoryID được hỏi (kho riêng từng mã)
-- XML split (SQL Server 2012+)
-- ============================================================

USE [CRM_STDD]
GO

IF OBJECT_ID(N'[dbo].[sp_GetInventoryRiskContext]', N'P') IS NOT NULL
    DROP PROCEDURE [dbo].[sp_GetInventoryRiskContext]
GO

CREATE PROCEDURE [dbo].[sp_GetInventoryRiskContext]
    @InventoryList      NVARCHAR(MAX),
    @DefaultLeadTime    INT = 30        -- ngày mặc định khi Amount04 chưa điền
AS
BEGIN
    SET NOCOUNT ON;

    -- Bước 1: Parse CSV (XML split, SQL 2012+)
    CREATE TABLE #RequestedIDs (InventoryID NVARCHAR(50) NOT NULL)

    DECLARE @xml XML = CAST('<i>' + REPLACE(@InventoryList, ',', '</i><i>') + '</i>' AS XML)
    INSERT INTO #RequestedIDs (InventoryID)
    SELECT LTRIM(RTRIM(n.value('.', 'NVARCHAR(50)')))
    FROM @xml.nodes('/i') AS T(n)
    WHERE LTRIM(RTRIM(n.value('.', 'NVARCHAR(50)'))) <> ''

    -- Bước 2: Item master — Varchar05, InventoryName, LeadTime, SafetyStock
    -- LeadTime lấy từ Amount04 của InventoryID này
    -- Nếu 0 hoặc NULL → @DefaultLeadTime (30 ngày)
    CREATE TABLE #ItemMaster (
        InventoryID     NVARCHAR(50)  NOT NULL,
        Varchar05       NVARCHAR(50)  NULL,
        InventoryName   NVARCHAR(255) NULL,
        LeadTime_Days   DECIMAL(10,2) NOT NULL,   -- luôn > 0
        SafetyStock_Qty DECIMAL(18,4) NOT NULL,
        IsDefaultLead   BIT           NOT NULL    -- 1 = dùng giá trị mặc định
    )
    INSERT INTO #ItemMaster
    SELECT
        I.InventoryID,
        I.Varchar05,
        I.InventoryName,
        -- LeadTime: dùng Amount04 nếu > 0, fallback về @DefaultLeadTime
        CASE
            WHEN ISNULL(I.Amount04, 0) > 0 THEN I.Amount04
            ELSE @DefaultLeadTime
        END,
        ISNULL(I.Amount05, 0),
        CASE WHEN ISNULL(I.Amount04, 0) > 0 THEN 0 ELSE 1 END
    FROM [OMEGA_STDD].[dbo].[IT1302] AS I WITH (NOLOCK)
    INNER JOIN #RequestedIDs R ON I.InventoryID = R.InventoryID

    -- Bước 3: Tồn kho của từng InventoryID (không gộp nhóm)
    ;WITH StockCTE AS (
        SELECT
            T.InventoryID,
            SUM(ISNULL(T.Ton, 0)) AS TonKho,
            SUM(ISNULL(T.con, 0)) AS HangDangVe
        FROM [OMEGA_STDD].[dbo].[CRM_TON KHO BACK ORDER] AS T WITH (NOLOCK)
        INNER JOIN #RequestedIDs R ON T.InventoryID = R.InventoryID
        GROUP BY T.InventoryID
    ),

    -- Bước 4: Velocity toàn nhóm Varchar05
    VelocityCTE AS (
        SELECT Varchar05, TotalMonthlyVelocity
        FROM [dbo].[VELOCITY_SKU_GROUP]
        WHERE TotalMonthlyVelocity > 0
    )

    -- Bước 5: Kết hợp — ROP tính từ Velocity nhóm × LeadTime per-item
    SELECT
        R.InventoryID,
        ISNULL(IM.InventoryName, R.InventoryID)  AS InventoryName,
        ISNULL(IM.Varchar05, '')                  AS Varchar05,
        ISNULL(S.TonKho, 0)                       AS TonKho,
        ISNULL(S.HangDangVe, 0)                   AS HangDangVe,

        V.TotalMonthlyVelocity                    AS TieuHaoThang,
        IM.LeadTime_Days,
        IM.SafetyStock_Qty,
        ISNULL(IM.IsDefaultLead, 1)               AS IsDefaultLead,

        -- ROP = (Velocity/30.4 × LeadTime_item) + SafetyStock_item
        -- Luôn có giá trị khi có velocity (LeadTime không bao giờ 0)
        CASE
            WHEN V.TotalMonthlyVelocity > 0
            THEN ((V.TotalMonthlyVelocity / 30.4) * IM.LeadTime_Days)
                 + IM.SafetyStock_Qty
            ELSE NULL
        END                                       AS ROP_Goc,

        -- LuongThieuDu = ROP - (TonKho + HangDangVe)
        -- > 0: đang thiếu hàng so với ROP → cần đặt
        -- ≤ 0: kho đang đủ hoặc dư
        CASE
            WHEN V.TotalMonthlyVelocity > 0
            THEN (((V.TotalMonthlyVelocity / 30.4) * IM.LeadTime_Days)
                 + IM.SafetyStock_Qty)
                 - (ISNULL(S.TonKho, 0) + ISNULL(S.HangDangVe, 0))
            ELSE NULL
        END                                       AS LuongThieuDu,

        -- CurrentMonthsOfStock = TonKho / Velocity
        CASE
            WHEN V.TotalMonthlyVelocity > 0
            THEN CAST(ISNULL(S.TonKho, 0) AS DECIMAL(18,4)) / V.TotalMonthlyVelocity
            ELSE NULL
        END                                       AS CurrentMonthsOfStock,

        CASE WHEN S.InventoryID IS NULL THEN 0 ELSE 1 END AS HasStockData,
        CASE WHEN V.Varchar05   IS NULL THEN 0 ELSE 1 END AS HasVelocityData

    FROM #RequestedIDs AS R
    LEFT JOIN #ItemMaster AS IM ON R.InventoryID = IM.InventoryID
    LEFT JOIN StockCTE    AS S  ON R.InventoryID = S.InventoryID
    LEFT JOIN VelocityCTE AS V  ON IM.Varchar05  = V.Varchar05

    ORDER BY R.InventoryID

    DROP TABLE #RequestedIDs
    DROP TABLE #ItemMaster
    SET NOCOUNT OFF;
END
GO

-- Quick test:
-- EXEC [dbo].[sp_GetInventoryRiskContext] 'AB4087,AB4083,AB1317'
-- AB4087: Varchar05='AB_6208DDU', Amount04=? → LeadTime=Amount04 or 30, IsDefaultLead=0/1
-- AB4083: Varchar05='AB_1205, NSK', Amount04=? → same logic
