function updateOrganiserSelect() {
    const meta = document.getElementById('people');
    let people = [];
    if (meta) {
        const raw = meta.getAttribute('data-people');
        try {
            people = JSON.parse(raw);
        } catch (e) {
            // Fallback to jQuery data (handles some older formats)
            try {
                people = $(meta).data('people') || [];
            } catch (e2) {
                people = [];
            }
        }
    }

    const organiserSelect = document.getElementById('organiser');
    const filterInput = document.getElementById('filter_people');
    const filterValue = (filterInput && filterInput.value) ? filterInput.value.toLowerCase() : '';

    // Clear existing options
    if (organiserSelect) organiserSelect.innerHTML = '';

    // Add filtered options
    if (Array.isArray(people)) {
        people.forEach(person => {
            if (!person || !person.name) return;
            if (person.name.toLowerCase().includes(filterValue)) {
                const option = document.createElement('option');
                option.value = person.id;
                option.text = person.name;
                organiserSelect.appendChild(option);
            }
        });
    }
}