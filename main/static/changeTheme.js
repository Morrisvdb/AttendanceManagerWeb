// Update the theme by calling the sever in the background
function toggleTheme() {
    const themeIcon = document.getElementById('themeIcon');
    url = document.getElementById("theme_route").getAttribute("data-other");
    console.log("Toggling theme with URL:", url);
    fetch(url, {
        method: 'POST',
    })
    .then(response => {
        if (response.ok) {
            if (themeIcon.classList.contains('fa-moon')) {
                themeIcon.classList.remove('fa-moon');
                themeIcon.classList.add('fa-sun');
            } else {
                themeIcon.classList.remove('fa-sun');
                themeIcon.classList.add('fa-moon');
            }
        } else {
            console.error('Failed to toggle theme:', response.status);
        }
    })
    .catch(error => {
        console.error('Error toggling theme:', error);
    });
}

// Set the initial theme icon based on the current theme
function setThemeIcon() {
    const themeIcon = document.getElementById('themeIcon');
    const currentTheme = document.cookie.replace(/(?:(?:^|.*;\s*)theme\s*\=\s*([^;]*).*$)|^.*$/, "$1");
    console.log("Current theme from cookie:", currentTheme);

    if (currentTheme === 'dark') {
        themeIcon.classList.remove('fa-sun');
        themeIcon.classList.add('fa-moon');
    } else {
        themeIcon.classList.remove('fa-moon');
        themeIcon.classList.add('fa-sun');
    }
}

document.addEventListener('DOMContentLoaded', setThemeIcon);