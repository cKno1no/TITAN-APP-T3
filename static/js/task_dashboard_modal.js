/**
 * Task Dashboard - Modal cập nhật, giao việc, autocomplete khách hàng.
 * Cần có sẵn: #updateTaskModal, #task-data-daily, #task-data-history, #task-data-isadmin.
 */
(function () {
    'use strict';

    var isHelpMode = false;

    function showInlineError(id, message) {
        var el = document.getElementById(id);
        if (el) { el.textContent = message || ''; el.style.display = message ? 'block' : 'none'; }
    }
    function clearInlineErrors() {
        showInlineError('update_content_error', '');
        showInlineError('update_helper_error', '');
    }
    function setSubmitButtonLoading(loading) {
        var btn = document.getElementById('update_submit_btn');
        var textEl = document.getElementById('update_submit_text');
        if (!btn || !textEl) return;
        if (loading) {
            btn.disabled = true;
            btn.classList.add('btn-loading');
            textEl.innerHTML = '<span class="btn-spinner"><i class="fas fa-spinner fa-spin"></i></span> Đang lưu...';
        } else {
            btn.disabled = false;
            btn.classList.remove('btn-loading');
            textEl.innerHTML = '<i class="fas fa-save me-1"></i> Lưu Cập Nhật';
        }
    }
    function showToast(icon, title) {
        if (window.Swal) window.Swal.fire({ toast: true, position: 'top-end', icon: icon, title: title || '', showConfirmButton: false, timer: 3000, timerProgressBar: true });
        else alert(title);
    }

    window.syncProgressPercent = function (type) {
        if (type === 'REQUEST_CLOSE') {
            var range = document.getElementById('progress_range');
            var label = document.getElementById('progress_label');
            if (range) range.value = 100;
            if (label) label.innerText = '100%';
        }
    };

    window.toggleHelpBox = function () {
        var box = document.getElementById('helperSelectionBox');
        var btn = document.getElementById('helpCallBtn');
        isHelpMode = !isHelpMode;
        if (isHelpMode) {
            if (box) box.style.display = 'block';
            if (btn) { btn.classList.replace('btn-outline-danger', 'btn-danger'); }
            window.loadEligibleHelpers();
        } else {
            if (box) box.style.display = 'none';
            if (btn) btn.classList.replace('btn-danger', 'btn-outline-danger');
        }
    };

    window.loadEligibleHelpers = function () {
        var select = document.getElementById('helper_code_select');
        if (!select || select.options.length > 0) return;
        fetch('/api/get_eligible_helpers')
            .then(function (r) { return r.json(); })
            .then(function (data) {
                var html = '<optgroup label="GIAO CHO CẢ PHÒNG BAN">';
                html += '<option value="DEPT_KỸ THUẬT">🏢 Cả phòng Kỹ Thuật</option>';
                html += '<option value="DEPT_KHO">🏢 Cả phòng Kho</option>';
                html += '<option value="DEPT_SALES">🏢 Cả phòng Sales</option>';
                html += '<option value="DEPT_KẾ TOÁN">🏢 Cả phòng Kế Toán</option>';
                html += '</optgroup><optgroup label="GIAO CHO CÁ NHÂN">';
                data.forEach(function (h) { html += '<option value="' + h.code + '">👤 ' + h.name + '</option>'; });
                html += '</optgroup>';
                select.innerHTML = html;
            })
            .catch(function (e) { console.error('Lỗi load danh sách helper', e); });
    };

    window.submitCustomTaskUpdate = function () {
        clearInlineErrors();
        var taskId = document.getElementById('update_task_id').value;
        var type = document.getElementById('log_type_select').value;
        var progress = document.getElementById('progress_range').value;
        var content = document.getElementById('update_detail_content').value;
        var objectId = document.getElementById('update_object_id').value;

        if (parseInt(progress, 10) === 100) type = 'REQUEST_CLOSE';

        var helperCodes = [];
        if (isHelpMode) {
            type = 'HELP_CALL';
            var sel = document.getElementById('helper_code_select');
            if (sel) helperCodes = Array.prototype.map.call(sel.selectedOptions, function (opt) { return opt.value; });
            if (helperCodes.length === 0) {
                showInlineError('update_helper_error', 'Vui lòng chọn ít nhất 1 người/phòng ban để giao việc.');
                return;
            }
        }

        if (!content || !content.trim()) {
            showInlineError('update_content_error', 'Vui lòng nhập nội dung báo cáo.');
            return;
        }

        setSubmitButtonLoading(true);
        var formData = new FormData();
        formData.append('task_id', taskId);
        formData.append('log_type', type);
        formData.append('progress_percent', progress);
        formData.append('content', content);
        formData.append('object_id', objectId);
        formData.append('helper_codes', JSON.stringify(helperCodes));

        var fileInput = document.getElementById('update_attachment');
        if (fileInput && fileInput.files.length > 0) formData.append('attachment', fileInput.files[0]);

        fetch('/api/task/log_progress', { method: 'POST', body: formData })
            .then(function (r) { return r.json(); })
            .then(function (result) {
                if (result.success) {
                    showToast('success', result.message || 'Đã lưu.');
                    setTimeout(function () { location.reload(); }, 1500);
                } else {
                    setSubmitButtonLoading(false);
                    showToast('error', result.message || 'Lỗi');
                }
            })
            .catch(function () {
                setSubmitButtonLoading(false);
                showToast('error', 'Lỗi kết nối tới Server!');
            });
    };

    window.approveTask = function (isApproved) {
        var taskId = document.getElementById('update_task_id').value;
        var title = isApproved ? 'Duyệt task' : 'Từ chối task';
        var label = isApproved ? 'Nhận xét (tùy chọn):' : 'Lý do từ chối (bắt buộc):';
        var placeholder = isApproved ? 'Nhập nhận xét...' : 'Nhập lý do từ chối...';
        var inputValidator = isApproved ? function () { return true; } : function (value) { return (value && value.trim()) ? null : 'Cần nhập lý do từ chối!'; };

        if (window.Swal) {
            window.Swal.fire({
                title: title,
                input: 'textarea',
                inputLabel: label,
                inputPlaceholder: placeholder,
                inputAttributes: { 'aria-label': label },
                showCancelButton: true,
                confirmButtonText: isApproved ? 'Duyệt' : 'Gửi từ chối',
                cancelButtonText: 'Hủy',
                inputValidator: inputValidator
            }).then(function (res) {
                if (!res.isConfirmed) return;
                var feedback = (res.value && res.value.trim()) ? res.value.trim() : (isApproved ? 'Duyệt. OK!' : '');
                fetch('/api/task/approve', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ task_id: taskId, is_approved: isApproved, feedback: feedback })
                })
                    .then(function (r) { return r.json(); })
                    .then(function (result) {
                        if (result.success) {
                            showToast('success', result.message || (isApproved ? 'Đã duyệt.' : 'Đã từ chối.'));
                            setTimeout(function () { location.reload(); }, 1500);
                        } else {
                            showToast('error', result.message || 'Lỗi');
                        }
                    })
                    .catch(function () {
                        showToast('error', 'Lỗi kết nối tới Server!');
                    });
            });
        } else {
            var feedback = prompt(isApproved ? 'Nhập nhận xét (tùy chọn):' : 'Nhập lý do từ chối (bắt buộc):');
            if (!isApproved && !feedback) { alert('Cần nhập lý do từ chối!'); return; }
            fetch('/api/task/approve', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ task_id: taskId, is_approved: isApproved, feedback: feedback || 'Duyệt. OK!' })
            })
                .then(function (r) { return r.json(); })
                .then(function (result) {
                    if (result.success) { alert(result.message); location.reload(); }
                    else alert('Lỗi: ' + (result.message || ''));
                });
        }
    };

    window.openUpdateModal = function (taskId) {
        var updateTaskId = document.getElementById('update_task_id');
        var updateTaskIdDisplay = document.getElementById('updateTaskIdDisplay');
        var updateObjectId = document.getElementById('update_object_id');
        var updateTaskTitleDisplay = document.getElementById('updateTaskTitleDisplay');
        var helperBox = document.getElementById('helperSelectionBox');
        var helpCallBtn = document.getElementById('helpCallBtn');
        var attachInput = document.getElementById('update_attachment');
        var approveBlock = document.getElementById('approve_action_block');
        var container = document.getElementById('logHistoryContainer');
        var modalEl = document.getElementById('updateTaskModal');

        if (updateTaskId) updateTaskId.value = taskId;
        if (updateTaskIdDisplay) updateTaskIdDisplay.innerText = '#' + taskId;

        var dailyEl = document.getElementById('task-data-daily');
        var historyEl = document.getElementById('task-data-history');
        var dailyTasks = [];
        var historyTasks = [];
        if (dailyEl && dailyEl.textContent) try { dailyTasks = JSON.parse(dailyEl.textContent); } catch (e) {}
        if (historyEl && historyEl.textContent) try { historyTasks = JSON.parse(historyEl.textContent); } catch (e) {}
        var task = null;
        dailyTasks.concat(historyTasks).forEach(function (t) { if (t && t.TaskID == taskId) task = t; });
        if (task) {
            if (updateObjectId) updateObjectId.value = task.ObjectID || '';
            if (updateTaskTitleDisplay) updateTaskTitleDisplay.innerText = task.Title || '';
        }

        isHelpMode = false;
        if (helperBox) helperBox.style.display = 'none';
        if (helpCallBtn) helpCallBtn.classList.replace('btn-danger', 'btn-outline-danger');
        if (attachInput) attachInput.value = '';
        clearInlineErrors();
        setSubmitButtonLoading(false);

        var isAdminEl = document.getElementById('task-data-isadmin');
        var isAdmin = false;
        if (isAdminEl && isAdminEl.textContent) try { isAdmin = JSON.parse(isAdminEl.textContent); } catch (e) {}
        if (approveBlock) approveBlock.style.display = isAdmin ? 'block' : 'none';

        if (container) container.innerHTML = '<div class="text-center text-muted py-3"><i class="fas fa-spinner fa-spin me-2"></i>Đang tải dữ liệu...</div>';

        if (typeof bootstrap !== 'undefined' && modalEl) {
            var modal = bootstrap.Modal.getInstance(modalEl);
            if (!modal) modal = new bootstrap.Modal(modalEl);
            modal.show();
        } else if (typeof $ !== 'undefined' && modalEl) {
            $(modalEl).modal('show');
        }

        fetch('/api/task/history/' + taskId)
            .then(function (r) { return r.json(); })
            .then(function (logs) {
                if (!Array.isArray(logs)) {
                    if (container) container.innerHTML = '<div class="text-center text-danger py-3">Lỗi dữ liệu lịch sử từ Server.</div>';
                    return;
                }
                var html = logs.map(function (log) {
                    var dateStr = log.UpdateDate ? new Date(log.UpdateDate).toLocaleString('vi-VN') : '';
                    var sf = log.SupervisorFeedback ? '<div class="mt-2 ms-4 p-2 bg-warning-subtle border-start border-warning border-4 rounded shadow-sm"><div class="fw-bold text-danger mb-1" style="font-size: 0.8rem;"><i class="fas fa-reply me-1"></i>SẾP CHỈ ĐẠO:</div><div class="text-dark fst-italic" style="font-size: 0.9rem;">' + log.SupervisorFeedback + '</div></div>' : '';
                    return '<div class="timeline-item mb-3"><div class="timeline-marker mt-1"></div><div class="d-flex justify-content-between align-items-start mb-1 ms-3"><span class="badge bg-secondary">' + (log.UserShortName || log.UserCode) + '</span><small class="text-muted">' + dateStr + '</small></div><div class="ps-3 py-1 ms-2" style="font-size: 0.95rem;"><strong><i class="fas fa-angle-right text-muted me-1"></i></strong> ' + (log.UpdateContent || '') + '</div>' + sf + '</div>';
                }).join('') || '<div class="text-center text-muted py-3">Chưa có lịch sử cập nhật.</div>';
                if (container) container.innerHTML = html;
            })
            .catch(function (err) {
                console.error('Lỗi khi mở modal:', err);
                if (container) container.innerHTML = '<div class="text-center text-danger py-3">Không thể tải lịch sử.</div>';
            });
    };

    /* Autocomplete khách hàng: do task_dashboard.js xử lý (API /sales/api/khachhang) */

    var contentEl = document.getElementById('update_detail_content');
    var helperSelectEl = document.getElementById('helper_code_select');
    if (contentEl) contentEl.addEventListener('input', function () { showInlineError('update_content_error', ''); });
    if (contentEl) contentEl.addEventListener('blur', function () { showInlineError('update_content_error', ''); });
    if (helperSelectEl) helperSelectEl.addEventListener('change', function () { showInlineError('update_helper_error', ''); });
})();
