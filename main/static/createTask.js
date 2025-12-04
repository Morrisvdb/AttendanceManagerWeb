function updatePeopleSelect() {
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

    const peopleSelect = document.getElementById('people-select');
    const filterInput = document.getElementById('filter_people');
    const filterValue = (filterInput && filterInput.value) ? filterInput.value.toLowerCase() : '';

    // Clear existing options
    if (peopleSelect) peopleSelect.innerHTML = '';

    // Add filtered options
    if (Array.isArray(people)) {
        people.forEach(person => {
            if (!person || !person.name) return;
            if (person.name.toLowerCase().includes(filterValue)) {
                const option = document.createElement('option');
                option.value = person.id;
                option.text = person.name;
                peopleSelect.appendChild(option);
            }
        });
    }
}

function updateNumber() {
    const numberInput = document.getElementById('number');
    const peopleSelect = document.getElementById('people-select');

    number = parseInt(numberInput.value) || 1;
    selectedPeopleCount = peopleSelect.selectedOptions.length;
    console.log(`Selected people count: ${selectedPeopleCount}, Limit: ${number}`);

    if (selectedPeopleCount > number) {
        numberInput.value = selectedPeopleCount;
    }
    numberInput.min = selectedPeopleCount;

}

function warnNumber() {
    const numberInput = document.getElementById('number');
    const peopleSelect = document.getElementById('people-select');
    const warning = document.getElementById('number-warning');
    
    number = parseInt(numberInput.value) || 1;
    selectedPeopleCount = peopleSelect.selectedOptions.length;
    if (selectedPeopleCount > number) {
        warning.style.display = 'flex';
    } else {
        warning.style.display = 'none';
    }
}