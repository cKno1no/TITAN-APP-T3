
CREATE PROCEDURE [dbo].[sp_KPI_GetDetail_System]
    @CriteriaID VARCHAR(50), @UserCode VARCHAR(50), @TranYear INT, @TranMonth INT
AS
BEGIN
    SET NOCOUNT ON;

    -- 1. Báo cáo CRM
    IF @CriteriaID = 'KPI_SYS_01'
    BEGIN
        SELECT 
            CONVERT(VARCHAR, [NGAY], 103) AS NgayNop,
            ISNULL([KHACH HANG], 'N/A') AS KhachHang,
            [Noi dung 1] AS NoiDung
        FROM [dbo].[HD_BAO CAO] WITH (NOLOCK)
        WHERE YEAR([NGAY]) = @TranYear AND MONTH([NGAY]) = @TranMonth 
          AND [NGUOI] = @UserCode
        ORDER BY [NGAY] DESC;
    END

    -- 2. Kỷ luật Thực thi Task
    ELSE IF @CriteriaID = 'KPI_SYS_02'
    BEGIN
        SELECT 
            CONVERT(VARCHAR, [TaskDate], 103) AS NgayTask,
            [Title] AS TenTask,
            CASE WHEN [CapTren] IS NOT NULL OR [SupervisorCode] IS NOT NULL THEN N'Được giao (70%)' ELSE N'Tự lên KH (30%)' END AS LoaiTask,
            [Status] AS TrangThai
        FROM [dbo].[Task_Master] WITH (NOLOCK)
        WHERE [UserCode] = @UserCode AND YEAR([TaskDate]) = @TranYear AND MONTH([TaskDate]) = @TranMonth
        ORDER BY [TaskDate] DESC, LoaiTask DESC;
    END

    -- 3. Tinh thần Học tập (XP)
    ELSE IF @CriteriaID = 'KPI_SYS_03'
    BEGIN
        -- Bài học hoàn tất
        ;WITH LessonCompleted AS (
            SELECT P.MaterialID
            FROM dbo.TRAINING_USER_PROGRESS P WITH (NOLOCK)
            WHERE P.UserCode = @UserCode
              AND P.Status = 'COMPLETED'
              AND YEAR(ISNULL(P.LastInteraction, P.LastAccessDate)) = @TranYear
              AND MONTH(ISNULL(P.LastInteraction, P.LastAccessDate)) = @TranMonth
            GROUP BY P.MaterialID
        )
        SELECT 
            N'Bài học' AS Nguon,
            ISNULL(M.FileName, CONCAT('Material #', L.MaterialID)) AS MoTa,
            1 AS SoLuong,
            25 AS XP
        FROM LessonCompleted L
        LEFT JOIN dbo.TRAINING_MATERIALS M WITH (NOLOCK) ON L.MaterialID = M.MaterialID
        
        UNION ALL
        
        -- Khóa học hoàn tất (tính mỗi khóa 1 dòng, XP sẽ áp dụng cap 2 khóa/tháng ở logic KPI tổng)
        SELECT 
            N'Khóa học' AS Nguon,
            C.Title AS MoTa,
            1 AS SoLuong,
            100 AS XP
        FROM (
            SELECT 
                C.CourseID,
                MAX(ISNULL(P.LastInteraction, P.LastAccessDate)) AS MaxInteraction,
                MIN(CASE WHEN P.Status = 'COMPLETED' THEN 1 ELSE 0 END) AS AllCompletedFlag
            FROM dbo.TRAINING_MATERIALS M WITH (NOLOCK)
            INNER JOIN dbo.TRAINING_COURSES C WITH (NOLOCK) ON M.CourseID = C.CourseID
            LEFT JOIN dbo.TRAINING_USER_PROGRESS P WITH (NOLOCK) 
                ON M.MaterialID = P.MaterialID AND P.UserCode = @UserCode
            GROUP BY C.CourseID
        ) CP
        INNER JOIN dbo.TRAINING_COURSES C WITH (NOLOCK) ON CP.CourseID = C.CourseID
        WHERE CP.AllCompletedFlag = 1 
          AND YEAR(CP.MaxInteraction) = @TranYear 
          AND MONTH(CP.MaxInteraction) = @TranMonth
        
        UNION ALL
        
        -- Daily Challenge thắng
        SELECT 
            N'Daily Challenge' AS Nguon,
            CONVERT(VARCHAR, S.BatchTime, 103) AS MoTa,
            1 AS SoLuong,
            15 AS XP
        FROM dbo.TRAINING_DAILY_SESSION S WITH (NOLOCK)
        WHERE S.UserCode = @UserCode
          AND S.Status = 'COMPLETED'
          AND ISNULL(S.IsCorrect, 0) = 1
          AND YEAR(S.BatchTime) = @TranYear
          AND MONTH(S.BatchTime) = @TranMonth
        ORDER BY Nguon, MoTa;
    END
END;

GO
