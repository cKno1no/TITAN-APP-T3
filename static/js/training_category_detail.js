/**
 * Training Category Detail - Alpine.js categoryApp
 */
function categoryApp() {
    return {
        catName: '',
        subCategories: [],
        activeSubCat: 'all',
        totalCourses: 0,
        isLoading: true,
        loadError: false,

        async init() {
            var self = this;
            var path = window.location.pathname.replace(/\/$/, '');
            self.catName = decodeURIComponent(path.split('/').pop());
            self.isLoading = true;
            self.loadError = false;

            try {
                var res = await fetch('/api/training/dashboard_v2');
                if (!res.ok) throw new Error('Máy chủ phản hồi lỗi.');
                var data = await res.json();
                var searchCat = self.catName.toLowerCase().replace(/\s+/g, ' ').trim();

                var currentCatKey = Object.keys(data).find(function(k) {
                    var apiCat = k.toLowerCase().replace(/\s+/g, ' ').trim();
                    return apiCat === searchCat;
                });
                if (!currentCatKey) {
                    currentCatKey = Object.keys(data).find(function(k) {
                        var apiCat = k.toLowerCase().replace(/\s+/g, ' ').trim();
                        return apiCat.indexOf(searchCat) !== -1 || searchCat.indexOf(apiCat) !== -1;
                    });
                }

                if (currentCatKey && data[currentCatKey]) {
                    self.catName = currentCatKey;
                    var rawSubCats = data[currentCatKey];
                    var processedSubs = {};

                    for (var subName in rawSubCats) {
                        if (!rawSubCats.hasOwnProperty(subName)) continue;
                        var cleanSubName = (!subName || subName === 'null' || String(subName).trim() === '') ? 'Chuyên đề chung' : String(subName).trim();
                        if (!processedSubs[cleanSubName]) processedSubs[cleanSubName] = [];
                        var courses = rawSubCats[subName].map(function(c) {
                            return {
                                id: c.id || c.CourseID,
                                title: c.title || c.Title || 'Khóa học không tên',
                                desc: c.desc || c.Description || '',
                                thumbnail: c.thumbnail || c.ThumbnailUrl,
                                lessons: c.lessons || c.TotalLessons || 0,
                                xp: c.xp || c.XP_Reward || 300
                            };
                        });
                        processedSubs[cleanSubName].push.apply(processedSubs[cleanSubName], courses);
                    }

                    self.subCategories = Object.keys(processedSubs).map(function(name) {
                        return { name: name, courses: processedSubs[name] };
                    });
                    self.subCategories.sort(function(a, b) { return b.courses.length - a.courses.length; });
                    self.totalCourses = self.subCategories.reduce(function(acc, sub) { return acc + sub.courses.length; }, 0);
                    self.loadError = false;
                } else {
                    self.subCategories = [];
                    self.totalCourses = 0;
                }
            } catch (e) {
                console.error('Lỗi fetch dữ liệu Detail:', e);
                self.loadError = true;
                if (window.Swal) {
                    window.Swal.fire({
                        icon: 'error',
                        title: 'Không tải được danh mục',
                        text: (e && e.message) ? e.message : 'Vui lòng thử lại sau.',
                        confirmButtonText: 'Thử lại'
                    }).then(function(r) {
                        if (r.isConfirmed) self.init();
                    });
                } else {
                    alert('Lỗi tải dữ liệu. Vui lòng thử lại.');
                }
            } finally {
                self.isLoading = false;
            }
        }
    };
}
