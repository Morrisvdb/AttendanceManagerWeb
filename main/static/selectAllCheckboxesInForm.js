function selectAllCheckboxesInForm() {
    const checkboxes = document.querySelectorAll('input[type="checkbox"].presence-checkbox');
    checkboxes.forEach((checkbox) => {
        checkbox.checked = true;
    });
}