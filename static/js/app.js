/**
 * Titan OS - Global app script
 * CSRF, form helpers, TitanUtils, theme & mailbox (Alpine).
 * APP_CONFIG phải đã được set trong base.html (Jinja) trước khi load file này.
 */

(function () {
    'use strict';

    var CONFIG = window.APP_CONFIG || {
        DIVISOR: 1000000,
        LOCALE: 'vi-VN',
        CURRENCY_SUFFIX: ' tr',
        DATE_FMT: 'DD/MM/YYYY'
    };

    // --- TitanUtils (format tiền, số, ngày) ---
    window.TitanUtils = {
        formatCurrency: function (val) {
            if (val === undefined || val === null || val === '') return '0';
            var num = parseFloat(val);
            if (isNaN(num)) return '0';
            var reducedVal = num / CONFIG.DIVISOR;
            var formatted = new Intl.NumberFormat(CONFIG.LOCALE, {
                minimumFractionDigits: 0,
                maximumFractionDigits: 1
            }).format(reducedVal);
            return formatted + CONFIG.CURRENCY_SUFFIX;
        },
        formatNumber: function (val) {
            if (val === undefined || val === null) return '0';
            return new Intl.NumberFormat(CONFIG.LOCALE).format(val);
        },
        formatDate: function (dateStr) {
            if (!dateStr) return '';
            try {
                var d = new Date(dateStr);
                return d.toLocaleDateString(CONFIG.LOCALE);
            } catch (e) {
                return dateStr;
            }
        }
    };
    window.fmtMoney = window.TitanUtils.formatCurrency;
    window.fmtNum = window.TitanUtils.formatNumber;

    // --- HTMX: gắn CSRF token cho mọi request ---
    document.addEventListener('htmx:configRequest', function (event) {
        var meta = document.querySelector('meta[name="csrf-token"]');
        if (meta) event.detail.headers['X-CSRFToken'] = meta.content;
    });

    // --- Fetch: tự động gắn CSRF cho POST/PUT/DELETE ---
    var originalFetch = window.fetch;
    window.fetch = function () {
        var options = arguments[1] || {};
        if (options.method && ['POST', 'PUT', 'DELETE'].includes(options.method.toUpperCase())) {
            options.headers = options.headers || {};
            var meta = document.querySelector('meta[name="csrf-token"]');
            if (meta) options.headers['X-CSRFToken'] = meta.content;
            arguments[1] = options;
        }
        return originalFetch.apply(this, arguments);
    };

    // --- jQuery: CSRF cho $.ajax + tự chèn hidden vào form POST ---
    if (typeof $ !== 'undefined') {
        $(document).ready(function () {
            $.ajaxSetup({
                beforeSend: function (xhr, settings) {
                    if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                        var meta = document.querySelector('meta[name="csrf-token"]');
                        if (meta) xhr.setRequestHeader('X-CSRFToken', meta.content);
                    }
                }
            });

            var csrfToken = $('meta[name="csrf-token"]').attr('content');
            if (csrfToken) {
                $('form').each(function () {
                    var method = $(this).attr('method');
                    if (method && method.toUpperCase() === 'POST') {
                        if ($(this).find('input[name="csrf_token"]').length === 0) {
                            $(this).prepend('<input type="hidden" name="csrf_token" value="' + csrfToken + '">');
                        }
                    }
                });
            }
        });
    }

    // --- Alpine: global app (theme) ---
    window.globalApp = function () {
        return {
            theme: localStorage.getItem('titan_theme') || 'light',
            initApp: function () { this.setTheme(this.theme, false); },
            setTheme: function (themeName, saveToDb) {
                if (saveToDb === undefined) saveToDb = true;
                this.theme = themeName;
                localStorage.setItem('titan_theme', themeName);
                if (saveToDb) {
                    fetch('/api/user/set_theme', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ theme: themeName })
                    }).catch(function (e) { console.error('set_theme', e); });
                }
            }
        };
    };

    // --- Alpine: mailbox widget ---
    window.mailboxWidget = function () {
        return {
            mails: [],
            unreadCount: 0,
            loading: false,
            init: function () { this.fetchMails(true); },
            fetchMails: function (badgeOnly) {
                if (!badgeOnly) this.loading = true;
                var self = this;
                fetch('/api/mailbox')
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        self.mails = data.map(function (m) { return Object.assign({}, m, { processing: false }); });
                        self.unreadCount = data.filter(function (m) { return !m.IsClaimed; }).length;
                        self.loading = false;
                    })
                    .catch(function () { self.loading = false; });
            },
            loadMailbox: function () { this.fetchMails(false); },
            getIcon: function (mail) {
                if (mail.Total_Coins > 0) return 'fa-coins text-warning';
                if (mail.Total_XP > 0) return 'fa-star text-info';
                return 'fa-envelope';
            },
            formatDate: function (dateStr) {
                if (!dateStr) return 'Vừa xong';
                try { return new Date(dateStr).toLocaleString('vi-VN'); } catch (e) { return dateStr; }
            },
            claimReward: function (mail) {
                var self = this;
                mail.processing = true;
                fetch('/api/mailbox/claim', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ mail_id: mail.MailID || mail.id })
                })
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        mail.processing = false;
                        if (data.success) {
                            mail.IsClaimed = true;
                            self.unreadCount = Math.max(0, self.unreadCount - 1);
                            self.handleEffects(data);
                        } else {
                            if (window.Swal) window.Swal.fire({ icon: 'error', title: 'Oops...', text: data.msg });
                        }
                    });
            },
            handleEffects: function (data) {
                if (typeof fireFireworks === 'function') fireFireworks();
                if (data.level_up && window.Swal) {
                    window.Swal.fire({
                        html: '<div class="level-up-content"><div style="font-size: 1.2rem; color: #E65100; font-weight: 700;">Level Up!</div><div style="font-size: 6rem; font-weight: 900; color: #4318FF;">' + data.new_level + '</div><div class="badge rounded-pill bg-warning text-dark px-4 py-2 mt-3"><i class="fas fa-coins me-2"></i>+' + data.coins_earned + ' Coins</div></div>',
                        customClass: { popup: 'round-glow-popup', confirmButton: 'btn btn-primary rounded-pill px-4 fw-bold mt-3 shadow-lg' },
                        backdrop: 'rgba(11, 20, 55, 0.8) url("https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExNXBpeGcwanhwNDA2d3Ntd2VlazNqZm00c3JhaWRtemN0YmpuMTIwNCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/9qKNE5R7PE7VZjJ4La/giphy.gif") left top no-repeat',
                        timer: 5000,
                        timerProgressBar: true
                    });
                } else if (window.Swal) {
                    var Toast = window.Swal.mixin({ toast: true, position: 'top-end', showConfirmButton: false, timer: 3000 });
                    Toast.fire({ icon: 'success', title: 'Đã nhận quà thành công!' });
                }
            }
        };
    };
})();
