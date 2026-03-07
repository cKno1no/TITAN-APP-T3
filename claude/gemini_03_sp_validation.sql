-- ============================================================
-- GEMINI TASK 3/4 — Tầng 1 + Tầng 2 Validation SPs
-- Database: CRM_STDD (gọi cross-db sang OMEGA_STDD)
--
-- SP A: sp_CheckPOLines        — Tầng 1 Hard-block
--   1A: 100% dòng phải có RefTransactionID
--   1B: PT3002.OrderQuantity ≤ OT2002.OrderQuantity
--   1C: PT3002.ShipDate ≤ OT2002.Date01  (chỉ áp dụng PO, không áp dụng DPO)
--
-- SP B: sp_CheckPOPriceHistory  — Tầng 2 Warning
--   Giá mua hiện tại vượt 15% trung bình 720 ngày → flag
-- ============================================================

USE [CRM_STDD]
GO


-- ────────────────────────────────────────────────────────────
-- SP A: sp_CheckPOLines
-- Gọi bởi: po_approval_service._check_all_lines()
-- Output:  2 result sets:
--   RS1: Summary  { UnlinkedLines, QtyExceedLines, ShipDateLateLines }
--   RS2: Detail   { InventoryID, ViolationType, PO_Qty, DHB_Qty,
--                   PO_ShipDate, DHB_Date01, Excess }
--          Chỉ trả về các dòng VI PHẠM để Python hiển thị message.
-- ────────────────────────────────────────────────────────────
IF OBJECT_ID(N'[dbo].[sp_CheckPOLines]', N'P') IS NOT NULL
    DROP PROCEDURE [dbo].[sp_CheckPOLines]
GO

CREATE PROCEDURE [dbo].[sp_CheckPOLines]
    @POrderID       NVARCHAR(20),
    @VoucherTypeID  NVARCHAR(20)    -- 'PO' hoặc 'DPO'
                                    -- ShipDate check chỉ chạy khi 'PO'
AS
BEGIN
    SET NOCOUNT ON;

    -- ── RS1: Summary counts ──────────────────────────────────
    SELECT
        -- 1A: Dòng chưa kế thừa
        SUM(CASE
            WHEN T1.RefTransactionID IS NULL
              OR LTRIM(RTRIM(T1.RefTransactionID)) = ''
            THEN 1 ELSE 0
        END)                                    AS UnlinkedLines,

        -- 1B: Dòng vượt SL DHB
        SUM(CASE
            WHEN T1.RefTransactionID IS NOT NULL
             AND LTRIM(RTRIM(T1.RefTransactionID)) <> ''
             AND T1.OrderQuantity > ISNULL(T2.OrderQuantity, 0)
            THEN 1 ELSE 0
        END)                                    AS QtyExceedLines,

        -- 1C: Dòng ShipDate trễ (chỉ tính khi là PO)
        SUM(CASE
            WHEN @VoucherTypeID = 'PO'
             AND T1.RefTransactionID IS NOT NULL
             AND LTRIM(RTRIM(T1.RefTransactionID)) <> ''
             AND T2.Date01 IS NOT NULL
             AND T1.ShipDate > T2.Date01
            THEN 1 ELSE 0
        END)                                    AS ShipDateLateLines,

        COUNT(*)                                AS TotalLines

    FROM [OMEGA_STDD].[dbo].[PT3002] AS T1
    LEFT JOIN [OMEGA_STDD].[dbo].[OT2002] AS T2
        ON T1.RefTransactionID = T2.TransactionID
    WHERE T1.POrderID = @POrderID;


    -- ── RS2: Chi tiết từng dòng vi phạm ─────────────────────
    SELECT
        T1.InventoryID,
        T1.OrderQuantity                        AS PO_Qty,
        ISNULL(T2.OrderQuantity, 0)             AS DHB_Qty,
        T1.OrderQuantity - ISNULL(T2.OrderQuantity, 0)
                                                AS Excess,          -- > 0 = vượt
        T1.ShipDate                             AS PO_ShipDate,
        T2.Date01                               AS DHB_Date01,
        T2.InventoryID                          AS DHB_InventoryID,

        -- Python dùng ViolationType để build message
        CASE
            WHEN T1.RefTransactionID IS NULL
              OR LTRIM(RTRIM(T1.RefTransactionID)) = ''
            THEN 'UNLINKED_LINE'

            WHEN T1.OrderQuantity > ISNULL(T2.OrderQuantity, 0)
             AND @VoucherTypeID = 'PO'
             AND T1.ShipDate > T2.Date01
            THEN 'QTY_EXCEED_AND_LATE'          -- Cả 2 vi phạm cùng lúc

            WHEN T1.OrderQuantity > ISNULL(T2.OrderQuantity, 0)
            THEN 'QTY_EXCEED_DHB'

            WHEN @VoucherTypeID = 'PO'
             AND T2.Date01 IS NOT NULL
             AND T1.ShipDate > T2.Date01
            THEN 'SHIPDATE_LATE'

            ELSE NULL                           -- Không vi phạm
        END                                     AS ViolationType

    FROM [OMEGA_STDD].[dbo].[PT3002] AS T1
    LEFT JOIN [OMEGA_STDD].[dbo].[OT2002] AS T2
        ON T1.RefTransactionID = T2.TransactionID
    WHERE T1.POrderID = @POrderID
      AND (
            -- 1A
            T1.RefTransactionID IS NULL
         OR LTRIM(RTRIM(T1.RefTransactionID)) = ''
            -- 1B
         OR T1.OrderQuantity > ISNULL(T2.OrderQuantity, 0)
            -- 1C (chỉ khi PO)
         OR (
                @VoucherTypeID = 'PO'
            AND T2.Date01 IS NOT NULL
            AND T1.ShipDate > T2.Date01
            )
      )
    ORDER BY T1.InventoryID;

    SET NOCOUNT OFF;
