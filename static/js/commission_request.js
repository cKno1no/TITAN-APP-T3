let currentMaSo = null;
let contactModal = null; 

function formatCurrency(num) {
    return new Intl.NumberFormat('vi-VN').format(num || 0);
}

document.addEventListener('DOMContentLoaded', function() {
    contactModal = new bootstrap.Modal(document.getElementById('addContactModal'));
});

// --- 1. TÌM KHÁCH HÀNG ---
const searchInput = document.getElementById('kh_search_input');
const resultsDropdown = document.getElementById('kh_search_results');

searchInput.addEventListener('input', function() {
    const term = this.value.trim();
    if (term.length < 2) { resultsDropdown.style.display = 'none'; return; }
    fetch(`/sales/api/khachhang/${term}`).then(r => r.json()).then(data => {
        resultsDropdown.innerHTML = '';
        if (data.length > 0) {
            data.forEach(kh => {
                const opt = document.createElement('option');
                opt.value = kh.ID; opt.text = `${kh.FullName} (${kh.ID})`;
                resultsDropdown.appendChild(opt);
            });
            resultsDropdown.style.display = 'block';
        }
    });
});

resultsDropdown.addEventListener('change', function() {
    const selected = this.options[this.selectedIndex];
    document.getElementById('kh_id_selected').value = selected.value;
    searchInput.value = selected.text;
    resultsDropdown.style.display = 'none';
});

document.addEventListener('click', function(e) {
    if (!searchInput.contains(e.target) && !resultsDropdown.contains(e.target)) resultsDropdown.style.display = 'none';
});

// --- 2. TẠO PHIẾU ---
function createProposal() {
    const customerId = document.getElementById('kh_id_selected').value;
    if (!customerId) { alert("Vui lòng chọn khách hàng."); return; }
    const btn = document.getElementById('btnCreate');
    btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Xử lý...';

    fetch('/api/commission/create', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            customer_id: customerId,
            date_from: document.getElementById('date_from').value,
            date_to: document.getElementById('date_to').value,
            rate: document.getElementById('commission_rate').value,
            note: document.getElementById('proposal_note').value
        })
    })
    .then(r => r.json()).then(data => {
        btn.disabled = false; btn.innerHTML = '<i class="fas fa-bolt me-2"></i>Tạo Phiếu';
        if (data.success) {
            currentMaSo = data.ma_so;
            renderTable(data.details);
            renderRecipients(data.recipients);
            updateFooter(data.master);
            
            document.getElementById('recipientCard').classList.remove('d-none');
            document.getElementById('resultCard').classList.remove('d-none');
            document.getElementById('bottomBar').classList.remove('d-none');
            document.getElementById('displayMaSo').innerText = currentMaSo;
        } else { alert("Lỗi: " + data.message); }
    });
}

// --- 3. VẼ BẢNG HÓA ĐƠN ---
function renderTable(details) {
    const tbody = document.getElementById('invoiceTableBody');
    tbody.innerHTML = '';
    let totalInvoiceVal = 0;
    if (!details || details.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center p-4 text-muted">Không tìm thấy hóa đơn.</td></tr>';
        return;
    }
    details.forEach(item => {
        totalInvoiceVal += parseFloat(item.DOANH_SO || 0);
        const row = `
            <tr class="${item.CHON ? 'table-info' : ''}" id="row-${item.VoucherID}">
                <td class="text-center">
                    <input type="checkbox" class="form-check-input item-checkbox" 
                        onchange="toggleItem('${item.VoucherID}', this.checked)" ${item.CHON ? 'checked' : ''}>
                </td>
                <td>${item.VoucherDate ? new Date(item.VoucherDate).toLocaleDateString('vi-VN') : ''}</td>
                <td class="fw-bold text-primary">${item.InvoiceNo || item.INVOICE_NO || '---'}</td>
                <td class="small text-muted">${item.VoucherID}</td>
                <td class="text-end fw-bold">${formatCurrency(item.DOANH_SO)}</td>
            </tr>`;
        tbody.insertAdjacentHTML('beforeend', row);
    });
    document.getElementById('displayTotalInvoice').innerText = formatCurrency(totalInvoiceVal);
}

