/**
 * Training Dashboard (Thư viện) - Alpine.js homeApp
 */
function homeApp() {
    return {
        query: '',
        results: [],
        loading: true,
        loadError: false,
        searchLoading: false,
        mandatoryCourses: [],
        categories: [
            { id: 1, name: 'Kiến thức Sản phẩm', icon: '<i class="fas fa-box-open"></i>', bg: 'https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?w=500&q=80', count: 0 },
            { id: 2, name: 'Kỹ thuật chuyên sâu', icon: '<i class="fas fa-microchip"></i>', bg: 'https://images.unsplash.com/photo-1581092580497-e0d23cbdf1dc?w=500&q=80', count: 0 },
            { id: 3, name: 'Giới thiệu về STDD và năng lực cung cấp', icon: '<i class="fas fa-building"></i>', bg: 'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=500&q=80', count: 0 },
            { id: 4, name: 'Kỹ năng mềm', icon: '<i class="fas fa-users"></i>', bg: 'https://images.unsplash.com/photo-1552664730-d307ca884978?w=500&q=80', count: 0 },
            { id: 5, name: 'Quy trình & Vận hành', icon: '<i class="fas fa-project-diagram"></i>', bg: 'https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=500&q=80', count: 0 },
            { id: 6, name: 'Công cụ & Catalogue', icon: '<i class="fas fa-book"></i>', bg: 'https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=500&q=80', count: 0 },
            { id: 7, name: 'Quy định & chính sách', icon: '<i class="fas fa-balance-scale"></i>', bg: 'https://images.unsplash.com/photo-1589829085413-56de8ae18c73?w=500&q=80', count: 0 },
            { id: 8, name: 'Văn hóa & phát triển cá nhân', icon: '<i class="fas fa-seedling"></i>', bg: 'https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?w=500&q=80', count: 0 }
        ],

        async init() {
            var self = this;
            self.loading = true;
            self.loadError = false;
            try {
                var res = await fetch('/api/training/dashboard_v2');
                if (!res.ok) throw new Error('Máy chủ phản hồi lỗi.');
                var data = await res.json();
                var mandatories = [];
                self.categories.forEach(function(c) { c.count = 0; });

                for (var catName in data) {
                    if (!data.hasOwnProperty(catName)) continue;
                    var subCats = data[catName];
                    var totalInCat = 0;
                    for (var key in subCats) {
                        if (!subCats.hasOwnProperty(key)) continue;
                        var list = subCats[key];
                        totalInCat += list.length;
                        list.forEach(function(c) {
                            if (c.is_mandatory && !mandatories.some(function(m) { return m.id === c.id; })) {
                                mandatories.push(c);
                            }
                        });
                    }
                    var target = self.categories.find(function(c) {
                        var cleanUI = c.name.toLowerCase().replace(/\s+/g, ' ').trim();
                        var cleanDB = catName.toLowerCase().replace(/\s+/g, ' ').trim();
                        return cleanUI === cleanDB || cleanDB.indexOf(cleanUI) !== -1 || cleanUI.indexOf(cleanDB) !== -1;
                    });
                    if (target) target.count = totalInCat;
                }
                self.mandatoryCourses = mandatories;
                self.loadError = false;
            } catch (e) {
                console.error('Lỗi tải dashboard:', e);
                self.loadError = true;
                if (window.Swal) {
                    window.Swal.fire({
                        icon: 'error',
                        title: 'Không tải được Thư viện',
                        text: (e && e.message) ? e.message : 'Vui lòng thử lại sau.',
                        confirmButtonText: 'Thử lại'
                    }).then(function(r) {
                        if (r.isConfirmed) self.init();
                    });
                } else {
                    alert('Lỗi tải dữ liệu. Vui lòng thử lại.');
                }
            } finally {
                self.loading = false;
            }
        },

        async search() {
            if (this.query.length < 2) {
                this.results = [];
                return;
            }
            this.searchLoading = true;
            try {
                var res = await fetch('/api/training/search?q=' + encodeURIComponent(this.query));
                if (!res.ok) throw new Error('Tìm kiếm thất bại.');
                var data = await res.json();
                this.results = Array.isArray(data) ? data : [];
                if (this.results.length === 0 && window.Swal) {
                    window.Swal.fire({ toast: true, position: 'top-end', icon: 'info', title: 'Không tìm thấy kết quả.', showConfirmButton: false, timer: 2500, timerProgressBar: true });
                }
            } catch (e) {
                this.results = [];
                if (window.Swal) {
                    window.Swal.fire({ toast: true, position: 'top-end', icon: 'error', title: 'Lỗi tìm kiếm. Thử lại.', showConfirmButton: false, timer: 3000, timerProgressBar: true });
                }
            } finally {
                this.searchLoading = false;
            }
        }
    };
}
