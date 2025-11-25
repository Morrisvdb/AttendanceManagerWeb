function changeLocale(locale) {
    console.log("Changing locale to:", locale);
    url = document.getElementById("locale_route").getAttribute("data-other");
    url = url.replace("__locale__", locale);
    fetch(url, {'method': 'post'}).then(response => {
        if (response.status === 200) {
            window.location.reload();
        } else {
            console.error("Failed to change locale:", response.status);
        }
    });
}