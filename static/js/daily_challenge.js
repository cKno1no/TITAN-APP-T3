/**
 * Daily Challenge - Alpine.js app
 */
function dailyChallengeApp() {
    return {
        isLoading: true,
        loadError: false,
        question: null,
        sessionState: 'PENDING',
        userAnswer: '',
        isSubmitting: false,
        history: [],
        nextSlot: '--:--',
        secondsLeft: 900,
        isTimeUp: false,
        timer: null,

        async initData() {
            this.isLoading = true;
            this.loadError = false;
            try {
                var res = await fetch('/api/challenge/status');
                if (!res.ok) throw new Error('Không tải được trạng thái thử thách.');
                var data = await res.json();

                if (data.status === 'AVAILABLE') {
                    this.question = {
                        ID: data.session_id,
                        Content: data.question.Content,
                        Image: data.question.Image
                    };
                    this.sessionState = 'PENDING';
                    this.secondsLeft = data.seconds_left || 900;
                    this.nextSlot = data.next_slot || '--:--';
                    var draft = localStorage.getItem('draft_daily_' + this.question.ID);
                    if (draft) this.userAnswer = draft;
                    this.startTimer();
                } else if (data.status === 'WAITING') {
                    this.question = null;
                    this.nextSlot = data.next_slot || '--:--';
                    setTimeout(function() { this.initData(); }.bind(this), 60000);
                } else {
                    this.sessionState = data.status;
                    this.question = typeof data.question === 'object' ? data.question : { Content: data.question };
                    this.userAnswer = data.user_answer || '';
                }

                var hRes = await fetch('/api/training/daily_challenge/history');
                var hData = await hRes.json();
                if (hData.success) this.history = hData.history || [];
            } catch (e) {
                console.error('Lỗi:', e);
                this.loadError = true;
                if (window.Swal) {
                    var self = this;
                    window.Swal.fire({
                        icon: 'error',
                        title: 'Không tải được thử thách',
                        text: (e && e.message) ? e.message : 'Vui lòng thử lại sau.',
                        confirmButtonText: 'Thử lại'
                    }).then(function(r) {
                        if (r.isConfirmed) self.initData();
                    });
                }
            } finally {
                this.isLoading = false;
            }
        },

        startTimer: function() {
            if (this.timer) clearInterval(this.timer);
            var self = this;
            this.timer = setInterval(function() {
                if (self.secondsLeft > 0) {
                    self.secondsLeft--;
                } else {
                    clearInterval(self.timer);
                    self.isTimeUp = true;
                    self.autoSubmit();
                }
            }, 1000);
        },

        formatTime: function(seconds) {
            var m = Math.floor(seconds / 60);
            var s = seconds % 60;
            return (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s;
        },

        saveDraft: function() {
            if (this.question && this.question.ID) {
                localStorage.setItem('draft_daily_' + this.question.ID, this.userAnswer);
            }
        },

        async autoSubmit() {
            if (this.sessionState === 'PENDING') {
                await this.submitAnswer(true);
            }
        },

        async submitAnswer(isAuto) {
            if (this.isSubmitting) return;
            this.isSubmitting = true;
            try {
                var res = await fetch('/api/challenge/submit', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: this.question.ID,
                        answer: this.userAnswer
                    })
                });
                var result = await res.json();

                if (result.success) {
                    this.sessionState = 'SUBMITTED';
                    localStorage.removeItem('draft_daily_' + this.question.ID);
                    if (this.timer) clearInterval(this.timer);
                    if (window.Swal) {
                        window.Swal.fire({
                            icon: 'success',
                            title: isAuto ? 'Hết giờ làm bài!' : 'Thành công!',
                            text: isAuto ? 'Hệ thống đã lưu nội dung hiện có.' : 'Bài làm đã được gửi tới AI chấm điểm.',
                            background: '#ffffff',
                            color: '#1e293b',
                            confirmButtonColor: '#3b82f6'
                        });
                    }
                } else {
                    if (window.Swal) {
                        window.Swal.fire({
                            icon: 'error',
                            title: 'Gửi bài thất bại',
                            text: (result.message || 'Vui lòng thử lại.')
                        });
                    }
                }
            } catch (e) {
                console.error(e);
                if (window.Swal) {
                    window.Swal.fire({
                        icon: 'error',
                        title: 'Lỗi kết nối',
                        text: (e && e.message) ? e.message : 'Không thể gửi bài. Vui lòng thử lại.'
                    });
                }
            } finally {
                this.isSubmitting = false;
            }
        },

        formatText: function(text) {
            if (!text) return '';
            var formatted = text.replace(/\n/g, '<br>');
            formatted = formatted.replace(/- ([A-F]):/g, '<strong>- $1:</strong>');
            formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
            return formatted;
        }
    };
}