// --- 4. VẼ BẢNG NGƯỜI NHẬN ---
function renderRecipients(recipients) {
    const tbody = document.getElementById('recipientTableBody');
    tbody.innerHTML = '';
    let total = 0;
    if(!recipients || recipients.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted fst-italic py-3">Chưa có người thụ hưởng.</td></tr>';
    } else {
        recipients.forEach(r => {
            total += parseFloat(r['MUC CHI'] || 0);
            const row = `<tr>
                <td class="fw-bold">${r['NHAN SU']}</td>
                <td>${r['NGAN HANG'] || '-'}</td>
                <td class="font-monospace">${r['SO TAI KHOAN'] || '-'}</td>
                <td class="text-end text-danger fw-bold">${formatCurrency(r['MUC CHI'])}</td>
                <td class="text-center"><i class="fas fa-check text-success"></i></td>
            </tr>`;
            tbody.insertAdjacentHTML('beforeend', row);
        });
    }
    document.getElementById('totalRecipientAmount').innerText = formatCurrency(total);
}

// --- 5. LOGIC KHÁC ---
function toggleItem(voucherId, isChecked) {
    const row = document.getElementById(`row-${voucherId}`);
    if (row) isChecked ? row.classList.add('table-info') : row.classList.remove('table-info');
    fetch('/api/commission/toggle_item', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ detail_id: voucherId, is_checked: isChecked, ma_so: currentMaSo })
    }).then(r => r.json()).then(data => { if (data.success) updateFooter(data.master); });
}

function toggleAll(sourceChecked) {
     const checkboxes = document.querySelectorAll('.item-checkbox');
     let promises = [];
     checkboxes.forEach(cb => {
         cb.checked = sourceChecked;
         const voucherId = cb.getAttribute('onchange').match(/'([^']+)'/)[1];
         const row = document.getElementById(`row-${voucherId}`);
         if (row) sourceChecked ? row.classList.add('table-info') : row.classList.remove('table-info');

         promises.push(
             fetch('/api/commission/toggle_item', {
                 method: 'POST', headers: {'Content-Type': 'application/json'},
                 body: JSON.stringify({ detail_id: voucherId, is_checked: sourceChecked, ma_so: currentMaSo })
             }).then(r => r.json())
         );
     });
     Promise.all(promises).then(results => {
         if(results.length > 0 && results[results.length-1].success) updateFooter(results[results.length-1].master);
     });
}

function updateFooter(master) {
    document.getElementById('footerTotalDS').innerText = formatCurrency(master.DOANH_SO_CHON);
    document.getElementById('footerTotalCommission').innerText = formatCurrency(master.GIA_TRI_CHI);
}

function openAddContactModal() {
    const custId = document.getElementById('kh_id_selected').value;
    if(!custId || !currentMaSo) { alert("Chưa tạo phiếu."); return; }
    fetch(`/api/nhansu_ddl_by_khachhang/${custId}`).then(r => r.json()).then(data => {
        const sel = document.getElementById('manual_contact_select');
        sel.innerHTML = '<option value="">-- Chọn nhân sự --</option>';
        data.forEach(item => sel.add(new Option(item.text, item.text)));
        contactModal.show();
    });
}

function submitManualContact() {
    const contactName = document.getElementById('manual_contact_select').value;
    const amount = parseFloat(document.getElementById('manual_amount').value);
    if(!contactName || amount <= 0) { alert("Vui lòng nhập đúng thông tin."); return; }
    
    fetch('/api/commission/add_contact', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            ma_so: currentMaSo,
            contact_name: contactName,
            bank_name: document.getElementById('manual_bank_name').value,
            bank_account: document.getElementById('manual_bank_acc').value,
            amount: amount
        })
    })
    .then(r => r.json()).then(data => {
        if(data.success) {
            alert("Đã thêm!");
            contactModal.hide();
            renderRecipients(data.recipients);
            if(data.master) updateFooter(data.master);
        } else { alert("Lỗi: " + data.message); }
    });
}

function submitProposal() {
    if (!confirm("Hệ thống sẽ xóa các hóa đơn không được chọn và tạo đề nghị thanh toán kèm phiếu in. Tiếp tục?")) return;
    fetch('/api/commission/submit', {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ ma_so: currentMaSo })
    })
    .then(r => r.json()).then(data => {
        if (data.success) { 
            alert(data.message); 
            window.location.reload(); 
        } else { alert("Lỗi: " + data.message); }
    });
}

