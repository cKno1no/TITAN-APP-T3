/**
 * Hall of Fame - Góc Kể Chuyện - Quill, Select2, form submit
 */
(function() {
    var quill;

    function showToast(icon, title) {
        if (window.Swal) {
            window.Swal.fire({ toast: true, position: 'top-end', icon: icon, title: title || '', showConfirmButton: false, timer: 3000, timerProgressBar: true });
        } else {
            alert(title);
        }
    }

    function formatUser(state) {
        if (!state.id) return state.text;
        var shortname = $(state.element).data('shortname');
        var fullname = $(state.element).data('fullname');
        var usercode = $(state.element).data('usercode');
        var avatarLetter = shortname ? shortname.charAt(0).toUpperCase() : '?';
        var $state = $(
            '<div class="user-option-row">' +
            '<div class="user-avatar-small">' + avatarLetter + '</div>' +
            '<div class="user-meta">' +
            '<span class="user-main-name">' + (shortname || '') + '</span>' +
            '<span class="user-sub-info">' + (fullname || '') + ' (#' + (usercode || '') + ')</span>' +
            '</div></div>'
        );
        return $state;
    }

    window.previewImages = function(input) {
        var container = document.getElementById('galleryPreview');
        if (!container) return;
        container.innerHTML = '';
        if (input.files) {
            if (input.files.length > 5) {
                showToast('warning', 'Tối đa 5 ảnh thôi nhé!');
                input.value = '';
                return;
            }
            Array.from(input.files).forEach(function(file, index) {
                var reader = new FileReader();
                reader.onload = function(e) {
                    var div = document.createElement('div');
                    div.className = 'polaroid';
                    var rotate = (Math.random() * 6 - 3).toFixed(1);
                    div.style.transform = 'rotate(' + rotate + 'deg)';
                    div.innerHTML = '<img src="' + e.target.result + '">';
                    container.appendChild(div);
                };
                reader.readAsDataURL(file);
            });
        }
    };

    function init() {
        var editorEl = document.getElementById('editor-container');
        if (!editorEl) return;

        quill = new Quill('#editor-container', {
            theme: 'snow',
            modules: {
                toolbar: [['bold', 'italic', 'underline'], [{ 'list': 'ordered' }, { 'list': 'bullet' }], ['clean']]
            },
            placeholder: 'Ngày ấy, chúng tôi đã...'
        });

        if (typeof $ !== 'undefined' && $('#userSelect').length) {
            $('#userSelect').select2({
                templateResult: formatUser,
                templateSelection: formatUser,
                width: '100%',
                placeholder: 'Gõ tên hoặc mã nhân viên...',
                allowClear: true
            });
        }

        var form = document.getElementById('storyForm');
        if (form) {
            form.onsubmit = function() {
                var html = document.querySelector('.ql-editor') ? document.querySelector('.ql-editor').innerHTML : '';
                if (quill && quill.getText().trim().length === 0) {
                    showToast('warning', 'Hãy viết vài dòng nhé!');
                    return false;
                }
                var hidden = document.getElementById('hiddenContent');
                if (hidden) hidden.value = html;

                var btn = form.querySelector('.btn-submit-story');
                if (btn) {
                    btn.disabled = true;
                    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Đang lưu...';
                }
                return true;
            };
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
