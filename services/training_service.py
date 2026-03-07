import random
import re
import difflib
import json
import os
import PyPDF2
from datetime import datetime, timedelta
import google.generativeai as genai
from flask import current_app, session
import urllib.parse

class TrainingService:
    def __init__(self, db_manager, gamification_service):
        self.db = db_manager
        self.gamification = gamification_service
        self.ACTIVITY_CODE_WIN = 'DAILY_QUIZ_WIN'
        self.ai_model_name = 'gemini-2.5-flash'
    # =========================================================================
    # PHẦN 1: GAME & DAILY CHALLENGE
    # =========================================================================
    
    # 1. TÌM KIẾM KIẾN THỨC (Cho Chatbot)
    def search_knowledge(self, query):
        if not query: return None

        # [BỔ SUNG AUDIT LOG]
        user_code = session.get('user_code', 'GUEST')
        self.db.write_audit_log(
            user_code, 'TRAINING_KNOWLEDGE_SEARCH', 'INFO', 
            f"Tìm kiếm kiến thức: {query[:100]}", 
            current_app.config.get('SERVER_IP', '127.0.0.1')
        )

        stop_words = {'là', 'gì', 'của', 'hãy', 'nêu', 'cho', 'biết', 'trong', 'với', 'tại', 'sao', 'như', 'thế', 'nào', 'em', 'anh', 'chị', 'ad', 'bot', 'bạn', 'tôi', 'mình'}
        clean_query = query.lower()
        for char in "?!,.:;\"'()[]{}":
            clean_query = clean_query.replace(char, " ")
        raw_words = clean_query.split()
        keywords = [w for w in raw_words if len(w) > 1 and w not in stop_words]
        if not keywords: return None 

        top_kws = sorted(keywords, key=len, reverse=True)[:4]
        conditions = []
        params = []
        for kw in top_kws:
            conditions.append("Content LIKE ?")
            params.append(f"%{kw}%")
        if not conditions: return None

        sql = f"SELECT TOP 50 ID, Content, CorrectAnswer, Explanation FROM TRAINING_QUESTION_BANK WHERE CorrectAnswer IS NOT NULL AND ({' OR '.join(conditions)})"
        candidates = self.db.get_data(sql, tuple(params))
        if not candidates: return "⚠️ Không tìm thấy kiến thức nào khớp."

        scored_candidates = []
        user_tokens = set(keywords)
        for row in candidates:
            db_content = row['Content'].lower()
            matches = sum(1 for token in user_tokens if token in db_content)
            overlap_score = matches / len(user_tokens)
            scored_candidates.append((overlap_score, row))

        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        if not scored_candidates: return None
        best_score, best_row = scored_candidates[0]
        
        if best_score >= 0.7: return self._format_answer(best_row)
        top_suggestions = [item for item in scored_candidates[:3] if item[0] >= 0.3]
        if not top_suggestions: return "⚠️ Không tìm thấy câu hỏi nào đủ khớp."
        if len(top_suggestions) == 1: return self._format_answer(top_suggestions[0][1])

        msg = f"🤔 **Có phải ý Sếp là:**\n\n"
        for idx, (score, row) in enumerate(top_suggestions):
            msg += f"**{idx+1}.** {row['Content']}\n"
        return msg

    def _format_answer(self, row):
        ans_clean = row['CorrectAnswer'].replace('[', '').replace(']', '')
        explanation = f"\n\n💡 *Giải thích: {row['Explanation']}*" if row['Explanation'] else ""
        return f"📚 **Kiến thức:**\n**Q:** _{row['Content']}_\n\n{ans_clean}{explanation}"

    # =========================================================================
    # 2. PHÂN PHỐI CÂU HỎI (Cho Scheduler chạy định kỳ)
    # =========================================================================
    def distribute_daily_questions(self):
        # Lấy 3 câu hỏi ngẫu nhiên
        sql_q = """
            SELECT TOP 3 Q.ID, Q.Content, Q.OptionA, Q.OptionB, Q.OptionC, Q.OptionD, Q.OptionE, Q.OptionF 
            FROM TRAINING_QUESTION_BANK Q
            LEFT JOIN TRAINING_MATERIALS M ON Q.SourceMaterialID = M.MaterialID
            LEFT JOIN TRAINING_COURSES C ON M.CourseID = C.CourseID
            WHERE Q.CorrectAnswer IS NOT NULL 
              AND Q.IsActive = 1
              AND (
                -- Trường hợp 1: Là Assessment thì phải thuộc khóa học bắt buộc
                (Q.Category = 'Assessment' AND C.IsMandatory = -1)
                OR 
                -- Trường hợp 2: Các loại câu hỏi khác (Kiến thức chung, đố vui...) lấy bình thường
                (Q.Category != 'Assessment' OR Q.Category IS NULL)
              )
            ORDER BY NEWID()
        """
        questions = self.db.get_data(sql_q)
        if not questions: return []

        # [ĐÃ FIX]: Lọc danh sách user active (STDD, có bộ phận, khác Du học)
        sql_u = """
            SELECT UserCode 
            FROM [GD - NGUOI DUNG] 
            WHERE Division = 'STDD' 
              AND [BO PHAN] IS NOT NULL 
              AND LTRIM(RTRIM([BO PHAN])) != '9. DU HOC'
        """ 
        users_data = self.db.get_data(sql_u)
        users = [u['UserCode'] for u in users_data]
        if not users: return []

        random.shuffle(users)
        chunk_size = len(users) // len(questions) + 1
        user_groups = [users[i:i + chunk_size] for i in range(0, len(users), chunk_size)]
        messages_to_send = []

        for idx, group in enumerate(user_groups):
            if idx >= len(questions): break
            q_id = questions[idx]['ID']
            mail_title = f"💡 Cơ hội nâng tầm tri thức lúc {datetime.now().strftime('%H:%M')}"
            mail_content = f"""
<div class='p-2 text-center'>
    <p class='mb-3'>Một thử thách tri thức mới vừa xuất hiện. Sếp đã sẵn sàng cập nhật bản thân?</p>
    <a href='/training/daily-challenge' 
       class='btn btn-lg w-100 fw-bold shadow-lg rounded-pill animate__animated animate__pulse animate__infinite' 
       style='background: linear-gradient(45deg, #FF512F 0%, #DD2476 100%); color: white; border: none;'>
       🚀 TIẾN VÀO THỬ THÁCH
    </a>
</div>
"""
            expired_at = datetime.now() + timedelta(minutes=45)
            conn = None
            try:
                conn = self.db.get_transaction_connection()
                cursor = conn.cursor()
                placeholders = ','.join(['?'] * len(group))
                cursor.execute(f"UPDATE TRAINING_DAILY_SESSION SET Status='EXPIRED' WHERE UserCode IN ({placeholders}) AND Status='PENDING'", group)
                cursor.executemany("""
                    INSERT INTO TRAINING_DAILY_SESSION 
                    (UserCode, QuestionID, Status, ExpiredAt, BatchTime) 
                    VALUES (?, ?, 'PENDING', ?, GETDATE())
                """, [(user_code, q_id, expired_at) for user_code in group])
                cursor.executemany("INSERT INTO TitanOS_Game_Mailbox (UserCode, Title, Content, CreatedTime, IsClaimed) VALUES (?, ?, ?, GETDATE(), 0)", [(user_code, mail_title, mail_content) for user_code in group])
                conn.commit()
            except Exception:
                if conn: conn.rollback()
                raise
            finally:
                if conn: conn.close()
            for user_code in group:
                messages_to_send.append({"user_code": user_code})
                
        return messages_to_send

    # =========================================================================
    # 3. LẤY TRẠNG THÁI CHALLENGE (Cho Frontend hiển thị)
    # =========================================================================
    def get_current_challenge_status(self, user_code):
        now = datetime.now()

        # 1. TRUY VẤN LẤY PHIÊN MỚI NHẤT TRONG NGÀY
        try:
            sql_latest = """
                SELECT TOP 1 
                    S.SessionID, S.QuestionID, S.Status, S.ExpiredAt, S.AIScore, S.AIFeedback, S.UserAnswerContent, S.EarnedXP,
                    Q.Content as QuestionContent, Q.CorrectAnswer, Q.Explanation, Q.QuestionCode, -- THÊM CỘT NÀY
                    Q.OptionA, Q.OptionB, Q.OptionC, Q.OptionD, Q.OptionE, Q.OptionF
                FROM TRAINING_DAILY_SESSION S
                JOIN TRAINING_QUESTION_BANK Q ON S.QuestionID = Q.ID
                WHERE S.UserCode = ? 
                AND CAST(S.BatchTime AS DATE) = CAST(GETDATE() AS DATE)
                ORDER BY S.SessionID DESC
            """
            latest = self.db.get_data(sql_latest, (user_code,))
            has_earned_xp = True
        except Exception:
            # Fallback nếu DB chưa cập nhật đầy đủ cột
            sql_latest = """
                SELECT TOP 1 
                    S.SessionID, S.QuestionID, S.Status, S.ExpiredAt, S.AIScore, S.AIFeedback, S.UserAnswerContent, S.EarnedXP,
                    Q.Content as QuestionContent, Q.CorrectAnswer, Q.Explanation, Q.QuestionCode, -- THÊM CỘT NÀY
                    Q.OptionA, Q.OptionB, Q.OptionC, Q.OptionD, Q.OptionE, Q.OptionF
                FROM TRAINING_DAILY_SESSION S
                JOIN TRAINING_QUESTION_BANK Q ON S.QuestionID = Q.ID
                WHERE S.UserCode = ? 
                AND CAST(S.BatchTime AS DATE) = CAST(GETDATE() AS DATE)
                ORDER BY S.SessionID DESC
            """
            latest = self.db.get_data(sql_latest, (user_code,))
            has_earned_xp = False

        # 2. XỬ LÝ LOGIC TRẠNG THÁI
        if latest:
            row = latest[0]
            current_status = row['Status']

            # --- LOGIC GỘP NỘI DUNG CÂU HỎI VÀ CÁC Ý NHỎ (OPTION A-F) ---
            full_content = row['QuestionContent']
            options_text = ""
            # Duyệt qua các cột Option để kiểm tra dữ liệu bổ trợ
            for char in ['A', 'B', 'C', 'D', 'E', 'F']:
                col_name = f"Option{char}"
                if row.get(col_name) and str(row[col_name]).strip():
                    options_text += f"\n- {char}: {row[col_name]}"
            
            if options_text:
                full_content += "\n\n**Các ý bổ trợ/Lựa chọn:**" + options_text

            # Ảnh lưu tại: D:\CRM STDD\static\images\N3H\{ID}.jpg
            # URL web sẽ là: /static/images/N3H/{ID}.jpg
            # --- ĐOẠN SỬA LẠI TRONG get_current_challenge_status ---
            # Lấy QuestionCode từ row (SQL của sếp đã có SELECT Q.* nên sẽ có QuestionCode)
            question_code = row.get('QuestionCode') 
            image_filename = f"{question_code}.jpg" if question_code else f"{row['QuestionID']}.jpg"

            image_path = os.path.join(current_app.root_path, 'static', 'images', 'N3H', image_filename)

            # Trả về URL nếu file tồn tại
            if os.path.exists(image_path):
                image_url = f"/static/images/N3H/{image_filename}"
            else:
                # Backup: Nếu không tìm thấy theo Code, thử tìm theo ID
                backup_filename = f"{row['QuestionID']}.jpg"
                backup_path = os.path.join(current_app.root_path, 'static', 'images', 'N3H', backup_filename)
                image_url = f"/static/images/N3H/{backup_filename}" if os.path.exists(backup_path) else None
            # A. Đã hoàn thành (Chấm điểm xong)
            if current_status == 'COMPLETED':
                return {
                    'status': 'DONE',
                    'question': {'Content': full_content, 'Image': image_url}, # Trả thêm Image
                    'user_answer': row['UserAnswerContent'],
                    'score': row['AIScore'], 
                    'feedback': row['AIFeedback'],
                    'correct_answer': row['CorrectAnswer'],
                    'explanation': row['Explanation'],
                    'earned_xp': row.get('EarnedXP', 0) if has_earned_xp else 0
                }

            # B. Đã nộp (Chờ AI quét chấm lúc 9:30, 14:30, 17:45)
            elif current_status == 'SUBMITTED':
                 return {
                     'status': 'SUBMITTED',
                     'question': {'Content': full_content, 'Image': image_url},
                     'user_answer': row['UserAnswerContent']
                 }

            # C. Đang diễn ra (Sẵn sàng làm bài)
            elif current_status == 'PENDING':
                if row['ExpiredAt'] > now:
                    # [QUAN TRỌNG]: Ép cứng 15 phút (900s) cho user khi mở trang
                    return {
                        'status': 'AVAILABLE',
                        'session_id': row['SessionID'],
                        'question': {
                            'ID': row['QuestionID'],
                            'Content': full_content,
                            'Image': image_url
                        },
                        'seconds_left': 900,
                        'next_slot': "" # Placeholder
                    }
                else:
                    # Tự động đóng phiên nếu quá 45 phút chưa làm
                    self.db.execute_non_query("UPDATE TRAINING_DAILY_SESSION SET Status='EXPIRED' WHERE SessionID=?", (row['SessionID'],))

        # 3. TRẠNG THÁI CHỜ PHIÊN TIẾP THEO (CẬP NHẬT MỐC GIỜ MỚI)
        current_time_str = now.strftime("%H:%M")
        if current_time_str < "08:30":
            next_slot = "08:30"
        elif current_time_str < "13:30":
            next_slot = "13:30"
        elif current_time_str < "16:45":
            next_slot = "16:45"
        else:
            next_slot = "08:30 (Sáng mai)"

        return {'status': 'WAITING', 'next_slot': next_slot}
    
    def submit_answer(self, user_code, session_id, user_answer):
        """Hàm ghi nhận câu trả lời và chuyển sang trạng thái chờ AI chấm."""
        try:
            # 1. Kiểm tra phiên và thời gian hết hạn
            sql_check = "SELECT ExpiredAt, Status FROM TRAINING_DAILY_SESSION WHERE SessionID = ? AND UserCode = ?"
            session_data = self.db.get_data(sql_check, (session_id, user_code))
            
            if not session_data:
                return {'success': False, 'msg': 'Phiên không hợp lệ.'}
            
            # Nếu đã quá hạn 15 phút
            if session_data[0]['ExpiredAt'] < datetime.now():
                self.db.execute_non_query("UPDATE TRAINING_DAILY_SESSION SET Status='EXPIRED' WHERE SessionID=?", (session_id,))
                return {'success': False, 'msg': 'Rất tiếc, thời gian làm bài (10 phút) đã kết thúc!'}

            if session_data[0]['Status'] in ['SUBMITTED', 'COMPLETED']:
                return {'success': False, 'msg': 'Bạn đã nộp bài này rồi.'}

            # 2. Cập nhật câu trả lời và chuyển trạng thái chờ chấm
            # Ghi nhận UserAnswerContent và set Status='SUBMITTED'
            sql_update = """
                UPDATE TRAINING_DAILY_SESSION 
                SET Status='SUBMITTED', UserAnswerContent=?, SubmittedAt=GETDATE()
                WHERE SessionID=?
            """
            self.db.execute_non_query(sql_update, (user_answer, session_id))
            
            # [BỔ SUNG AUDIT LOG]
            self.db.write_audit_log(
                user_code, 'TRAINING_DAILY_SUBMIT', 'INFO', 
                f"Nộp bài Daily Challenge (Session: {session_id})", 
                current_app.config.get('SERVER_IP', '127.0.0.1')
            )

            return {
                'success': True, 
                'msg': 'Bài làm đã được ghi nhận. AI sẽ trả lời kết quả sau khi kết thúc thời gian thi (10 phút).'
            }
            
        except Exception as e:
            current_app.logger.error(f"Lỗi submit_answer: {e}")
            return {'success': False, 'msg': 'Lỗi hệ thống khi nộp bài.'}

    def get_daily_challenge_history(self, user_code, limit=20):
        """Lấy lịch sử tham gia Thử thách mỗi ngày (cho block Nhật ký hoạt động)."""
        try:
            sql = """
                SELECT TOP (?)
                    S.SessionID, S.BatchTime, S.Status, S.AIScore, S.EarnedXP,
                    LEFT(Q.Content, 80) AS QuestionPreview
                FROM TRAINING_DAILY_SESSION S
                LEFT JOIN TRAINING_QUESTION_BANK Q ON S.QuestionID = Q.ID
                WHERE S.UserCode = ?
                ORDER BY S.BatchTime DESC
            """
            rows = self.db.get_data(sql, (limit, user_code)) or []
            history = []
            for r in rows:
                batch_time = r.get('BatchTime')
                if hasattr(batch_time, 'strftime'):
                    batch_str = batch_time.strftime('%d/%m/%Y %H:%M')
                else:
                    batch_str = str(batch_time) if batch_time else '--'
                history.append({
                    'session_id': r.get('SessionID'),
                    'batch_time': batch_str,
                    'status': r.get('Status') or '--',
                    'score': r.get('AIScore'),
                    'earned_xp': r.get('EarnedXP', 0),
                    'question_preview': (r.get('QuestionPreview') or '')[:80],
                })
            return history
        except Exception as e:
            current_app.logger.warning(f"get_daily_challenge_history: {e}")
            return []

    # 5. HÀM PHỤ TRỢ AI CHẤM
    def _ai_grade_answer(self, question, standard, user_ans):
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            prompt = f"""
            Chấm điểm tự luận (0-10) và nhận xét ngắn.
            Câu hỏi: {question}
            Đáp án chuẩn: {standard}
            User trả lời: {user_ans}
            Output JSON: {{ "score": number, "feedback": "string" }}
            """
            res = model.generate_content(prompt)
            return json.loads(res.text.replace('```json', '').replace('```', '').strip())
        except Exception:
            return {"score": 5, "feedback": "Hệ thống bận, chấm điểm khuyến khích."}

    # 6. LẤY CHALLENGE CHO CHATBOT (Legacy)
    def get_pending_challenge(self, user_code):
        status = self.get_current_challenge_status(user_code)
        if status['status'] == 'AVAILABLE':
            return f"🔥 **THỬ THÁCH ĐANG CHỜ**\n{status['question']}\n\n👉 Vào 'Đấu Trường' để chiến ngay!"
        return None

    # =========================================================================
    # PHẦN 2: DASHBOARD & COURSE (LOGIC MỚI)
    # =========================================================================

    # 7. LẤY DASHBOARD THEO CATEGORY (V2)
    def get_training_dashboard_v2(self, user_code):
        # 1. Cố gắng lấy dữ liệu cấu trúc MỚI (Có SubCategory)
        # [FIX] Thêm cột C.IsMandatory vào Query
        sql = """
            SELECT 
                C.CourseID, C.Title, C.Description, C.Category, C.ThumbnailUrl, C.XP_Reward,
                C.SubCategory, C.IsMandatory, -- Lấy thêm cột này
                COUNT(DISTINCT M.MaterialID) as TotalLessons, -- Thêm DISTINCT để tránh đếm trùng
                SUM(CASE WHEN P.Status = 'COMPLETED' THEN 1 ELSE 0 END) as CompletedLessons
            FROM TRAINING_COURSES C
            LEFT JOIN TRAINING_MATERIALS M ON C.CourseID = M.CourseID
            LEFT JOIN TRAINING_USER_PROGRESS P ON M.MaterialID = P.MaterialID AND P.UserCode = ?
            GROUP BY C.CourseID, C.Title, C.Description, C.Category, C.ThumbnailUrl, C.XP_Reward, C.SubCategory, C.IsMandatory
        """
        
        try:
            rows = self.db.get_data(sql, (user_code,))
        except Exception as e:
            print(f"Warning: Đang dùng Query dự phòng do lỗi DB: {e}")
            # 2. Fallback: Nếu lỗi (do chưa chạy SQL update DB), dùng Query CŨ
            sql_fallback = """
                SELECT 
                    C.CourseID, C.Title, C.Description, C.Category, C.ThumbnailUrl, C.XP_Reward,
                    COUNT(M.MaterialID) as TotalLessons,
                    SUM(CASE WHEN P.Status = 'COMPLETED' THEN 1 ELSE 0 END) as CompletedLessons
                FROM TRAINING_COURSES C
                LEFT JOIN TRAINING_MATERIALS M ON C.CourseID = M.CourseID
                LEFT JOIN TRAINING_USER_PROGRESS P ON M.MaterialID = P.MaterialID AND P.UserCode = ?
                GROUP BY C.CourseID, C.Title, C.Description, C.Category, C.ThumbnailUrl, C.XP_Reward
            """
            rows = self.db.get_data(sql_fallback, (user_code,))

        grouped = {}
        def_img = 'https://cdn3d.iconscout.com/3d/premium/thumb/folder-5206733-4352249.png'

        # Từ khóa để tự động phân loại nếu DB chưa có dữ liệu chuẩn
        keywords_map = {
            'Vòng bi & Truyền động': ['vòng bi', 'bạc đạn', 'bôi trơn', 'truyền động', 'skf', 'timken'],
            'Hệ thống Cơ khí': ['bơm', 'quạt', 'thủy lực', 'đường ống', 'băng tải', 'khí nén'],
            'Bảo trì & MRO': ['mro', 'bảo trì', 'sửa chữa', 'vận hành', 'cmms'],
            'Công nghệ 4.0': ['số hóa', 'iot', '4.0', 'thông minh', 'phần mềm', 'condasset'],
            'Kinh doanh & Chiến lược': ['bán hàng', 'khách hàng', 'thị trường', 'chiến lược', 'doanh số'],
            'Kỹ năng & Văn hóa': ['lãnh đạo', 'giao tiếp', 'tư duy', 'văn hóa', 'nhân viên mới']
        }

        for r in rows:
            # [AN TOÀN] Dùng .get() để tránh lỗi KeyError nếu cột không tồn tại
            cat_raw = r.get('Category') or 'Khác'
            cat = cat_raw.strip().replace('[', '').replace(']', '').replace('1.', '').replace('5.', '').strip()
            
            if cat not in grouped: grouped[cat] = {}

            # [AN TOÀN] Kiểm tra xem cột SubCategory có tồn tại trong row không
            sub_cat = 'Chung'
            db_sub = r.get('SubCategory') # Lấy giá trị an toàn
            
            if db_sub and str(db_sub).strip():
                sub_cat = str(db_sub).strip()
            else:
                # Logic tự động phân loại bằng từ khóa (Auto-tagging)
                title_lower = r['Title'].lower()
                for key, kws in keywords_map.items():
                    if any(w in title_lower for w in kws):
                        sub_cat = key
                        break
            
            if sub_cat not in grouped[cat]: grouped[cat][sub_cat] = []

            # Tính toán tiến độ
            total = r['TotalLessons'] or 0
            done = r['CompletedLessons'] or 0
            percent = int((done / total) * 100) if total > 0 else 0
            
            is_mandatory_val = r.get('IsMandatory', 0)
            is_mandatory = True if is_mandatory_val == 1 or is_mandatory_val == -1 else False

            course = {
                'id': r['CourseID'],
                'title': r['Title'],
                'desc': r.get('Description', 'Chưa có mô tả.'),
                'thumbnail': r.get('ThumbnailUrl') or def_img,
                'xp': r.get('XP_Reward', 0),
                'lessons': total,
                'is_mandatory': is_mandatory,  # Truyền flag này ra API
                'progress': percent,
                'sub_cat_display': sub_cat
            }
            grouped[cat][sub_cat].append(course)
            
        return grouped
    
    def search_courses_and_materials(self, query):
        term = f"%{query}%"
        sql = """
            SELECT DISTINCT TOP 10 C.CourseID, C.Title, C.Category, C.ThumbnailUrl
            FROM TRAINING_COURSES C
            LEFT JOIN TRAINING_MATERIALS M ON C.CourseID = M.CourseID
            WHERE C.Title LIKE ? OR C.Description LIKE ? OR M.FileName LIKE ? OR M.Summary LIKE ?
        """
        rows = self.db.get_data(sql, (term, term, term, term))

        results = []
        for r in rows:
            results.append({
                'id': r['CourseID'],
                'title': r['Title'],
                'category': r['Category'],
                'thumbnail': r['ThumbnailUrl']
            })
        return results
    
    # 8. LẤY CHI TIẾT KHÓA HỌC & BÀI HỌC
    def get_course_detail(self, course_id, user_code):
        # Info
        c_sql = "SELECT * FROM TRAINING_COURSES WHERE CourseID = ?"
        course = self.db.get_data(c_sql, (course_id,))
        if not course: return None
        
        # Materials List
        m_sql = """
            SELECT 
                M.MaterialID, M.FileName, M.TotalPages, M.Summary,
                ISNULL(P.Status, 'NOT_STARTED') as Status,
                ISNULL(P.LastPageRead, 0) as LastPage
            FROM TRAINING_MATERIALS M
            LEFT JOIN TRAINING_USER_PROGRESS P ON M.MaterialID = P.MaterialID AND P.UserCode = ?
            WHERE M.CourseID = ?
            ORDER BY M.MaterialID
        """
        materials = self.db.get_data(m_sql, (user_code, course_id))
        
        return {'info': course[0], 'materials': materials}

    # =========================================================================
    # PHẦN 3: HỌC TẬP & KIỂM TRA (STUDY & QUIZ)
    # =========================================================================

    # 9. LẤY NỘI DUNG BÀI HỌC (Study Room)
    def get_material_content(self, material_id, user_code):
        sql = "SELECT * FROM TRAINING_MATERIALS WHERE MaterialID = ?"
        data = self.db.get_data(sql, (material_id,))
        if not data: return None
        material = data[0]
        
        # [BỔ SUNG AUDIT LOG]
        self.db.write_audit_log(
            user_code, 'TRAINING_STUDY_START', 'INFO', 
            f"Bắt đầu học bài: {material.get('FileName')} (ID: {material_id})", 
            current_app.config.get('SERVER_IP', '127.0.0.1')
        )

        # Lấy tiến độ đọc
        prog = self.db.get_data("SELECT LastPageRead FROM TRAINING_USER_PROGRESS WHERE UserCode=? AND MaterialID=?", (user_code, material_id))
        material['last_page'] = prog[0]['LastPageRead'] if prog else 1
        
        # --- [FIX LỖI URL & KÝ TỰ ĐẶC BIỆT STD&D] ---
        raw_path = material.get('FilePath', '')
        if not raw_path:
            material['WebPath'] = ''
            return material

        # 1. Đồng bộ dấu chéo
        raw_path = raw_path.replace('\\', '/')
        
        # 2. Xử lý đường dẫn ảo (Web Path)
        if 'static' in raw_path:
            web_path = '/static' + raw_path.split('static')[1]
        elif 'attachments' in raw_path:
            web_path = '/attachments' + raw_path.split('attachments')[1]
        else:
            # Nếu trong DB chỉ lưu tên file (vd: Quy_trinh_STD&D.pdf)
            # Tự động gán vào thư mục attachments
            web_path = '/attachments/' + raw_path.split('/')[-1]

        # 3. Mã hóa ký tự đặc biệt (Rất quan trọng cho dấu cách và dấu '&')
        # Ví dụ: "STD&D.pdf" -> "STD%26D.pdf"
        parts = web_path.split('/')
        encoded_parts = [urllib.parse.quote(p) for p in parts]
        material['WebPath'] = '/'.join(encoded_parts)
            
        return material

    # =========================================================================
    # [NEW] KIỂM TRA GIỚI HẠN REQUEST API CHO PHÒNG HỌC
    # =========================================================================
    def _check_ai_rate_limit(self, user_code):
        from flask import session # Đảm bảo lấy được role
        user_role = session.get('user_role', '').strip().upper()
        
        base_limit = 20  
        bonus_per_level = 2
        
        if user_role == 'ADMIN':
            max_limit = base_limit * 100  
        else:
            try:
                stats = self.db.get_data("SELECT Level FROM TitanOS_UserStats WHERE UserCode = ?", (user_code,))
                level = int(stats[0]['Level']) if stats else 1
            except Exception:
                level = 1
            max_limit = base_limit + (level * bonus_per_level)

        redis_client = current_app.redis_client
        if not redis_client: return True, max_limit, 0 
            
        today_str = datetime.now().strftime('%Y%m%d')
        # Dùng chung key limit với Chatbot để tổng hợp số lượt dùng toàn hệ thống
        key = f"ai_limit:chatbot:{today_str}:{user_code}"
        
        try:
            current_usage = redis_client.get(key)
            current_usage = int(current_usage) if current_usage else 0
            
            if current_usage >= max_limit: return False, max_limit, current_usage
                
            pipe = redis_client.pipeline()
            pipe.incr(key)
            if current_usage == 0: pipe.expire(key, 86400)
            pipe.execute()
            
            return True, max_limit, current_usage + 1
        except Exception:
            return True, max_limit, 0

    # 10. AI TUTOR (Chatbot học tập)
    def chat_with_document(self, material_id, user_question):

        user_code = session.get('user_code')
        
        # --- [THÊM MỚI] CHECK RATE LIMIT ---
        is_allowed, max_limit, current_usage = self._check_ai_rate_limit(user_code)
        if not is_allowed:
            return {
                "text": f"⚡ Bạn đã dùng hết giới hạn AI hôm nay ({max_limit}/{max_limit} lượt). Hãy cày cấp để được tăng giới hạn vào ngày mai nhé!", 
                "page": None
            }
        # ------------------------------------
        sql = "SELECT FilePath FROM TRAINING_MATERIALS WHERE MaterialID = ?"
        data = self.db.get_data(sql, (material_id,))
        if not data: return {"text": "Tài liệu không tồn tại.", "page": None}
        
        raw_path = data[0]['FilePath'].replace('\\', '/')
        file_name = raw_path.split('/')[-1] # Lấy mỗi tên file
        
        # [FIX]: Dò tìm file vật lý ở 2 thư mục phổ biến nhất
        possible_paths = [
            os.path.join(current_app.config.get('UPLOAD_FOLDER', 'attachments'), file_name),
            os.path.join(current_app.root_path, 'static', 'materials', file_name),
            raw_path # Thử dùng đường dẫn thô trong DB nếu đó là đường dẫn tuyệt đối C:\...
        ]
        
        real_path = None
        for p in possible_paths:
            if os.path.exists(p):
                real_path = p
                break
                
        if not real_path:
             return {"text": f"Không tìm thấy file gốc trên Server: {file_name}", "page": None}

        # Live Read PDF
        pdf_text = ""
        try:
            reader = PyPDF2.PdfReader(real_path)
            for i, page in enumerate(reader.pages[:10]): # Đọc 10 trang đầu
                text = page.extract_text()
                if text: pdf_text += f"\n--- TRANG {i+1} ---\n{text}"
        except Exception as e:
            return {"text": f"Lỗi đọc PDF: {str(e)}", "page": None}

        if not pdf_text.strip():
            return {"text": "Tài liệu này là file ảnh scan, AI chưa đọc được chữ.", "page": None}

        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            prompt = f"Trả lời câu hỏi dựa trên tài liệu. Nếu thấy thông tin ở trang nào, ghi [[PAGE:số_trang]]. Câu hỏi: {user_question}. Dữ liệu: {pdf_text[:15000]}"
            res = model.generate_content(prompt)
            reply = res.text
            
            target_page = None
            match = re.search(r'\[\[PAGE:(\d+)\]\]', reply)
            if match:
                target_page = int(match.group(1))
                reply = reply.replace(match.group(0), f"(Xem trang {target_page})")
            return {"text": reply, "page": target_page}
        except Exception as e:
            return {"text": f"Lỗi AI: {e}", "page": None}

    # 11. CẬP NHẬT TRANG ĐANG ĐỌC
    def update_reading_progress(self, user_code, material_id, page_num):
        check = self.db.get_data("SELECT ProgressID FROM TRAINING_USER_PROGRESS WHERE UserCode=? AND MaterialID=?", (user_code, material_id))
        if check:
            self.db.execute_non_query("UPDATE TRAINING_USER_PROGRESS SET LastPageRead=?, LastAccessDate=GETDATE() WHERE UserCode=? AND MaterialID=?", (page_num, user_code, material_id))
        else:
            self.db.execute_non_query("INSERT INTO TRAINING_USER_PROGRESS (UserCode, MaterialID, Status, LastPageRead, LastAccessDate) VALUES (?, ?, 'IN_PROGRESS', ?, GETDATE())", (user_code, material_id, page_num))
        return True

    # 12. LẤY ĐỀ THI (CƠ CHẾ: GIỮ 4 CŨ - ĐỔI 1 MỚI)
    def get_material_quiz(self, material_id, user_code):
        # 1. Tìm xem user đã thi bài này lần nào chưa
        sql_history = """
            SELECT TOP 5 QuestionID 
            FROM TRAINING_QUIZ_SUBMISSIONS 
            WHERE UserCode = ? AND MaterialID = ?
            ORDER BY AttemptNumber DESC, SubmissionID ASC
        """
        last_questions = self.db.get_data(sql_history, (user_code, material_id))
        
        final_questions = []

        # TRƯỜNG HỢP 1: THI LẦN ĐẦU (Chưa có lịch sử) -> Lấy 5 câu ngẫu nhiên
        if not last_questions or len(last_questions) < 5:
            sql_random = """
                SELECT TOP 5 ID, Content, OptionA, OptionB, OptionC, OptionD 
                FROM TRAINING_QUESTION_BANK 
                WHERE SourceMaterialID = ? 
                ORDER BY NEWID()
            """
            final_questions = self.db.get_data(sql_random, (material_id,))
        
        # TRƯỜNG HỢP 2: THI LẠI (Đã có đề cũ) -> Giữ 4, Đổi 1
        else:
            old_ids = [row['QuestionID'] for row in last_questions]
            
            # Chọn ngẫu nhiên 4 câu từ đề cũ để giữ lại
            keep_ids = random.sample(old_ids, 4)
            
            # Lấy 1 câu MỚI TOANH (không nằm trong đề cũ)
            placeholders = ','.join(['?'] * len(old_ids))
            sql_new = f"""
                SELECT TOP 1 ID, Content, OptionA, OptionB, OptionC, OptionD 
                FROM TRAINING_QUESTION_BANK 
                WHERE SourceMaterialID = ? 
                AND ID NOT IN ({placeholders})
                ORDER BY NEWID()
            """
            params = [material_id] + old_ids
            new_question = self.db.get_data(sql_new, tuple(params))
            
            # Nếu hết câu hỏi mới trong kho -> Đành lấy lại 1 câu cũ còn lại
            if not new_question:
                missing_id = [x for x in old_ids if x not in keep_ids][0]
                sql_fallback = "SELECT ID, Content, OptionA, OptionB, OptionC, OptionD FROM TRAINING_QUESTION_BANK WHERE ID = ?"
                new_question = self.db.get_data(sql_fallback, (missing_id,))

            # Lấy thông tin chi tiết 4 câu giữ lại
            keep_placeholders = ','.join(['?'] * len(keep_ids))
            sql_keep = f"SELECT ID, Content, OptionA, OptionB, OptionC, OptionD FROM TRAINING_QUESTION_BANK WHERE ID IN ({keep_placeholders})"
            kept_questions = self.db.get_data(sql_keep, tuple(keep_ids))
            
            # Gộp lại thành 5 câu
            final_questions = kept_questions + new_question
            random.shuffle(final_questions) # Trộn thứ tự lại cho mới mẻ

        return final_questions

    # 13. NỘP BÀI (AI CHẤM KHẮT KHE + LƯU LỊCH SỬ NHIỀU LẦN)
    def submit_material_quiz(self, user_code, material_id, answers):
        score = 0
        total = len(answers)
        ai_feedback_summary = []
        
        if total == 0: return {'score': 0, 'passed': False}

        # 1. Xác định AttemptNumber (Lần thi thứ mấy)
        sql_att = "SELECT ISNULL(MAX(AttemptNumber), 0) as MaxAtt FROM TRAINING_QUIZ_SUBMISSIONS WHERE UserCode=? AND MaterialID=?"
        att_data = self.db.get_data(sql_att, (user_code, material_id))
        current_attempt = (att_data[0]['MaxAtt'] + 1) if att_data else 1

        for q_id, user_ans in answers.items():
            # Lấy đáp án chuẩn từ DB
            q_sql = "SELECT Content, OptionA, CorrectAnswer FROM TRAINING_QUESTION_BANK WHERE ID=?"
            q_data = self.db.get_data(q_sql, (q_id,))
            if not q_data: continue
            row = q_data[0]
            
            is_correct = 0
            feedback = ""
            
            # Phân loại câu hỏi
            is_mcq = row['OptionA'] and row['OptionA'].strip() != ""
            
            if is_mcq:
                # --- CHẤM TRẮC NGHIỆM ---
                correct_char = row['CorrectAnswer'].strip()[0].upper()
                user_char = user_ans.strip()[0].upper() if user_ans else ""
                if correct_char == user_char:
                    score += 1
                    is_correct = 1
            else:
                # --- CHẤM TỰ LUẬN (AI) ---
                # Gọi hàm AI chấm điểm (Logic mới: >= 70/100 là Đạt)
                ai_res = self._ai_grade_essay(row['Content'], row['CorrectAnswer'], user_ans)
                grade_percent = ai_res.get('score', 0) # Thang 100
                feedback = ai_res.get('feedback', '')
                
                # Logic: Đúng trên 70% nội dung -> Tính điểm
                if grade_percent >= 70:
                    score += 1
                    is_correct = 1
                else:
                    ai_feedback_summary.append(f"- Câu '{row['Content'][:30]}...': {feedback} (Độ khớp: {grade_percent}%)")

            # LƯU VÀO DB (Kèm AttemptNumber)
            self.db.execute_non_query("""
                INSERT INTO TRAINING_QUIZ_SUBMISSIONS 
                (UserCode, MaterialID, QuestionID, UserAnswer, IsCorrect, AIFeedback, AttemptNumber, SubmittedDate)
                VALUES (?, ?, ?, ?, ?, ?, ?, GETDATE())
            """, (user_code, material_id, q_id, user_ans, is_correct, feedback, current_attempt))

        # 2. Tính kết quả chung cuộc
        pass_rate = (score / total) * 100
        passed = pass_rate >= 80
        
        # 3. Cập nhật tiến độ (QUAN TRỌNG: Không làm mất trạng thái COMPLETED cũ)
        check = self.db.get_data("SELECT Status FROM TRAINING_USER_PROGRESS WHERE UserCode=? AND MaterialID=?", (user_code, material_id))
        
        new_status = 'COMPLETED' if passed else 'IN_PROGRESS'
        
        if check:
            old_status = check[0]['Status']
            # Chỉ update trạng thái nếu:
            # 1. Trước đó chưa xong (IN_PROGRESS) và giờ làm xong (COMPLETED)
            # 2. Hoặc giữ nguyên trạng thái cũ, chỉ update LastInteraction
            # TUYỆT ĐỐI KHÔNG downgrade từ COMPLETED về IN_PROGRESS
            final_status = 'COMPLETED' if old_status == 'COMPLETED' else new_status

            self.db.execute_non_query("""
                UPDATE TRAINING_USER_PROGRESS 
                SET Status = ?, LastInteraction = GETDATE() 
                WHERE UserCode=? AND MaterialID=?""", (final_status, user_code, material_id))
        else:
            self.db.execute_non_query("INSERT INTO TRAINING_USER_PROGRESS (UserCode, MaterialID, Status, LastPageRead, LastInteraction) VALUES (?, ?, ?, 1, GETDATE())", (user_code, material_id, new_status))
            
        feedback_msg = "<br>".join(ai_feedback_summary) if ai_feedback_summary else "Xuất sắc! Bạn nắm bài rất tốt."


        # [BỔ SUNG AUDIT LOG]
        log_msg = f"Nộp bài thi Material ID: {material_id}. Kết quả: {score}/{total} ({'ĐẠT' if passed else 'KHÔNG ĐẠT'}). Lần thi: {current_attempt}"
        self.db.write_audit_log(
            user_code, 'TRAINING_QUIZ_SUBMIT', 
            'SUCCESS' if passed else 'WARNING', 
            log_msg, 
            current_app.config.get('SERVER_IP', '127.0.0.1')
        )

        return {
            'score': score, 
            'total': total, 
            'passed': passed, 
            'attempt': current_attempt,
            'feedback': feedback_msg
        }
    
    # HÀM CHẤM TỰ LUẬN NÂNG CAO
    def _ai_grade_essay(self, question, standard_ans, user_ans):
        # Nếu user không trả lời -> 0 điểm ngay
        if not user_ans or len(user_ans.strip()) < 5:
            return {"score": 0, "feedback": "Chưa trả lời hoặc quá ngắn."}

        try:
            model = genai.GenerativeModel(self.ai_model_name)
            
            prompt = f"""
            Bạn là Giám khảo chấm thi Tự luận kỹ thuật.
            
            CÂU HỎI: {question}
            ĐÁP ÁN CHUẨN (Ý chính): {standard_ans}
            
            TRẢ LỜI CỦA HỌC VIÊN: "{user_ans}"
            
            NHIỆM VỤ:
            So sánh ý nghĩa (Semantic Matching) của câu trả lời học viên với đáp án chuẩn.
            - Không bắt bẻ chính tả.
            - Chú trọng vào các từ khóa kỹ thuật và logic.
            - Nếu trả lời lan man, sai trọng tâm -> Điểm thấp.
            - Nếu trả lời đúng ý nhưng khác văn phong -> Điểm cao.
            
            OUTPUT JSON (Bắt buộc):
            {{
                "score": 0-100,  // Điểm số (Interger)
                "feedback": "..." // Nhận xét ngắn gọn (dưới 15 từ) tại sao sai/đúng.
            }}
            """
            
            res = model.generate_content(prompt)
            text = res.text.replace('```json', '').replace('```', '').strip()
            return json.loads(text)
            
        except Exception as e:
            print(f"❌ Lỗi AI Grading: {e}")
            # [QUAN TRỌNG] Lỗi AI -> Trả về 0 điểm để tránh gian lận, yêu cầu user làm lại
            return {"score": 0, "feedback": "Lỗi kết nối AI chấm điểm. Vui lòng thử lại sau giây lát."}


    
    def process_pending_grading(self):
        """
        Quét và chấm điểm tự động cho các bài Daily Challenge.
        Sửa lỗi: Chuyển từ lọc AIScore sang AIFeedback IS NULL.
        Logic: Chấm ngay bài đã SUBMITTED, bài PENDING thì đợi Expired.
        """
        print(f"🤖 [AI Grading] Bắt đầu quét các bài nộp chưa chấm...")
        
        # SQL Cập nhật: Ưu tiên chấm bài đã bấm nộp (SUBMITTED) 
        # HOẶC bài mở rồi nhưng để hết hạn (PENDING + Expired)
        # Lọc theo AIFeedback IS NULL để tránh lỗi Default Value của AIScore
        sql_pending = """
            SELECT s.SessionID, s.UserCode, s.UserAnswerContent, 
                   q.Content as QuestionText, q.CorrectAnswer as StandardAnswer
            FROM TRAINING_DAILY_SESSION s
            JOIN TRAINING_QUESTION_BANK q ON s.QuestionID = q.ID
            WHERE (
                    s.Status = 'SUBMITTED' 
                    OR (s.Status = 'PENDING' AND s.ExpiredAt <= GETDATE())
                  )
              AND (s.AIFeedback IS NULL) 
        """
        
        try:
            pending_list = self.db.get_data(sql_pending)
            if not pending_list:
                print("✅ Không có bài nộp nào cần chấm.")
                return

            for row in pending_list:
                sid = row['SessionID']
                user_code = row['UserCode']
                user_ans = row['UserAnswerContent'] or ""
                question = row['QuestionText']
                standard_ans = row['StandardAnswer']

                try:
                    # Nếu nội dung quá ngắn -> Mặc định Sai
                    if len(str(user_ans).strip()) < 5:
                        score = 0
                        feedback = "Nội dung trả lời quá ngắn hoặc sếp chưa nhập bài làm."
                    else:
                        print(f"--- Đang chấm cho User: {user_code} (Session: {sid}) ---")
                        grade_result = self._ai_grade_essay(question, standard_ans, user_ans)
                        
                        # [FIX QUAN TRỌNG] NẾU AI LỖI (MẤT MẠNG, HẾT QUOTA, SAI KEY) -> BỎ QUA BÀI NÀY
                        if grade_result is None:
                            print(f"⚠️ Bỏ qua Session {sid} do lỗi AI. Sẽ chấm lại vào chu kỳ quét sau.")
                            continue 
                            
                        score = grade_result.get('score', 0)
                        feedback = grade_result.get('feedback', 'Đã chấm điểm tự động.')

                    # Phân định thưởng (20 XP nếu đúng, 5 XP nếu tham gia)
                    is_correct = 1 if score >= 50 else 0
                    xp_to_log = 20 if is_correct else 5
                    activity_code = 'DAILY_CHALLENGE_WIN' if is_correct else 'DAILY_CHALLENGE_PARTICIPATE'

                    # Cập nhật kết quả vào phiên thi
                    sql_update = """
                        UPDATE TRAINING_DAILY_SESSION 
                        SET AIScore = ?, AIFeedback = ?, Status = 'COMPLETED', IsCorrect = ?, EarnedXP = ?
                        WHERE SessionID = ?
                    """
                    self.db.execute_non_query(sql_update, (score, feedback, is_correct, xp_to_log, sid))

                    # [BỔ SUNG AUDIT LOG]
                    self.db.write_audit_log(
                        'SYSTEM_AI', 'TRAINING_AI_GRADED', 'SUCCESS', 
                        f"AI chấm bài cho {user_code}: {score}đ. Thưởng: {xp_to_log} XP. (Session: {sid})", 
                        "INTERNAL"
                    )
                    # Ghi log hoạt động để tổng kết XP cuối ngày (Lúc 20:00)
                    self.gamification.log_activity(user_code, activity_code)
                    
                    # Gửi thư báo kết quả (Không kèm XP trực tiếp)
                    title = "🎉 Kết quả Thử thách Daily" if is_correct else "📝 Phản hồi Thử thách Daily"
                    res_text = "ĐÚNG" if is_correct else "CHƯA CHÍNH XÁC"
                    msg = f"""
                        <div style='border-left: 4px solid { '#28a745' if is_correct else '#dc3545' }; padding: 10px 15px; background: #f8f9fa;'>
                            <p style='margin-bottom:5px;'>Kết quả: <b>{res_text} ({score}/100 điểm)</b></p>
                            <p style='margin-bottom:5px;'>Nhận xét từ AI: <i>{feedback}</i></p>
                            <p style='font-size: 12px; color: #666; margin-top: 10px;'>
                                * XP thưởng ({xp_to_log} XP) sẽ được hệ thống tổng kết và gửi vào thư tặng quà cuối ngày.
                            </p>
                        </div>
                    """
                    sql_mail = "INSERT INTO TitanOS_Game_Mailbox (UserCode, Title, Content, Total_XP, IsClaimed, CreatedTime) VALUES (?, ?, ?, 0, 0, GETDATE())"
                    self.db.execute_non_query(sql_mail, (user_code, title, msg))
                    
                    print(f"✅ Đã chấm xong Session {sid}: {score}đ")

                except Exception as e:
                    print(f"❌ Lỗi AI chấm điểm Session {sid}: {e}")
                    continue

        except Exception as e:
            print(f"❌ Lỗi SQL process_pending_grading: {e}")

    
    def request_teaching(self, user_code, material_id):
        try:
            # 1. Kiểm tra hạn mức tuần
            query_check = """
                SELECT COUNT(*) as RequestCount FROM dbo.TRAINING_REQUEST_LOGS 
                WHERE UserCode = ? AND RequestDate >= DATEADD(day, -7, GETDATE())
            """
            result_check = self.db.get_data(query_check, (user_code,))
            count = result_check[0]['RequestCount'] if result_check else 0
            if count >= 3:
                return False, "Sếp đã hết lượt đề nghị trong tuần này (tối đa 3)."

            # 2. Lưu log đề nghị (Ghi nhận vào SQL thành công như hình sếp chụp)
            self.db.execute_non_query(
                "INSERT INTO dbo.TRAINING_REQUEST_LOGS (CourseID, UserCode, RequestDate, IsDone) VALUES (?, ?, GETDATE(), 0)", 
                (material_id, user_code)
            )

            # 3. Lấy danh sách người yêu cầu để chuẩn bị nội dung Task
            # FIX: Tên biến request_list phải khớp với logic phía dưới
            query_list = """
                SELECT L.UserCode, U.SHORTNAME, L.RequestDate
                FROM dbo.TRAINING_REQUEST_LOGS L
                JOIN [GD - NGUOI DUNG] U ON L.UserCode = U.USERCODE
                WHERE L.CourseID = ? AND L.IsDone = 0
                ORDER BY L.RequestDate DESC
            """
            request_list = self.db.get_data(query_list, (material_id,)) # Đã có request_list
            total_req = len(request_list)
            # [BỔ SUNG AUDIT LOG]
            
            self.db.write_audit_log(
                user_code, 'TRAINING_REQUEST_TEACH', 'INFO', 
                f"Đề nghị dạy trực tiếp bài học ID: {material_id}", 
                current_app.config.get('SERVER_IP', '127.0.0.1')
            )

            # 4. Logic tạo TASK (Ngưỡng 4 người)
            if total_req > 0 and total_req % 4 == 0:
                mat_info = self.db.get_data("SELECT FileName FROM TRAINING_MATERIALS WHERE MaterialID = ?", (material_id,))
                file_name = mat_info[0]['FileName'] if mat_info else f"Tài liệu {material_id}"
                
                # FIX: Tạo chuỗi danh sách người yêu cầu an toàn
                requesters_str = ", ".join([f"{r['SHORTNAME']}" for r in request_list[:5]])
                # FIX: Lấy ngày yêu cầu gần nhất an toàn
                last_date_obj = request_list[0]['RequestDate']
                last_req_str = last_date_obj.strftime('%d/%m/%Y %H:%M') if last_date_obj else "N/A"

                admin_supervisor = "GD001" 
                task_title = f"📢 DẠY TRỰC TIẾP: {file_name}"
                task_detail = (
                    f"📌 BÀI HỌC: {file_name} (ID: {material_id})\n"
                    f"👤 YÊU CẦU ({total_req} người): {requesters_str}...\n"
                    f"📅 GẦN NHẤT: {last_req_str}\n\n"
                    f"Hệ thống tự động tạo task vì đủ nhóm 4 người đề nghị."
                )
                current_app.task_service.create_new_task(
                    user_code='SYSTEM', 
                    title=task_title,
                    supervisor_code=admin_supervisor,
                    task_type='DAO_TAO',
                    detail_content=task_detail,
                    object_id=str(material_id)
                )
            
            return True, "Gửi đề nghị thành công!"

        except Exception as e:
            current_app.logger.error(f"Lỗi request_teaching: {str(e)}")
            # Trả về lỗi chi tiết để sếp biết vướng ở đâu
            return False, f"Lỗi phía máy chủ: {str(e)}"
    
    