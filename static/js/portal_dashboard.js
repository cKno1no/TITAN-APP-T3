/**
 * Portal Dashboard - Progress ring animation + optional refresh toast
 */
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(function() {
        var rings = document.querySelectorAll('.progress-ring');
        rings.forEach(function(ring) {
            var currentProg = ring.style.getPropertyValue('--progress');
            ring.style.setProperty('--progress', '0%');
            setTimeout(function() {
                ring.style.setProperty('--progress', currentProg || '0%');
            }, 100);
        });
    }, 500);
});
