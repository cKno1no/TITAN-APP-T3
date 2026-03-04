
CREATE PROCEDURE [dbo].[sp_KPI_Acc_GetMetrics]
    @TranYear INT, 
    @TranMonth INT, 
    @UserCode VARCHAR(50)
AS
BEGIN
    SET NOCOUNT ON;

    -- [BƯỚC 1]: Nhận diện Role của User từ bảng Profile (Sử dụng TitanOS_UserProfile)
    DECLARE @KPIRole VARCHAR(50);
    SELECT @KPIRole = KPIRole 
    FROM dbo.TitanOS_UserProfile 
    WHERE LTRIM(RTRIM(UserCode)) = LTRIM(RTRIM(@UserCode));

    -- [BƯỚC 2]: Phân luồng tính toán dựa trên Role chuyên trách

    -- >>> ROLE: KẾ TOÁN KINH DOANH (Thanh Diệu - KD006)
    IF @KPIRole = 'ACC_SALES'
    BEGIN
        SELECT 
            @KPIRole AS KPIRole,
            -- KPI: Độ trễ xuất HĐ (Giờ)
            ISNULL(AVG(CAST(DATEDIFF(hour, W.VoucherDate, G.VoucherDate) AS FLOAT)), 0) AS Invoice_Latency_Hours,
            
            -- KPI: Tỷ lệ treo hóa đơn (%) - VC quá 36h chưa có hóa đơn
            ISNULL((CAST(COUNT(CASE WHEN G.OTransactionID IS NULL 
                                    AND DATEDIFF(hour, W.VoucherDate, GETDATE()) > 36 THEN 1 END) AS FLOAT) 
                    / NULLIF(CAST(COUNT(*) AS FLOAT), 0)) * 100, 0) AS Pending_Invoice_Rate
        FROM [OMEGA_STDD].[dbo].[WT2006] W WITH (NOLOCK)
        INNER JOIN [OMEGA_STDD].[dbo].[WT2007] WD WITH (NOLOCK) ON W.VoucherID = WD.VoucherID
        LEFT JOIN [OMEGA_STDD].[dbo].[GT9000] G WITH (NOLOCK) ON WD.OTransactionID = G.OTransactionID 
             AND G.CreditAccountID LIKE '511%'
        WHERE W.VoucherTypeID = 'VC'
          AND W.TranYear = @TranYear AND W.TranMonth = @TranMonth
          AND W.CreateUserID = @UserCode; -- Đồng bộ theo CreatedUserID
    END

    -- >>> ROLE: KẾ TOÁN KHO (Tú Anh - ACC_WAREHOUSE)
    ELSE IF @KPIRole = 'ACC_WAREHOUSE'
    BEGIN
        DECLARE @Avg_LXH_Latency FLOAT = 0;
        
        SELECT @Avg_LXH_Latency = AVG(CAST(DATEDIFF(hour, H.OrderDate, L.VoucherDate) AS FLOAT))
        FROM [OMEGA_STDD].[dbo].[OT2001] H WITH (NOLOCK)
        INNER JOIN [OMEGA_STDD].[dbo].[OT2002] D WITH (NOLOCK) ON H.SOrderID = D.SOrderID
        INNER JOIN [OMEGA_STDD].[dbo].[OT2302] LD WITH (NOLOCK) ON D.TransactionID = LD.reSPtransactionID
        INNER JOIN [OMEGA_STDD].[dbo].[OT2301] L WITH (NOLOCK) ON LD.VoucherID = L.VoucherID
        WHERE H.OrderStatus = 1 
          AND L.VoucherTypeID = 'LXH'
          AND L.TranYear = @TranYear AND L.TranMonth = @TranMonth
          AND L.CreateUserID = @UserCode;

        DECLARE @Negative_Stock_Count INT = 0;
        SELECT @Negative_Stock_Count = COUNT(*)
        FROM [OMEGA_STDD].[dbo].[WT2008] WITH (NOLOCK)
        WHERE [EndQuantity] < 0 
          AND TranMonth = @TranMonth AND TranYear = @TranYear;

        SELECT 
            @KPIRole AS KPIRole,
            ISNULL(@Avg_LXH_Latency, 0) AS Order_Process_Latency,
            @Negative_Stock_Count AS Negative_Stock_Errors;
    END

    -- >>> ROLE: KẾ TOÁN THANH TOÁN (Thanh Bình - KT004)
    ELSE IF @KPIRole = 'ACC_PAYMENT'
    BEGIN
        SELECT 
            @KPIRole AS KPIRole,
            -- KPI: SLA Chi tiền (Giờ)
            ISNULL(AVG(CAST(DATEDIFF(hour, ApprovalDate, PaymentDate) AS FLOAT)), 0) AS Payment_SLA_Hours,
            
            -- KPI: Tỷ lệ nợ quá hạn / Tổng nợ (Lấy từ bảng summary công nợ)
            ISNULL((SELECT SUM(TotalOverdueDebt) / NULLIF(SUM(TotalDebt), 0) * 100 
                    FROM [CRM_STDD].[dbo].[CRM_AR_AGING_SUMMARY] WITH (NOLOCK)), 0) AS Overdue_Debt_Rate
        FROM [CRM_STDD].[dbo].[EXPENSE_REQUEST] WITH (NOLOCK)
        WHERE PayerCode = @UserCode
          AND MONTH(PaymentDate) = @TranMonth AND YEAR(PaymentDate) = @TranYear;
    END

    -- >>> ROLE: KẾ TOÁN THUẾ (Anh Thư - KD066)
    ELSE IF @KPIRole = 'ACC_TAX'
    BEGIN
        SELECT 
            @KPIRole AS KPIRole,
            -- KPI: Số chứng từ chi phí hạch toán trễ > 15 ngày
            COUNT(CASE WHEN DATEDIFF(day, VoucherDate, CreateDate) > 15 THEN 1 END) AS Late_Expense_Count
        FROM [OMEGA_STDD].[dbo].[GT9000] WITH (NOLOCK)
        WHERE (DebitAccountID LIKE '6%' OR DebitAccountID LIKE '8%')
          AND CreateUserID = @UserCode
          AND TranYear = @TranYear AND TranMonth = @TranMonth;
    END

    -- >>> ROLE: KẾ TOÁN TRƯỞNG (Quốc Nguyễn - KT007)
    ELSE IF @KPIRole = 'ACC_CHIEF'
    BEGIN
        SELECT 
            @KPIRole AS KPIRole,
            -- KPI: SLA Duyệt Expense Request (Giờ)
            ISNULL(AVG(CAST(DATEDIFF(hour, RequestDate, ApprovalDate) AS FLOAT)), 0) AS Admin_Approval_SLA
        FROM [CRM_STDD].[dbo].[EXPENSE_REQUEST] WITH (NOLOCK)
        WHERE Status = 'APPROVED' 
          AND CurrentApprover = @UserCode
          AND YEAR(ApprovalDate) = @TranYear AND MONTH(ApprovalDate) = @TranMonth;
    END
END;

GO
