const reviewModal = new bootstrap.Modal(document.getElementById('reviewModal'));

// Hàm format số chuẩn (1,234,567) cho Modal chi tiết
function formatNumberExact(num) {
    if (num === undefined || num === null) return '0';
    return new Intl.NumberFormat('en-US').format(num);
}

// Hàm format số rút gọn cho context (1.2M)
function formatNumberCompact(num) {
    if (!num) return '0';
    return new Intl.NumberFormat('en-US', { notation: "compact", maximumFractionDigits: 1 }).format(num);
}

function openReviewModal(item) {
    document.getElementById('md_request_id').value = item.RequestID;
    document.getElementById('md_requester').innerText = item.RequesterName;
    
    // [MỚI] Hiển thị Đối tượng thụ hưởng
    const objName = item.ObjectName || '---';
    const objId = item.ObjectID || '';
    document.getElementById('md_object_info').innerText = objId ? `${objName} (${objId})` : objName;

    document.getElementById('md_amount').innerText = formatNumberExact(item.Amount) + ' VNĐ';
    document.getElementById('md_budget').innerText = `${item.BudgetName} (${item.BudgetCode})`;
    document.getElementById('md_reason').innerText = item.Reason;

    // Attachments
    const attachBox = document.getElementById('md_attachments_box');
    const attachList = document.getElementById('md_attachment_list');
    attachList.innerHTML = '';
    
    const rawFiles = item.Attachments || item.attachments;
    if (rawFiles && rawFiles.trim() !== '') {
        attachBox.classList.remove('d-none');
        rawFiles.split(';').forEach(file => {
            if(file.trim()) {
                const link = document.createElement('a');
                link.href = `/attachments/${file}`;
                link.target = '_blank';
                link.className = 'btn btn-sm btn-light border shadow-sm text-primary';
                // Lấy tên file gốc (bỏ prefix timestamp)
                const name = file.split('_').slice(2).join('_') || file;
                link.innerHTML = `<i class="fas fa-file-download me-1"></i> ${name}`; 
                attachList.appendChild(link);
            }
        });
    } else {
        attachBox.classList.add('d-none');
    }

    // Budget Context (Logic Progress bar)
    const ytdPlan = parseFloat(item.YTD_Plan) || 0;
    const ytdActual = parseFloat(item.YTD_Actual) || 0; 
    const currentAmount = parseFloat(item.Amount) || 0;
    const totalUsage = ytdActual + currentAmount;
    const remaining = ytdPlan - totalUsage;

    let pctActual = (ytdPlan > 0) ? (ytdActual / ytdPlan) * 100 : 0;
    let pctCurrent = (ytdPlan > 0) ? (currentAmount / ytdPlan) * 100 : 0;

    // Nếu vượt quá 100% thì scale lại
    if (pctActual + pctCurrent > 100) {
        const scale = 100 / (pctActual + pctCurrent);
        pctActual *= scale; pctCurrent *= scale;
    }

    document.getElementById('bar_actual').style.width = `${pctActual}%`;
    document.getElementById('bar_current').style.width = `${pctCurrent}%`;

    document.getElementById('md_plan').innerText = formatNumberCompact(ytdPlan);
    document.getElementById('md_used').innerText = formatNumberCompact(ytdActual);
    document.getElementById('md_parent_code').innerText = item.ParentCode || '';

    const alertMsg = document.getElementById('md_alert_msg');
    const badge = document.getElementById('md_warning_badge');
    const elRemaining = document.getElementById('md_remaining');
    
    elRemaining.innerText = formatNumberCompact(remaining);
    elRemaining.className = remaining < 0 ? "text-danger fw-bold" : "text-success fw-bold";

    if (item.IsWarning) {
        alertMsg.classList.remove('d-none');
        badge.classList.remove('d-none');
        document.getElementById('md_context_box').classList.add('warning');
    } else {
        alertMsg.classList.add('d-none');
        badge.classList.add('d-none');
        document.getElementById('md_context_box').classList.remove('warning');
    }
    
    document.getElementById('md_note').value = '';
    reviewModal.show();
}

function submitDecision(action) {
    const reqId = document.getElementById('md_request_id').value;
    const note = document.getElementById('md_note').value;

    if (action === 'REJECT' && !note.trim()) { alert("Vui lòng nhập lý do từ chối."); return; }
    if(!confirm(`Xác nhận ${action === 'APPROVE' ? 'DUYỆT' : 'TỪ CHỐI'} đề nghị này?`)) return;

    fetch('/api/budget/approve', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ request_id: reqId, action: action, note: note })
    })
    .then(r => r.json()).then(data => {
        if (data.success) { reviewModal.hide(); location.reload(); } 
        else { alert("Lỗi: " + data.message); }
    }).catch(() => alert("Lỗi kết nối server."));
}

