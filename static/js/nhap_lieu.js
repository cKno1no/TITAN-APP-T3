const NHAPLIEU_DRAFT_KEY = 'NHAPLIEU_DRAFT';
const DRAFT_AUTOSAVE_INTERVAL_MS = 45000;

document.addEventListener('DOMContentLoaded', function() {
    
    // --- VARIABLES ---
    let allDefaults = {};
    let activeEditorId = 'editor_noi_dung_1'; 
    let activeTagGroup = '1'; 
    let searchTimeout = null;
    let draftSaveTimer = null;

    // --- ELEMENTS ---
    const inpSearchKh = document.getElementById('kh_ten_tat');
    const khSearchResults = document.getElementById('kh_search_results');
    const ddlLoaiBaoCao = document.getElementById('ddl_loai_bao_cao');
    const reportForm = document.getElementById('reportForm');

    // --- 1. CUSTOMER SEARCH LOGIC ---
    if(inpSearchKh) {
        inpSearchKh.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(timKhachHang, 300);
        });
        
        inpSearchKh.addEventListener('keydown', function(e) { 
            if (e.key === 'Enter') { e.preventDefault(); timKhachHang(); } 
        });
    }

    if(khSearchResults) {
        khSearchResults.addEventListener('change', chonKhachHang);
    }

    function timKhachHang() {
        const ten_tat = inpSearchKh.value.trim();
        khSearchResults.style.display = 'none'; 
        khSearchResults.innerHTML = '';
        
        if (ten_tat.length < 2) return;
        
        fetch(`/sales/api/khachhang/${encodeURIComponent(ten_tat)}`)
            .then(r => r.json())
            .then(data => {
                if (data && data.length > 0) {
                    data.forEach(kh => {
                        const option = document.createElement('option');
                        option.value = kh.ID; 
                        option.textContent = `${kh.FullName} (${kh.ID})`;
                        option.setAttribute('data-fullname', kh.FullName);
                        option.setAttribute('data-diachi', kh.Address || 'N/A');
                        khSearchResults.appendChild(option);
                    });
                    khSearchResults.style.display = 'block'; 
                    khSearchResults.size = Math.min(data.length, 5) + 1;
                }
            }).catch(console.error);
    }

    function chonKhachHang() {
        if (khSearchResults.selectedIndex === -1) return;
        const selectedOption = khSearchResults.options[khSearchResults.selectedIndex];
        if (selectedOption) {
            const maDoiTuong = selectedOption.value;
            document.getElementById('kh_ma_doi_tuong').value = maDoiTuong;
            document.getElementById('kh_ten_day_du').value = selectedOption.getAttribute('data-fullname');
            document.getElementById('ref_diachi').textContent = selectedOption.getAttribute('data-diachi');
            khSearchResults.style.display = 'none';
            
            // Trigger extra fetches
            fetchReferenceCount(maDoiTuong); 
            fetchNhansuDropdownData(maDoiTuong); 
        }
    }

    function fetchReferenceCount(maDoiTuong) {
        const nlhObject = document.getElementById('ref_nlh_count');
        if(nlhObject) nlhObject.textContent = '...';
        fetch(`/api/khachhang/ref/${maDoiTuong}`)
            .then(r => r.json())
            .then(data => { 
                if(nlhObject) nlhObject.textContent = `Đã liên hệ ${data.CountNLH || 0} người.`; 
            })
            .catch(() => { if(nlhObject) nlhObject.textContent = `Lỗi tải.`; });
    }

    // --- 2. STAFF DROPDOWN LOGIC ---
    function fetchNhansuDropdownData(maDoiTuong) {
        fetch(`/api/nhansu_ddl_by_khachhang/${maDoiTuong}`)
            .then(r => r.json())
            .then(data => {
                const ddl1 = document.getElementById('nhansu_hengap_1');
                const ddl2 = document.getElementById('nhansu_hengap_2');
                if(!ddl1 || !ddl2) return;

                ddl1.innerHTML = '<option value="">-- Chọn Nhân sự --</option>';
                ddl2.innerHTML = '<option value="">-- Chọn (Không bắt buộc) --</option>';
                
                if (data && data.length > 0) {
                    data.forEach(item => {
                        ddl1.appendChild(new Option(item.text, item.id));
                        ddl2.appendChild(new Option(item.text, item.id));
                    });
                }
            }).catch(console.error);
    }

    // Make global for onclick in HTML
    window.openNhansuForm = function(event) {
        event.preventDefault();
        const maDoiTuong = document.getElementById('kh_ma_doi_tuong').value;
        if (maDoiTuong.trim() !== '') { 
            window.open(`/nhansu_nhaplieu?kh_code=${maDoiTuong}`, '_blank'); 
        } else { 
            alert("Vui lòng chọn Khách hàng trước."); 
        }
    };

    // --- 3. EDITOR & TAG LOGIC ---
    
    // Create Tag Button DOM
    function createTagButton(tagName, tagTemplate, isGlobal = false) {
        const btn = document.createElement('div');
        btn.className = isGlobal ? 'tag-btn global-tag' : 'tag-btn';
        const icon = isGlobal ? 'fa-star' : 'fa-plus-circle';
        btn.innerHTML = `<i class="fas ${icon}"></i> ${tagName}`;
        
        btn.onclick = function() {
            injectHeaderOnly(tagName);
            updateSuggestionPreview(tagTemplate);
        };
        return btn;
    }

    // Insert Header into ContentEditable
    function injectHeaderOnly(tagName) {
        const editor = document.getElementById(activeEditorId);
        if (!editor) return;

        const htmlTemplate = `
            <div class="injected-header-p" contenteditable="false">
                <strong style="flex-grow: 1;">${tagName}:</strong>
                <span class="delete-header-btn" onclick="this.parentElement.nextElementSibling?.remove(); this.parentElement.remove();">&times;</span>
            </div>
            <br>
        `;
        
        editor.focus();
        
        // Move cursor to end
        const range = document.createRange();
        range.selectNodeContents(editor);
        range.collapse(false); 
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);

        // Insert
        document.execCommand('insertHTML', false, htmlTemplate);
        editor.scrollTop = editor.scrollHeight;
    }

    function updateSuggestionPreview(tagTemplate) {
        const previewContent = document.getElementById('suggestion-preview-content');
        if(!previewContent) return;

        const templateLines = (tagTemplate || '').split('\n').filter(line => line.trim() !== '');
        
        if (templateLines.length === 0) {
            previewContent.innerHTML = '<p class="text-muted small">Không có nội dung gợi ý.</p>';
            return;
        }

        let html = '<ul style="padding-left: 20px; margin-bottom: 0;">';
        templateLines.forEach(line => {
            let clean = line.trim();
            if (clean.startsWith('*')) clean = clean.substring(1).trim();
            clean = clean.replace(/\\F058/gi, '').trim();
            clean = clean.replace(/"/g, '');
            html += `<li>${clean}</li>`;
        });
        html += '</ul>';
        previewContent.innerHTML = html;
    }

    // --- 4. CONFIG & DROPDOWNS ---
    
    function resetTabsAndEditors() {
        const tabA = document.getElementById('lbl_tab_A');
        const tabB = document.getElementById('lbl_tab_B');
        const tabC = document.getElementById('lbl_tab_C');
        if(tabA) tabA.textContent = 'Tab A';
        if(tabB) tabB.textContent = 'Tab B';
        if(tabC) tabC.textContent = 'Tab C';

        const liB = document.getElementById('li_tab_b');
        const liC = document.getElementById('li_tab_c');
        if(liB) liB.classList.remove('hidden-field');
        if(liC) liC.classList.remove('hidden-field');
        
        document.getElementById('editor_noi_dung_1').innerHTML = '';
        document.getElementById('editor_noi_dung_2').innerHTML = '';
        document.getElementById('editor_danh_gia_1').innerHTML = '';

        updateDropdown(null, '4', 'noi_dung_4', 'Mục đích *');
        updateDropdown(null, '5', 'noi_dung_5', 'Kết quả *');
        updateDropdown(null, '6', 'danh_gia_4', 'Hành động *');
    }

    function updateDropdown(prefix, grp, name, defLabel) {
        const sel = document.querySelector(`select[name="${name}"]`);
        if(!sel) return;
        
        const parentDiv = sel.closest('div[class^="col-"]');
        const lbl = parentDiv.querySelector('label');
        
        sel.innerHTML = '<option value="">-- Vui lòng chọn --</option>';
        if (lbl) lbl.textContent = defLabel;
        
        if (!prefix) { parentDiv.classList.add('hidden-field'); return; }

        const labelKey = prefix + grp + '1H';
        if (allDefaults[labelKey] && lbl) lbl.textContent = allDefaults[labelKey] + ' *';

        const opts = Object.keys(allDefaults).filter(k => k.length === 4 && k.startsWith(prefix + grp) && k.endsWith('M')).sort();
        
        if (opts.length === 0) { parentDiv.classList.add('hidden-field'); return; }
        
        parentDiv.classList.remove('hidden-field');
        opts.forEach(k => {
            const s = allDefaults[k];
            if (s) {
                const p = s.split(':');
                const val = p.length > 1 ? p[1] : p[0];
                sel.appendChild(new Option(val, p[0]));
            }
        });
    }

    function updateTagPool(prefix) {
        const sidebar = document.getElementById('tag-pool-sidebar-body');
        sidebar.innerHTML = '';
        if (!prefix) { sidebar.innerHTML = '<p class="text-muted small text-center mt-4">Vui lòng chọn Loại Báo cáo.</p>'; return; }
        
        let hasTags = false;
        // Global Tag
        const gM = prefix + '00M'; const gH = prefix + '00H';
        if (allDefaults[gM] || allDefaults[gH]) {
            sidebar.appendChild(createTagButton(allDefaults[gH] || "Việc quan trọng", allDefaults[gM], true));
            hasTags = true;
        }
        
        // Tab Tags
        const keys = Object.keys(allDefaults).filter(k => k.length === 4 && k.startsWith(prefix) && k.endsWith('H') && k.substring(1, 3) !== '00');
        keys.forEach(k => {
            const group = k.substring(1, 2);
            if (group === activeTagGroup) {
                const mKey = k.replace('H', 'M');
                sidebar.appendChild(createTagButton(allDefaults[k], allDefaults[mKey], false));
                hasTags = true;
            }
        });
        
        if (!hasTags) sidebar.innerHTML = '<p class="text-muted small text-center mt-4">Không có gợi ý.</p>';
    }

    function updateTabs(prefix) {
        const tabB = document.getElementById('li_tab_b');
        const tabC = document.getElementById('li_tab_c');
        const keys = Object.keys(allDefaults).filter(k => k.length === 3 && k.startsWith(prefix) && (k.endsWith('AH') || k.endsWith('BH') || k.endsWith('CH')));
        let hasB = false, hasC = false;
        
        keys.forEach(k => {
            const stt = k.substring(1, 2);
            const lbl = document.getElementById('lbl_tab_' + stt);
            if (lbl) lbl.textContent = allDefaults[k];
            if (stt === 'B') hasB = true;
            if (stt === 'C') hasC = true;
        });
        
        if (!hasB && tabB) tabB.classList.add('hidden-field');
        if (!hasC && tabC) tabC.classList.add('hidden-field');
    }

    // --- DRAFT AUTOSAVE ---
    function getDraftPayload() {
        const e1 = document.getElementById('editor_noi_dung_1');
        const e2 = document.getElementById('editor_noi_dung_2');
        const e3 = document.getElementById('editor_danh_gia_1');
        return {
            loai: (ddlLoaiBaoCao && ddlLoaiBaoCao.value) || '',
            ma_doi_tuong_kh: (document.getElementById('kh_ma_doi_tuong') && document.getElementById('kh_ma_doi_tuong').value) || '',
            kh_ten_day_du: (document.getElementById('kh_ten_day_du') && document.getElementById('kh_ten_day_du').value) || '',
            ref_diachi: (document.getElementById('ref_diachi') && document.getElementById('ref_diachi').textContent) || '',
            nv_bao_cao: (reportForm && reportForm.querySelector('select[name="nv_bao_cao"]') && reportForm.querySelector('select[name="nv_bao_cao"]').value) || '',
            ngay_bao_cao: (reportForm && reportForm.querySelector('input[name="ngay_bao_cao"]') && reportForm.querySelector('input[name="ngay_bao_cao"]').value) || '',
            nhansu_hengap_1: (reportForm && reportForm.querySelector('select[name="nhansu_hengap_1"]') && reportForm.querySelector('select[name="nhansu_hengap_1"]').value) || '',
            nhansu_hengap_2: (reportForm && reportForm.querySelector('select[name="nhansu_hengap_2"]') && reportForm.querySelector('select[name="nhansu_hengap_2"]').value) || '',
            noi_dung_4: (reportForm && reportForm.querySelector('select[name="noi_dung_4"]') && reportForm.querySelector('select[name="noi_dung_4"]').value) || '',
            noi_dung_5: (reportForm && reportForm.querySelector('select[name="noi_dung_5"]') && reportForm.querySelector('select[name="noi_dung_5"]').value) || '',
            danh_gia_4: (reportForm && reportForm.querySelector('select[name="danh_gia_4"]') && reportForm.querySelector('select[name="danh_gia_4"]').value) || '',
            e1: (e1 && e1.innerHTML) || '',
            e2: (e2 && e2.innerHTML) || '',
            e3: (e3 && e3.innerHTML) || '',
            ts: Date.now()
        };
    }
    function saveDraft() {
        try {
            const payload = getDraftPayload();
            if (!payload.loai && !payload.ma_doi_tuong_kh && !payload.e1 && !payload.e2 && !payload.e3) return;
            localStorage.setItem(NHAPLIEU_DRAFT_KEY, JSON.stringify(payload));
        } catch (err) { console.warn('Draft save failed', err); }
    }
    function clearDraft() {
        try { localStorage.removeItem(NHAPLIEU_DRAFT_KEY); } catch (e) {}
    }
    function applyRestoredDraft(draft) {
        if (!draft) return;
        const khMa = document.getElementById('kh_ma_doi_tuong');
        const khTen = document.getElementById('kh_ten_day_du');
        const refDiachi = document.getElementById('ref_diachi');
        if (khMa) khMa.value = draft.ma_doi_tuong_kh || '';
        if (khTen) khTen.value = draft.kh_ten_day_du || '';
        if (refDiachi) refDiachi.textContent = draft.ref_diachi || '...';
        const nvSel = reportForm && reportForm.querySelector('select[name="nv_bao_cao"]');
        const ngayInp = reportForm && reportForm.querySelector('input[name="ngay_bao_cao"]');
        if (nvSel && draft.nv_bao_cao) nvSel.value = draft.nv_bao_cao;
        if (ngayInp && draft.ngay_bao_cao) ngayInp.value = draft.ngay_bao_cao;
        const s4 = reportForm && reportForm.querySelector('select[name="noi_dung_4"]');
        const s5 = reportForm && reportForm.querySelector('select[name="noi_dung_5"]');
        const s6 = reportForm && reportForm.querySelector('select[name="danh_gia_4"]');
        if (s4 && draft.noi_dung_4) s4.value = draft.noi_dung_4;
        if (s5 && draft.noi_dung_5) s5.value = draft.noi_dung_5;
        if (s6 && draft.danh_gia_4) s6.value = draft.danh_gia_4;
        const ed1 = document.getElementById('editor_noi_dung_1');
        const ed2 = document.getElementById('editor_noi_dung_2');
        const ed3 = document.getElementById('editor_danh_gia_1');
        if (ed1 && draft.e1) ed1.innerHTML = draft.e1;
        if (ed2 && draft.e2) ed2.innerHTML = draft.e2;
        if (ed3 && draft.e3) ed3.innerHTML = draft.e3;
        if (draft.ma_doi_tuong_kh) {
            fetchReferenceCount(draft.ma_doi_tuong_kh);
            fetchNhansuDropdownData(draft.ma_doi_tuong_kh);
        }
        const nh1 = reportForm && reportForm.querySelector('select[name="nhansu_hengap_1"]');
        const nh2 = reportForm && reportForm.querySelector('select[name="nhansu_hengap_2"]');
        if (draft.ma_doi_tuong_kh && nh1 && nh2) {
            fetch(`/api/nhansu_ddl_by_khachhang/${draft.ma_doi_tuong_kh}`)
                .then(r => r.json())
                .then(data => {
                    if (data && data.length > 0) {
                        nh1.innerHTML = '<option value="">-- Chọn Nhân sự --</option>';
                        nh2.innerHTML = '<option value="">-- Chọn (Không bắt buộc) --</option>';
                        data.forEach(item => {
                            nh1.appendChild(new Option(item.text, item.id));
                            nh2.appendChild(new Option(item.text, item.id));
                        });
                        if (draft.nhansu_hengap_1) nh1.value = draft.nhansu_hengap_1;
                        if (draft.nhansu_hengap_2) nh2.value = draft.nhansu_hengap_2;
                    }
                }).catch(console.error);
        }
    }

    // --- EVENTS ---
    if(ddlLoaiBaoCao) {
        ddlLoaiBaoCao.addEventListener('change', function() {
            const prefix = this.value;
            const sidebar = document.getElementById('tag-pool-sidebar-body');
            allDefaults = {};
            resetTabsAndEditors();
            sidebar.innerHTML = '<p class="text-muted small text-center mt-4"><i class="fas fa-spinner fa-spin"></i> Đang tải...</p>';
            if (prefix) {
                fetch(`/api/defaults/${prefix}`).then(r => r.json()).then(d => {
                    allDefaults = d;
                    updateTabs(prefix);
                    updateTagPool(prefix);
                    updateDropdown(prefix, '4', 'noi_dung_4', 'Mục đích *');
                    updateDropdown(prefix, '5', 'noi_dung_5', 'Kết quả *');
                    updateDropdown(prefix, '6', 'danh_gia_4', 'Hành động *');
                    document.querySelectorAll('.scenario-card').forEach(function(b) {
                        b.classList.toggle('active', b.getAttribute('data-loai') === prefix);
                    });
                    if (window.__restoreNhaplieuDraft) {
                        applyRestoredDraft(window.__restoreNhaplieuDraft);
                        window.__restoreNhaplieuDraft = null;
                    }
                }).catch(e => {
                    console.error(e);
                    sidebar.innerHTML = '<p class="text-danger small text-center mt-4">Lỗi kết nối.</p>';
                    if (window.__restoreNhaplieuDraft) {
                        applyRestoredDraft(window.__restoreNhaplieuDraft);
                        window.__restoreNhaplieuDraft = null;
                    }
                });
            } else {
                updateTagPool('');
                document.querySelectorAll('.scenario-card').forEach(function(b) { b.classList.remove('active'); });
                if (window.__restoreNhaplieuDraft) {
                    applyRestoredDraft(window.__restoreNhaplieuDraft);
                    window.__restoreNhaplieuDraft = null;
                }
            }
        });
    }

    // Tab Change
    document.querySelectorAll('button[data-bs-toggle="pill"]').forEach(t => {
        t.addEventListener('shown.bs.tab', function(e) {
            const id = e.target.id;
            if (id === 'tab-a-tab') { activeEditorId = 'editor_noi_dung_1'; activeTagGroup = '1'; }
            else if (id === 'tab-b-tab') { activeEditorId = 'editor_noi_dung_2'; activeTagGroup = '2'; }
            else { activeEditorId = 'editor_danh_gia_1'; activeTagGroup = '3'; }
            
            if(ddlLoaiBaoCao) updateTagPool(ddlLoaiBaoCao.value);
        });
    });

    // Form Submit (Map Editor -> Hidden + loading, clear draft)
    if(reportForm) {
        reportForm.addEventListener('submit', function(e) {
            try {
                document.getElementById('hidden_danh_gia_2').value = document.getElementById('editor_noi_dung_1').innerHTML;
                document.getElementById('hidden_noi_dung_2').value = document.getElementById('editor_noi_dung_2').innerHTML;
                document.getElementById('hidden_noi_dung_1').value = document.getElementById('editor_danh_gia_1').innerHTML;
                clearDraft();
                var btn = document.getElementById('btn-submit-nhaplieu');
                if (btn) {
                    btn.disabled = true;
                    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Đang lưu...';
                }
            } catch (err) {
                e.preventDefault();
                if (window.Swal) window.Swal.fire({ icon: 'error', title: 'Lỗi', text: 'Không lấy được nội dung editor.' });
                else alert('Lỗi lấy nội dung.');
            }
        });
    }

    // Scenario cards: chọn kịch bản thay dropdown
    document.querySelectorAll('.scenario-card').forEach(function(btn) {
        btn.addEventListener('click', function() {
            const loai = this.getAttribute('data-loai');
            if (!loai || !ddlLoaiBaoCao) return;
            ddlLoaiBaoCao.value = loai;
            ddlLoaiBaoCao.dispatchEvent(new Event('change'));
            document.querySelectorAll('.scenario-card').forEach(function(b) { b.classList.remove('active'); });
            this.classList.add('active');
        });
    });

    // Focus mode: Chế độ viết
    const btnFocusMode = document.getElementById('btn-focus-mode');
    if (btnFocusMode) {
        btnFocusMode.addEventListener('click', function() {
            document.body.classList.toggle('nhap-lieu-focus-mode');
            const isFocus = document.body.classList.contains('nhap-lieu-focus-mode');
            this.innerHTML = isFocus ? '<i class="fas fa-compress-alt me-1"></i> Thoát chế độ viết' : '<i class="fas fa-expand-alt me-1"></i> Chế độ viết';
        });
    }

    // Init
    resetTabsAndEditors();
    updateTagPool('');

    // Draft: restore prompt on load
    try {
        const raw = localStorage.getItem(NHAPLIEU_DRAFT_KEY);
        if (raw) {
            const draft = JSON.parse(raw);
            if (draft && (draft.loai || draft.e1 || draft.e2 || draft.e3)) {
                if (window.Swal) {
                    Swal.fire({
                        title: 'Khôi phục bản nháp?',
                        text: 'Có bản nháp chưa lưu. Bạn có muốn khôi phục?',
                        icon: 'question',
                        showCancelButton: true,
                        confirmButtonText: 'Khôi phục',
                        cancelButtonText: 'Bỏ qua',
                        confirmButtonColor: '#4318FF'
                    }).then(function(res) {
                        if (res.isConfirmed && draft.loai && ddlLoaiBaoCao) {
                            window.__restoreNhaplieuDraft = draft;
                            ddlLoaiBaoCao.value = draft.loai;
                            ddlLoaiBaoCao.dispatchEvent(new Event('change'));
                        } else if (res.isConfirmed) {
                            applyRestoredDraft(draft);
                        }
                        if (!res.isConfirmed) clearDraft();
                    });
                } else {
                    if (confirm('Khôi phục bản nháp?')) {
                        if (draft.loai && ddlLoaiBaoCao) {
                            window.__restoreNhaplieuDraft = draft;
                            ddlLoaiBaoCao.value = draft.loai;
                            ddlLoaiBaoCao.dispatchEvent(new Event('change'));
                        } else { applyRestoredDraft(draft); }
                    } else { clearDraft(); }
                }
            }
        }
    } catch (e) { clearDraft(); }

    // Draft: autosave every 45s
    draftSaveTimer = setInterval(saveDraft, DRAFT_AUTOSAVE_INTERVAL_MS);
});