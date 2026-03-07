/**
 * KPI Evaluation - Chi tiết tiêu chí, chốt KPI, modal dữ liệu.
 * Cần có trong DOM: #kpi-evaluation-config (data-api-detail, data-evaluate-url, data-target-user, data-year, data-month).
 */
(function () {
    'use strict';

    var detailData = [];
    var detailColumns = [];
    var currentPage = 1;
    var rowsPerPage = 20;
    var lastDetailParams = null;

    function showToast(icon, title) {
        if (window.Swal) window.Swal.fire({ toast: true, position: 'top-end', icon: icon, title: title || '', showConfirmButton: false, timer: 3000, timerProgressBar: true });
        else alert(title);
    }
    function setChotButtonLoading(loading) {
        var btn = document.getElementById('kpiChotBtn');
        var icon = document.getElementById('kpiChotIcon');
        var text = document.getElementById('kpiChotText');
        if (!btn) return;
        if (loading) {
            btn.disabled = true;
            if (icon) icon.innerHTML = '<i class="fas fa-spinner fa-spin fa-lg" aria-hidden="true"></i>';
            if (text) text.textContent = 'Đang tính...';
        } else {
            btn.disabled = false;
            if (icon) icon.innerHTML = '<i class="fas fa-robot fa-lg" aria-hidden="true"></i>';
            if (text) text.textContent = 'CHỐT KPI';
        }
    }

    function getConfig() {
        var el = document.getElementById('kpi-evaluation-config');
        if (!el) return {};
        return {
            apiDetail: el.getAttribute('data-api-detail') || '',
            evaluateUrl: el.getAttribute('data-evaluate-url') || '',
            targetUser: el.getAttribute('data-target-user') || '',
            year: parseInt(el.getAttribute('data-year'), 10) || new Date().getFullYear(),
            month: parseInt(el.getAttribute('data-month'), 10) || 1
        };
    }

    window.showKPIDetail = function (criteriaId, criteriaName, targetUser, year, month) {
        var cfg = getConfig();
        var apiUrl = cfg.apiDetail || '/api/kpi/detail';
        lastDetailParams = { criteriaId: criteriaId, criteriaName: criteriaName, targetUser: targetUser, year: year, month: month };

        var summaryEl = document.getElementById('kpiDetailSummary');
        var errorEl = document.getElementById('kpiDetailError');
        var errorTextEl = document.getElementById('kpiDetailErrorText');
        var tableWrap = document.getElementById('kpiDetailTableWrap');
        var emptyEl = document.getElementById('kpiDetailEmpty');
        var paginationWrap = document.getElementById('kpiDetailPaginationWrap');

        document.getElementById('kpiDetailModalLabel').innerText = criteriaName;
        if (summaryEl) { summaryEl.classList.remove('d-none'); summaryEl.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Đang trích xuất dữ liệu...'; }
        if (errorEl) errorEl.classList.add('d-none');
        if (tableWrap) tableWrap.classList.add('d-none');
        if (emptyEl) emptyEl.classList.add('d-none');
        if (paginationWrap) paginationWrap.classList.add('d-none');

        var myModal = new bootstrap.Modal(document.getElementById('kpiDetailModal'));
        myModal.show();

        var url = apiUrl + '?criteria_id=' + encodeURIComponent(criteriaId) + '&target_user=' + encodeURIComponent(targetUser) + '&year=' + year + '&month=' + month;
        fetch(url)
            .then(function (response) { return response.json(); })
            .then(function (res) {
                if (res.success && res.data) {
                    if (summaryEl) { summaryEl.innerHTML = res.data.summary || 'Không có bảng kê chi tiết.'; }
                    detailColumns = res.data.columns || [];
                    detailData = res.data.rows || [];
                    currentPage = 1;
                    window.renderTableHeader();
                    window.renderTableBody();
                    if (detailData.length === 0) {
                        if (summaryEl) summaryEl.classList.add('d-none');
                        if (tableWrap) tableWrap.classList.add('d-none');
                        if (paginationWrap) paginationWrap.classList.add('d-none');
                        if (emptyEl) emptyEl.classList.remove('d-none');
                    } else {
                        if (tableWrap) tableWrap.classList.remove('d-none');
                        if (paginationWrap) paginationWrap.classList.remove('d-none');
                        if (emptyEl) emptyEl.classList.add('d-none');
                    }
                } else {
                    if (summaryEl) summaryEl.classList.add('d-none');
                    if (errorEl && errorTextEl) { errorTextEl.textContent = res.message || 'Không thể tải dữ liệu.'; errorEl.classList.remove('d-none'); }
                    if (tableWrap) tableWrap.classList.add('d-none');
                    if (paginationWrap) paginationWrap.classList.add('d-none');
                    if (emptyEl) emptyEl.classList.add('d-none');
                }
            })
            .catch(function () {
                if (summaryEl) summaryEl.classList.add('d-none');
                if (errorEl && errorTextEl) { errorTextEl.textContent = 'Lỗi kết nối. Kiểm tra mạng và thử lại.'; errorEl.classList.remove('d-none'); }
                if (tableWrap) tableWrap.classList.add('d-none');
            });
    };

    function retryKpiDetail() {
        if (lastDetailParams) window.showKPIDetail(lastDetailParams.criteriaId, lastDetailParams.criteriaName, lastDetailParams.targetUser, lastDetailParams.year, lastDetailParams.month);
    }

    window.renderTableHeader = function () {
        if (detailColumns.length === 0) return;
        var theadHtml = '';
        detailColumns.forEach(function (col) {
            var align = (col.type === 'currency' || col.type === 'number') ? 'text-end' : 'text-start';
            theadHtml += '<th class="' + align + ' py-3 px-3">' + col.label + '</th>';
        });
        document.getElementById('kpiDetailHead').innerHTML = theadHtml;
    };

    window.renderTableBody = function () {
        var tbody = document.getElementById('kpiDetailBody');
        var totalPages = Math.ceil(detailData.length / rowsPerPage);
        var startIdx = (currentPage - 1) * rowsPerPage;
        var endIdx = startIdx + rowsPerPage;
        var paginatedData = detailData.slice(startIdx, endIdx);

        var tbodyHtml = '';
        paginatedData.forEach(function (row) {
            tbodyHtml += '<tr>';
            detailColumns.forEach(function (col) {
                var val = row[col.field];
                var align = 'text-start';
                if (col.type === 'currency' || col.type === 'number') {
                    var numVal = parseFloat(val) || 0;
                    val = new Intl.NumberFormat('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(numVal);
                    align = 'text-end fw-bold';
                }
                tbodyHtml += '<td class="' + align + ' py-3 px-3">' + val + '</td>';
            });
            tbodyHtml += '</tr>';
        });
        tbody.innerHTML = tbodyHtml;
        var pageInfoEl = document.getElementById('pageInfo');
        if (pageInfoEl) pageInfoEl.innerText = 'Dòng ' + (startIdx + 1) + ' - ' + Math.min(endIdx, detailData.length) + ' / ' + detailData.length;

        var pageHtml = '';
        if (totalPages > 1) {
            for (var i = 1; i <= totalPages; i++) {
                pageHtml += '<li class="page-item ' + (currentPage === i ? 'active' : '') + '"><a class="page-link" href="#" onclick="changePage(' + i + '); return false;">' + i + '</a></li>';
            }
        }
        var paginationEl = document.getElementById('kpiPagination');
        if (paginationEl) paginationEl.innerHTML = pageHtml;
    };

    document.addEventListener('DOMContentLoaded', function () {
        var retryBtn = document.getElementById('kpiDetailRetryBtn');
        if (retryBtn) retryBtn.addEventListener('click', retryKpiDetail);
    });

    window.changePage = function (page) {
        currentPage = page;
        window.renderTableBody();
    };

    window.evaluateKPI = function (userCode, year, month) {
        var cfg = getConfig();
        var url = cfg.evaluateUrl || '/api/kpi/evaluate';
        setChotButtonLoading(true);
        fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_code: userCode, year: year, month: month })
        })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.success) {
                    showToast('success', data.message || 'Chốt KPI thành công!');
                    setTimeout(function () { location.reload(); }, 1800);
                } else {
                    setChotButtonLoading(false);
                    showToast('error', data.message || 'Lỗi khi chốt KPI');
                }
            })
            .catch(function () {
                setChotButtonLoading(false);
                showToast('error', 'Lỗi kết nối. Vui lòng thử lại.');
            });
    };

    window.evaluateKPIFromConfig = function () {
        var cfg = getConfig();
        if (typeof window.Swal !== 'undefined') {
            window.Swal.fire({
                title: 'Chốt KPI',
                html: 'Tính lại điểm KPI cho <strong>' + (cfg.targetUser || '') + '</strong> tháng ' + cfg.month + '/' + cfg.year + '?',
                icon: 'question',
                showCancelButton: true,
                confirmButtonText: 'Đồng ý',
                cancelButtonText: 'Hủy',
                customClass: { confirmButton: 'btn btn-primary rounded-pill px-4', cancelButton: 'btn btn-light rounded-pill px-4' }
            }).then(function (result) {
                if (result.isConfirmed) window.evaluateKPI(cfg.targetUser, cfg.year, cfg.month);
            });
        } else {
            if (confirm('Tính lại điểm KPI tháng ' + cfg.month + '/' + cfg.year + '?')) window.evaluateKPI(cfg.targetUser, cfg.year, cfg.month);
        }
    };

    window.handleKPIClick = function (rowData, targetUser, year, month) {
        try {
            var isHigherBetter = rowData.IsHigherBetter;
            var unit = rowData.Unit || '';
            var formula = rowData.CalculationFormula || 'Chưa cập nhật hướng dẫn cho tiêu chí này.';

            var thresholdHtml = '<div class="mt-4 p-3 rounded-4" style="background: #f8f9fa; border: 1px solid #e9ecef;">' +
                '<p class="mb-3 fw-bold d-flex align-items-center" style="color: #764ba2;"><i class="fas fa-bullseye me-2"></i>Định mức đạt điểm (' + unit + ')</p>' +
                '<div class="table-responsive"><table class="table table-borderless mb-0" style="font-size: 0.85rem;">' +
                '<thead><tr class="text-muted border-bottom" style="font-size: 0.75rem;"><th class="pb-2">MỨC ĐIỂM</th><th class="pb-2 text-end">ĐIỀU KIỆN</th></tr></thead><tbody class="text-dark">' +
                '<tr style="border-bottom: 1px dashed #dee2e6;"><td class="py-2"><span class="badge rounded-pill bg-success px-3">100đ</span></td><td class="py-2 text-end fw-bold">' + (isHigherBetter ? '≥' : '≤') + ' ' + rowData.Threshold_100 + '</td></tr>' +
                '<tr style="border-bottom: 1px dashed #dee2e6;"><td class="py-2"><span class="badge rounded-pill bg-primary px-3">70đ</span></td><td class="py-2 text-end fw-bold">' + (isHigherBetter ? '≥' : '≤') + ' ' + rowData.Threshold_70 + '</td></tr>' +
                '<tr style="border-bottom: 1px dashed #dee2e6;"><td class="py-2"><span class="badge rounded-pill bg-warning px-3">50đ</span></td><td class="py-2 text-end fw-bold">' + (isHigherBetter ? '≥' : '≤') + ' ' + rowData.Threshold_50 + '</td></tr>' +
                '<tr><td class="py-2"><span class="badge rounded-pill bg-danger px-3">0đ</span></td><td class="py-2 text-end fw-bold">' + (isHigherBetter ? '<' : '>') + ' ' + rowData.Threshold_0 + '</td></tr>' +
                '</tbody></table></div></div>';

            if (typeof window.Swal === 'undefined') {
                window.showKPIDetail(rowData.CriteriaID, rowData.CriteriaName, targetUser, year, month);
                return;
            }

            window.Swal.fire({
                title: '<div class="mt-2" style="font-size: 1.25rem; color: #2d3748; letter-spacing: -0.5px;">' + rowData.CriteriaName + '</div>',
                html: '<div class="text-start px-2 py-1" style="line-height: 1.6;">' +
                    '<div class="mb-4"><label class="text-uppercase small fw-bold text-muted mb-2 d-block" style="letter-spacing: 1px;"><i class="fas fa-info-circle me-1"></i> Cách thức tính toán</label>' +
                    '<div class="p-3 rounded-4 bg-white shadow-sm border" style="font-size: 0.95rem; color: #4a5568;">' + formula + '</div></div>' +
                    thresholdHtml + '</div>',
                showCancelButton: true,
                confirmButtonText: '<i class="fas fa-search-plus me-2"></i>Xem dữ liệu chi tiết',
                cancelButtonText: 'Đóng',
                buttonsStyling: false,
                customClass: {
                    popup: 'rounded-5 shadow-lg border-0',
                    confirmButton: 'btn btn-primary px-4 py-2 rounded-pill mx-2 shadow-sm',
                    cancelButton: 'btn btn-light px-4 py-2 rounded-pill mx-2 border'
                },
                width: '550px',
                background: '#ffffff',
                showClass: { popup: 'animate__animated animate__fadeInUp animate__faster' }
            }).then(function (result) {
                if (result.isConfirmed) {
                    window.showKPIDetail(rowData.CriteriaID, rowData.CriteriaName, targetUser, year, month);
                }
            });
        } catch (e) {
            console.error('Lỗi popup:', e);
            window.showKPIDetail(rowData.CriteriaID, rowData.CriteriaName, targetUser, year, month);
        }
    };
})();
