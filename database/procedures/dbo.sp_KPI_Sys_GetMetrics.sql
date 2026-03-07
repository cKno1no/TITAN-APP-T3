
CREATE PROCEDURE [dbo].[sp_KPI_Sys_GetMetrics]
    @TranYear INT, 
    @TranMonth INT, 
    @UserCode VARCHAR(50)
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @CRM_Report_Count INT = 0;
    DECLARE @Task_Score FLOAT = 0;
    DECLARE @Lesson_XP INT = 0;
    DECLARE @Course_XP INT = 0;
    DECLARE @CompletedCourses INT = 0;
    DECLARE @Daily_XP INT = 0;
    DECLARE @Gamification_XP INT = 0;
    
    -- =====================================================================
    -- 1. KỶ LUẬT BÁO CÁO CRM (Đếm số lượng báo cáo tạo trên Titan OS)
    -- =====================================================================
    SELECT @CRM_Report_Count = COUNT(*)
    FROM [dbo].[HD_BAO CAO] WITH (NOLOCK)
    WHERE YEAR([NGAY]) = @TranYear AND MONTH([NGAY]) = @TranMonth 
      AND [nguoi] = @UserCode;

    -- =====================================================================
    -- 2. KỶ LUẬT THỰC THI TASK (Tách 70% Task Giao & 30% Task Tự lập)
    -- =====================================================================
    DECLARE @Assigned_Total INT = 0, @Assigned_Done INT = 0;
    DECLARE @Self_Total INT = 0;
    DECLARE @Expected_Self_Tasks INT = 22 * 7; -- 22 ngày công * 7 task/ngày = 154 tasks

    -- A. Đếm Task được cấp trên giao (Đảm bảo có CapTren hoặc SupervisorCode)
    SELECT 
        @Assigned_Total = COUNT(*),
        @Assigned_Done = SUM(CASE WHEN [Status] = 'Completed' THEN 1 ELSE 0 END)
    FROM [dbo].[Task_Master] WITH (NOLOCK)
    WHERE [UserCode] = @UserCode 
      AND YEAR([TaskDate]) = @TranYear AND MONTH([TaskDate]) = @TranMonth
      AND ([CapTren] IS NOT NULL OR [SupervisorCode] IS NOT NULL);

    -- B. Đếm Task nhân viên tự tạo kế hoạch
    SELECT @Self_Total = COUNT(*)
    FROM [dbo].[Task_Master] WITH (NOLOCK)
    WHERE [UserCode] = @UserCode 
      AND YEAR([TaskDate]) = @TranYear AND MONTH([TaskDate]) = @TranMonth
      AND [CapTren] IS NULL AND [SupervisorCode] IS NULL;

    -- C. Logic Tính Điểm 70 / 30
    DECLARE @Score_70 FLOAT = 70; -- Tự động đạt full 70 điểm nếu sếp không giao task nào
    IF @Assigned_Total > 0 
        SET @Score_70 = (@Assigned_Done * 1.0 / @Assigned_Total) * 70;

    DECLARE @Score_30 FLOAT = (@Self_Total * 1.0 / @Expected_Self_Tasks) * 30;
    IF @Score_30 > 30 
        SET @Score_30 = 30; -- Capping: Dù tạo nhiều hơn 154 task thì phần này cũng chỉ tối đa 30 điểm

    -- Tổng điểm Task
    SET @Task_Score = @Score_70 + @Score_30;

    -- =====================================================================
    -- 3. TINH THẦN HỌC TẬP (Gamification XP từ Titan OS)
    --     - Mỗi bài học (Material) hoàn tất trong tháng: +25 XP
    --     - Mỗi khóa học hoàn tất trong tháng: +100 XP
    --     - Mỗi câu trả lời đúng thử thách Daily Challenge: +15 XP
    -- =====================================================================

    -- 3.1. BÀI HỌC HOÀN TẤT (TRAINING_USER_PROGRESS)
    ;WITH LessonCompleted AS (
        SELECT P.MaterialID
        FROM dbo.TRAINING_USER_PROGRESS P WITH (NOLOCK)
        WHERE P.UserCode = @UserCode
          AND P.Status = 'COMPLETED'
          AND YEAR(ISNULL(P.LastInteraction, P.LastAccessDate)) = @TranYear
          AND MONTH(ISNULL(P.LastInteraction, P.LastAccessDate)) = @TranMonth
        GROUP BY P.MaterialID
    )
    SELECT @Lesson_XP = ISNULL(COUNT(*), 0) * 25
    FROM LessonCompleted;

    -- 3.2. KHÓA HỌC HOÀN TẤT (TẤT CẢ MATERIAL CỦA KHÓA ĐỀU COMPLETED)
    ;WITH CourseProgress AS (
        SELECT 
            C.CourseID,
            MAX(ISNULL(P.LastInteraction, P.LastAccessDate)) AS MaxInteraction,
            MIN(CASE WHEN P.Status = 'COMPLETED' THEN 1 ELSE 0 END) AS AllCompletedFlag
        FROM dbo.TRAINING_MATERIALS M WITH (NOLOCK)
        INNER JOIN dbo.TRAINING_COURSES C WITH (NOLOCK) ON M.CourseID = C.CourseID
        LEFT JOIN dbo.TRAINING_USER_PROGRESS P WITH (NOLOCK) 
            ON M.MaterialID = P.MaterialID AND P.UserCode = @UserCode
        GROUP BY C.CourseID
    )
    SELECT @CompletedCourses = ISNULL(SUM(
                    CASE 
                        WHEN AllCompletedFlag = 1 
                             AND YEAR(MaxInteraction) = @TranYear 
                             AND MONTH(MaxInteraction) = @TranMonth 
                        THEN 1 ELSE 0 
                    END
                ), 0)
    FROM CourseProgress;

    IF @CompletedCourses > 2 SET @CompletedCourses = 2;
    SET @Course_XP = @CompletedCourses * 100;

    -- 3.3. DAILY CHALLENGE (TRẢ LỜI ĐÚNG)
    SELECT @Daily_XP = ISNULL(COUNT(*), 0) * 15
    FROM dbo.TRAINING_DAILY_SESSION S WITH (NOLOCK)
    WHERE S.UserCode = @UserCode
      AND S.Status = 'COMPLETED'
      AND ISNULL(S.IsCorrect, 0) = 1
      AND YEAR(S.BatchTime) = @TranYear
      AND MONTH(S.BatchTime) = @TranMonth;

    SET @Gamification_XP = ISNULL(@Lesson_XP, 0) + ISNULL(@Course_XP, 0) + ISNULL(@Daily_XP, 0);

    -- ==============================================================================
    -- XUẤT KẾT QUẢ ĐỂ PYTHON BẮT LẤY
    -- ==============================================================================
    SELECT 
        ISNULL(@CRM_Report_Count, 0) AS CRM_Report_Count,
        ISNULL(@Task_Score, 0) AS Task_Completion_Rate,
        ISNULL(@Gamification_XP, 0) AS Gamification_XP;
END;

GO
