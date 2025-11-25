// Theme Manager - Handles dark/light theme switching via cookie
(function() {
    const THEME_COOKIE_NAME = 'theme';
    const THEME_LIGHT = 'light';
    const THEME_DARK = 'dark';

    /**
     * Get theme from cookie
     */
    function getThemeFromCookie() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === THEME_COOKIE_NAME) {
                return value;
            }
        }
        return null;
    }

    /**
     * Set theme cookie
     */
    function setThemeCookie(theme) {
        document.cookie = `${THEME_COOKIE_NAME}=${theme}; path=/; max-age=31536000`; // 1 year
    }

    /**
     * Apply theme to document
     */
    function applyTheme(theme) {
        if (theme === THEME_DARK) {
            document.documentElement.setAttribute('data-theme', 'dark');
        } else {
            document.documentElement.removeAttribute('data-theme');
        }
        
        // Update icon if present
        const themeIcon = document.getElementById('themeIcon');
        if (themeIcon) {
            if (theme === THEME_DARK) {
                themeIcon.classList.remove('fa-sun');
                themeIcon.classList.add('fa-moon');
            } else {
                themeIcon.classList.remove('fa-moon');
                themeIcon.classList.add('fa-sun');
            }
        }
    }

    /**
     * Toggle theme
     */
    window.toggleTheme = function() {
        const currentTheme = getThemeFromCookie() || THEME_LIGHT;
        const newTheme = currentTheme === THEME_LIGHT ? THEME_DARK : THEME_LIGHT;
        setThemeCookie(newTheme);
        applyTheme(newTheme);
    };

    /**
     * Initialize theme on page load
     */
    function initTheme() {
        const savedTheme = getThemeFromCookie() || THEME_LIGHT;
        applyTheme(savedTheme);
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTheme);
    } else {
        initTheme();
    }
})();
