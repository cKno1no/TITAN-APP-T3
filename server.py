# server.py
# --- TITAN OS PRODUCTION SERVER ---

import logging
from datetime import datetime
import os
import schedule
import time
import threading

# Import ứng dụng Flask (Biến 'app' này đã chứa sẵn chatbot_service nhờ factory.py)
from app import app
from waitress import serve
from apscheduler.schedulers.background import BackgroundScheduler

# =======================================================
# 1. ĐỊNH NGHĨA HÀM SCHEDULER (SỬ DỤNG SERVICE CỦA APP)
# =======================================================
def run_daily_challenge_job():
    print(f"⏰ [Cron] Kích hoạt Daily Challenge Batch: {datetime.now().strftime('%H:%M:%S')}")
    
    # [QUAN TRỌNG] Sử dụng app_context để truy cập vào biến 'app' an toàn
    with app.app_context():
        try:
            # Truy cập chatbot_service đã được gắn vào app ở factory.py
            if hasattr(app, 'chatbot_service'):
                # Gọi hàm phân phối câu hỏi
                # Đổi .training thành .training_service cho khớp với chatbot_service.py
                messages = app.chatbot_service.training_service.distribute_daily_questions()
                
                
                count = 0
                if messages:
                    for item in messages:
                        # [TODO] Sếp thêm logic gửi tin nhắn (Zalo/Socket) ở đây
                        # Ví dụ: notification_service.send(item['user_code'], item['message'])
                        print(f"   -> Gửi challenge cho {item['user_code']}")
                        count += 1
                print(f"✅ Đã gửi {count} câu hỏi daily.")
            else:
                print("❌ Lỗi: app.chatbot_service chưa được khởi tạo.")
                
        except Exception as e:
            print(f"❌ Lỗi Scheduler Daily Challenge: {e}")

# =========================================================================
# 2. CẤU HÌNH LOGGING
# =========================================================================
def logger_setup():
    if not os.path.exists('logs'):
        os.makedirs('logs')

    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        handlers=[
            logging.FileHandler(f"logs/titan_server_{datetime.now().strftime('%Y%m%d')}.log", encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    logging.info("Titan OS Startup: Hệ thống Logging đã kích hoạt.")

# =========================================================================
# 3. CÁC JOB KHÁC
# =========================================================================
def run_daily_gamification():
    """Job chạy định kỳ (20:00 hàng ngày) tổng kết điểm."""
    with app.app_context():
        try:
            print(f">>> [Job Scheduler] Bắt đầu tổng kết Gamification...")
            if hasattr(app, 'gamification_service'):
                app.gamification_service.process_daily_rewards()
            else:
                print("❌ Lỗi: Gamification Service chưa khởi tạo.")
        except Exception as e:
            print(f"❌ Lỗi Gamification Job: {e}")

def run_schedule_loop():
    """Vòng lặp cho thư viện 'schedule' (nếu sếp dùng song song với apscheduler)"""
    while True:
        try:
            schedule.run_pending()
            time.sleep(60) 
        except Exception as e:
            logging.error(f"Lỗi Scheduler Loop: {e}")
            time.sleep(60)

# =======================================================
# 1. ĐỊNH NGHĨA HÀM SCHEDULER CHẤM ĐIỂM AI
# =======================================================
def run_grading_job():
    """Quét và chấm điểm tự động các bài Daily Challenge đã hết hạn."""
    print(f"🤖 [Cron] Kích hoạt AI Grading Batch: {datetime.now().strftime('%H:%M:%S')}")
    with app.app_context():
        try:
            if hasattr(app, 'training_service'):
                # Gọi hàm xử lý chấm điểm hàng loạt đã viết trong Service
                app.training_service.process_pending_grading()
                print("✅ Đã hoàn tất đợt chấm điểm AI.")
            else:
                print("❌ Lỗi: training_service chưa được khởi tạo trong app.")
        except Exception as e:
            print(f"❌ Lỗi Job chấm điểm: {e}")

# =========================================================================
# 4. MAIN ENTRY POINT (CẬP NHẬT SCHEDULER)
# =========================================================================
if __name__ == '__main__':
    logger_setup()
    
    import socket
    
    # [QUAN TRỌNG] Sếp điền cái tên máy chủ vừa lấy ở Bước 1 vào đây nhé!
    PROD_SERVER_NAME = "ĐIỀN_TÊN_MÁY_CHỦ_VÀO_ĐÂY" 
    
    current_machine = socket.gethostname()

    # CHỈ BẬT CRONJOB NẾU ĐANG CHẠY TRÊN ĐÚNG MÁY CHỦ
    if current_machine == PROD_SERVER_NAME:
        print(f"✅ Phát hiện Máy chủ ({current_machine}): Đang bật hệ thống Cronjob...")
        
        # --- CẤU HÌNH APSCHEDULER ---
        scheduler = BackgroundScheduler()
        
        # [1] Lên lịch gửi câu hỏi (Mốc giờ mới)
        scheduler.add_job(run_daily_challenge_job, 'cron', hour=8, minute=30)
        scheduler.add_job(run_daily_challenge_job, 'cron', hour=13, minute=30)
        scheduler.add_job(run_daily_challenge_job, 'cron', hour=16, minute=45)

        # [2] Lên lịch CHẤM ĐIỂM tự động (Mốc giờ mới)
        scheduler.add_job(run_grading_job, 'cron', hour=9, minute=30)
        scheduler.add_job(run_grading_job, 'cron', hour=15, minute=44)
        scheduler.add_job(run_grading_job, 'cron', hour=17, minute=45)
        
        # [3] Lên lịch quét quà tổng kết ngày (20:00)
        scheduler.add_job(run_daily_gamification, 'cron', hour=20, minute=0)
        
        scheduler.start()
    else:
        # NẾU LÀ MÁY DEV (PC CỦA SẾP) THÌ TẮT CRONJOB ĐỂ TRÁNH GỬI TRÙNG
        print(f"⚠️ Phát hiện Máy DEV ({current_machine}): ĐÃ TẮT TỰ ĐỘNG CRONJOB.")

    # --- KHỞI CHẠY SERVER WEBSITES ---
    print("-------------------------------------------------------")
    print("TITAN OS - PRODUCTION SERVER (WAITRESS)")
    print("Server is running at: http://0.0.0.0:5000")
    print("-------------------------------------------------------")
    
    serve(app, host='0.0.0.0', port=5000, threads=12)