END
GO

-- ── Quick test ───────────────────────────────────────────────
-- EXEC [dbo].[sp_CheckPOLines] 'PO20250000003256', 'PO'
-- EXEC [dbo].[sp_CheckPOLines] 'DPO20250000001234', 'DPO'
GO


-- ────────────────────────────────────────────────────────────
-- SP B: sp_CheckPOPriceHistory
-- Tầng 2: Kiểm tra đơn giá mua hiện tại so với lịch sử.
-- Ngưỡng: config.PO_RISK_PRICE_THRESHOLD_PCT (default 15%)
--          config.PO_RISK_PRICE_HISTORY_DAYS  (default 720)
-- Output: Danh sách dòng hàng có giá vượt ngưỡng.
--         Python đọc HasPriceFlag = (COUNT > 0) để set NeedsOverride.
-- ────────────────────────────────────────────────────────────
IF OBJECT_ID(N'[dbo].[sp_CheckPOPriceHistory]', N'P') IS NOT NULL
    DROP PROCEDURE [dbo].[sp_CheckPOPriceHistory]
GO

CREATE PROCEDURE [dbo].[sp_CheckPOPriceHistory]
    @POrderID               NVARCHAR(20),
    -- Truyền từ config để không hardcode trong SP
    @PriceThresholdPct      DECIMAL(6,2) = 15.0,    -- config.PO_RISK_PRICE_THRESHOLD_PCT
    @HistoryDays            INT          = 720       -- config.PO_RISK_PRICE_HISTORY_DAYS
AS
BEGIN
    SET NOCOUNT ON;

    -- ── RS1: Summary ─────────────────────────────────────────
    -- Python chỉ cần biết có flag hay không (HasPriceFlag)
    -- và tổng số dòng vi phạm để hiển thị badge.
    SELECT
        COUNT(*)            AS FlaggedLines,
        CASE WHEN COUNT(*) > 0 THEN 1 ELSE 0 END AS HasPriceFlag

    FROM (
        -- Subquery: Tìm dòng có giá vượt ngưỡng
        SELECT T1.InventoryID
        FROM [OMEGA_STDD].[dbo].[PT3002] AS T1
        CROSS APPLY (
            -- Tính giá trung bình lịch sử cho từng InventoryID
            SELECT AVG(H.PurchasePrice) AS AvgPrice
            FROM [OMEGA_STDD].[dbo].[PT3002]  AS H
            INNER JOIN [OMEGA_STDD].[dbo].[PT3001] AS PH
                ON H.POrderID = PH.POrderID
            WHERE H.InventoryID   = T1.InventoryID
              AND PH.OrderStatus  = 1                                       -- Chỉ PO đã duyệt
              AND PH.OrderDate   >= DATEADD(DAY, -@HistoryDays, GETDATE())  -- Trong N ngày
              AND H.PurchasePrice > 0                                       -- Bỏ dòng giá 0
        ) AS HistAvg
        WHERE T1.POrderID = @POrderID
          AND HistAvg.AvgPrice > 0                           -- Có lịch sử
          AND T1.PurchasePrice > HistAvg.AvgPrice * (1 + @PriceThresholdPct / 100.0)
    ) AS FlaggedItems;


    -- ── RS2: Chi tiết từng dòng vi phạm ─────────────────────
    SELECT
        T1.InventoryID,
        T1.PurchasePrice                        AS CurrentPrice,
        HistAvg.AvgPrice,
        -- % vượt so với TB lịch sử
        ROUND(
            (T1.PurchasePrice / HistAvg.AvgPrice - 1.0) * 100,
        2)                                      AS PctOver,
        -- Ngưỡng config để Python hiển thị trong message
        @PriceThresholdPct                      AS ThresholdPct,
        @HistoryDays                            AS HistoryDays

    FROM [OMEGA_STDD].[dbo].[PT3002] AS T1
    CROSS APPLY (
        SELECT AVG(H.PurchasePrice) AS AvgPrice
        FROM [OMEGA_STDD].[dbo].[PT3002]  AS H
        INNER JOIN [OMEGA_STDD].[dbo].[PT3001] AS PH
            ON H.POrderID = PH.POrderID
        WHERE H.InventoryID   = T1.InventoryID
          AND PH.OrderStatus  = 1
          AND PH.OrderDate   >= DATEADD(DAY, -@HistoryDays, GETDATE())
          AND H.PurchasePrice > 0
    ) AS HistAvg
    WHERE T1.POrderID = @POrderID
      AND HistAvg.AvgPrice > 0
      AND T1.PurchasePrice > HistAvg.AvgPrice * (1 + @PriceThresholdPct / 100.0)
    ORDER BY PctOver DESC;   -- Dòng vượt nhiều nhất lên đầu

    SET NOCOUNT OFF;
END
GO

-- ── Quick test ───────────────────────────────────────────────
-- EXEC [dbo].[sp_CheckPOPriceHistory] 'PO20250000003256', 15.0, 720
GO
