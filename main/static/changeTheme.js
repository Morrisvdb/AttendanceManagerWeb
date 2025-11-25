function toggleTheme() {
    const themeIcon = document.getElementById('themeIcon');
    
    fetch('/theme/toggle/', {
        method: 'POST',
        credentials: 'same-origin'
    })
    .then(response => {
        if (response.ok) {
            // Toggle the icon based on the new theme
            if (themeIcon.classList.contains('fa-moon')) {
                themeIcon.classList.remove('fa-moon');
                themeIcon.classList.add('fa-sun');
            } else {
                themeIcon.classList.remove('fa-sun');
                themeIcon.classList.add('fa-moon');
            }
            // Optionally, you can also toggle a class on the body to change the theme immediately
            document.body.classList.toggle('dark-theme');
        } else {
            console.error('Failed to toggle theme:', response.status);
        }
    })
    .catch(error => {
        console.error('Error toggling theme:', error);
    });
}