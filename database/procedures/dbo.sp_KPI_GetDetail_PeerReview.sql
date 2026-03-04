
-- =============================================
-- Author:      Gemini / Sếp
-- Create date: 2026-02-26
-- Description: Lấy chi tiết thống kê đánh giá chéo cho Modal Detail
-- =============================================
CREATE PROCEDURE [dbo].[sp_KPI_GetDetail_PeerReview]
    @CriteriaID VARCHAR(50),
    @UserCode VARCHAR(50),
    @Year INT,
    @Month INT
AS
BEGIN
    SET NOCOUNT ON;

    -- Kiểm tra nếu đúng là tiêu chí Đánh giá phối hợp
    IF @CriteriaID = 'KPI_MAN_01'
    BEGIN
        SELECT 
            Score AS ReviewScore,               -- Mức điểm chấm (1-10)
            COUNT(EvaluatorUser) AS CountReviewer -- Số lượng người chấm mức điểm đó
        FROM 
            dbo.KPI_PEER_REVIEW
        WHERE 
            TargetUser = @UserCode 
            AND EvalYear = @Year 
            AND EvalMonth = @Month
        GROUP BY 
            Score
        ORDER BY 
            Score DESC; -- Sắp xếp từ điểm cao xuống thấp
    END
    ELSE
    BEGIN
        -- Trường hợp dự phòng nếu sau này có các loại đánh giá chéo khác
        SELECT 'N/A' AS ReviewScore, 0 AS CountReviewer WHERE 1=0;
    END
END

GO
