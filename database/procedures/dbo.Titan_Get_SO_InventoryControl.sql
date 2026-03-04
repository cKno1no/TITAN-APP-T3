CREATE PROCEDURE [dbo].[Titan_Get_SO_InventoryControl]
AS
BEGIN
    SET NOCOUNT ON;

    WITH 
    -- 1. LẤY TẤT CẢ SO TRỪ 'DTK' TRONG 2 NĂM ĐỔ LẠI
    SO_Data AS (
        SELECT 
            ORD.VoucherNo AS OrderNo, 
            ORD.OrderDate, 
            ORD.ContractNo, 
            ISNULL(CUST.ShortObjectName, CUST.ObjectName) AS CustomerName, 
            CUST.ObjectID AS CustomerCode, 
            ORD.SalesManID, 
            DT.TransactionID AS SO_TransactionID, 
            ITEM.InventoryID, 
            ITEM.InventoryName, 
            ISNULL(DT.OrderQuantity, 0) AS Qty_Ordered,
            ORD.VoucherTypeID
        FROM OMEGA_STDD.dbo.OT2001 ORD 
        JOIN OMEGA_STDD.dbo.OT2002 DT ON ORD.SOrderID = DT.SOrderID 
        LEFT JOIN OMEGA_STDD.dbo.IT1202 CUST ON ORD.ObjectID = CUST.ObjectID 
        LEFT JOIN OMEGA_STDD.dbo.IT1302 ITEM ON DT.InventoryID = ITEM.InventoryID 
        WHERE UPPER(ORD.VoucherTypeID) <> 'DTK' 
          AND ORD.OrderDate >= DATEADD(year, -2, GETDATE())
    ),
    PO_Data AS (
        SELECT 
            P2.RefTransactionID AS SO_TransactionID,
            P2.TransactionID AS PO_TransactionID,
            P1.VoucherNo AS PO_No,
            P1.OrderDate AS PO_Date,
            ISNULL(P2.OrderQuantity, 0) AS PO_Qty
        FROM OMEGA_STDD.dbo.PT3001 P1
        JOIN OMEGA_STDD.dbo.PT3002 P2 ON P1.POrderID = P2.POrderID
    ),
    Import_Agg AS (
        SELECT 
            SubT1.OTransactionID AS PO_TransactionID,
            SUM(ISNULL(SubT1.ActualQuantity, 0)) AS SL_nhap, 
            MAX(SubT2.VoucherDate) AS Ngay_nhap
        FROM OMEGA_STDD.dbo.WT2007 SubT1 
        JOIN OMEGA_STDD.dbo.WT2006 SubT2 ON SubT1.VoucherID = SubT2.VoucherID 
        WHERE UPPER(SubT2.VoucherTypeID) IN ('PNM', 'PNN', 'PNK', 'PN') 
        GROUP BY SubT1.OTransactionID
    ),
    Export_Agg AS (
        SELECT 
            SubT1.OTransactionID AS SO_TransactionID,
            SubT2.ObjectID AS ExportCustomerCode, 
            SUM(ISNULL(SubT1.ActualQuantity, 0)) AS SL_xuat, 
            MAX(SubT2.VoucherDate) AS Ngay_xuat
        FROM OMEGA_STDD.dbo.WT2007 SubT1 
        JOIN OMEGA_STDD.dbo.WT2006 SubT2 ON SubT1.VoucherID = SubT2.VoucherID 
        WHERE UPPER(SubT2.VoucherTypeID) IN ('PXN', 'PX', 'PXK') 
        GROUP BY SubT1.OTransactionID, SubT2.ObjectID
    ),
    Invoice_Agg AS (
        SELECT 
            OTransactionID AS SO_TransactionID, 
            MAX(InvoiceNo) AS InvoiceNo
        FROM OMEGA_STDD.dbo.GT9000 
        WHERE (DebitAccountID LIKE '131%' OR CreditAccountID LIKE '511%') 
        GROUP BY OTransactionID
    )

    SELECT 
        S.OrderNo, S.OrderDate, S.ContractNo, S.CustomerName, S.CustomerCode, S.SalesManID, S.VoucherTypeID,
        S.InventoryID, S.InventoryName, S.Qty_Ordered AS SO_Qty_Ordered, 
        P.PO_No, P.PO_Date, ISNULL(P.PO_Qty, 0) AS PO_Qty,
        ISNULL(I.SL_nhap, 0) AS SL_nhap, I.Ngay_nhap, 
        ISNULL(E.SL_xuat, 0) AS SL_xuat, E.Ngay_xuat, 
        INV.InvoiceNo AS HoaDon,
        CASE 
            WHEN I.Ngay_nhap IS NULL THEN N'⚪ Chưa về kho'
            WHEN I.Ngay_nhap IS NOT NULL AND E.Ngay_xuat IS NULL THEN 
                CASE 
                    WHEN DATEDIFF(day, I.Ngay_nhap, GETDATE()) > 90 THEN N'🔴 Tồn > 90 ngày'
                    ELSE N'🟡 Đang nằm kho'
                END
            WHEN I.Ngay_nhap IS NOT NULL AND E.Ngay_xuat IS NOT NULL THEN
                CASE 
                    WHEN S.CustomerCode <> E.ExportCustomerCode THEN N'🚨 XUẤT SAI KHÁCH'
                    WHEN DATEDIFF(day, I.Ngay_nhap, E.Ngay_xuat) > 90 THEN N'🟠 Xuất chậm (> 90 ngày)'
                    ELSE N'🟢 Hợp lệ'
                END
        END AS KetQuaKiemTra
    FROM SO_Data S
    LEFT JOIN PO_Data P ON S.SO_TransactionID = P.SO_TransactionID
    LEFT JOIN Import_Agg I ON P.PO_TransactionID = I.PO_TransactionID
    LEFT JOIN Export_Agg E ON S.SO_TransactionID = E.SO_TransactionID
    LEFT JOIN Invoice_Agg INV ON S.SO_TransactionID = INV.SO_TransactionID
    ORDER BY 
        -- Đưa những ca Vi phạm và Xuất sai khách lên đầu tiên
        CASE 
            WHEN I.Ngay_nhap IS NOT NULL AND E.Ngay_xuat IS NULL AND DATEDIFF(day, I.Ngay_nhap, GETDATE()) > 90 THEN 1
            WHEN I.Ngay_nhap IS NOT NULL AND E.Ngay_xuat IS NOT NULL AND S.CustomerCode <> E.ExportCustomerCode THEN 2
            ELSE 3
        END,
        S.OrderDate DESC;
END
GO
