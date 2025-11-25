function toggleProfileMenu() {
            var dropdown = document.getElementById('profileDropdown');
            dropdown.style.display = dropdown.style.display === 'block' ? 'none' : 'block';
        }
        // Hide dropdown when clicking outside
        document.addEventListener('click', function(event) {
            var btn = document.getElementById('profileBtn');
            var dropdown = document.getElementById('profileDropdown');
            if (!btn || !dropdown) return;
            if (!btn.contains(event.target) && !dropdown.contains(event.target)) {
                dropdown.style.display = 'none';
            }
        });