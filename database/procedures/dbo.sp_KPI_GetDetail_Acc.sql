
-- =============================================
-- Author:      Gemini / Sếp
-- Create date: 2026-02-26
-- Description: Lấy chi tiết KPI Kế toán từ dữ liệu gốc OMEGA ERP
-- =============================================
CREATE PROCEDURE [dbo].[sp_KPI_GetDetail_Acc]
    @CriteriaID VARCHAR(50),
    @UserCode VARCHAR(50),
    @Year INT,
    @Month INT
AS
BEGIN
    SET NOCOUNT ON;

    -- 1. TIÊU CHÍ: ĐỘ TRỄ XUẤT HÓA ĐƠN (KPI_KT_THU_04)
    -- Logic: Lấy các chứng từ VC có ngày hạch toán (TranDate) trễ hơn ngày chứng từ (VoucherDate)
    IF @CriteriaID = 'KPI_KT_THU_04'
    BEGIN
        SELECT 
            W.VoucherNo AS InvoiceNo, 
            W.VoucherDate AS NgayChungTu, 
            G.voucherDate AS NgayHoaDon,
            DATEDIFF(day, W.VoucherDate, G.voucherDate) AS SoNgayTre,
            G.VDescription AS DienGiai
        FROM [OMEGA_STDD].[dbo].[WT2006] W
        INNER JOIN [OMEGA_STDD].[dbo].[WT2007] WD ON W.VoucherID = WD.VoucherID
        INNER JOIN [OMEGA_STDD].[dbo].[GT9000] G ON WD.OTransactionID = G.OTransactionID
        WHERE W.VoucherTypeID = 'VC' 
          AND G.CreditAccountID LIKE '511%'
          AND W.TranYear = @Year 
          AND W.TranMonth = @Month
          AND (W.CreateUserID = @UserCode OR @UserCode = 'ADMIN') -- Lọc theo người tạo
          AND DATEDIFF(day, W.VoucherDate, G.voucherDate) > 0        -- Chỉ lấy những dòng bị trễ
        ORDER BY SoNgayTre DESC;
    END

    -- 2. TIÊU CHÍ: TỶ LỆ HÓA ĐƠN TREO (KPI_KT_THU_02)
    -- Logic: Lấy các chứng từ VC chưa được đẩy vào sổ cái (GT9000)
    ELSE IF @CriteriaID = 'KPI_KT_THU_02'
    BEGIN
        SELECT 
            W.VoucherNo AS VoucherNo,
            W.VoucherDate AS NgayCT,
            WD.ConvertedAmount AS SoTien,
            W.Description AS DienGiai,
            N'Chưa có hóa đơn trên sổ cái' AS LyDo
        FROM [OMEGA_STDD].[dbo].[WT2006] W
        INNER JOIN [OMEGA_STDD].[dbo].[WT2007] WD ON W.VoucherID = WD.VoucherID
        LEFT JOIN [OMEGA_STDD].[dbo].[GT9000] G ON WD.OTransactionID = G.OTransactionID AND G.CreditAccountID LIKE '511%'
        WHERE W.VoucherTypeID = 'VC'
          AND G.OTransactionID IS NULL 
          AND W.TranYear = @Year 
          AND W.TranMonth = @Month
          AND (W.CreateUserID = @UserCode OR @UserCode = 'ADMIN')
        ORDER BY W.VoucherDate ASC;
    END

    -- 3. TIÊU CHÍ: NĂNG SUẤT CHỨNG TỪ (KPI_KT_01)
    -- Logic: Đếm tổng số chứng từ đã xử lý trong tháng
    ELSE IF @CriteriaID = 'KPI_KT_01'
    BEGIN
        SELECT 
            VoucherNo, 
            VoucherTypeID AS LoaiPhieu, 
            VoucherDate AS NgayHT, 
            Description AS DienGiai
        FROM [OMEGA_STDD].[dbo].[WT2006]
        WHERE TranYear = @Year 
          AND TranMonth = @Month
          AND (CreateUserID = @UserCode OR @UserCode = 'ADMIN')
        ORDER BY VoucherDate DESC;
    END

    -- 4. [FIXED] TIÊU CHÍ: SLA PHÊ DUYỆT CHI PHÍ (KPI_KT_KTT_02)
    -- Lấy theo bảng EXPENSE_REQUEST sếp cung cấp
    ELSE IF @CriteriaID = 'KPI_KT_KTT_02'
    BEGIN
        SELECT 
            RequestID AS SoPhieu,
            RequestDate AS NgayGui,
            ApprovalDate AS NgayDuyet,
            -- Tính số giờ duyệt (SLA)
            DATEDIFF(hour, RequestDate, ApprovalDate) AS SoGioDuyet,
            Reason AS LyDoChi,
            Amount AS SoTien
        FROM [CRM_STDD].[dbo].[EXPENSE_REQUEST]
        WHERE YEAR(ApprovalDate) = @Year 
          AND MONTH(ApprovalDate) = @Month
          -- Lọc theo người duyệt cuối (thường là Kế toán trưởng hoặc người được giao)
          AND (CurrentApprover = @UserCode OR @UserCode = 'ADMIN')
          AND Status = 'APPROVED'
        ORDER BY SoGioDuyet DESC;
    END

END

GO
