function switchTask() {
    const select = document.getElementById("task-select");
    const taskId = select.value;

    if (taskId == "none") {
        document.getElementById('task-display').style.display = "none";
        return;
    }
    document.getElementById('task-display').style.display = "block";

    for (let i = 0; i < window.TASKS.length; i++) {
        const task = window.TASKS[i];
        if (task.id == taskId) {
            document.getElementById("task-name").innerText = task.name;
            document.getElementById("task-amount").innerText = task.amount;
            const peopleList = document.getElementById("task-people-list");
            peopleList.innerHTML = "";
            for (let j = 0; j < task.people.length; j++) {
                const person = task.people[j];
                const li = document.createElement("li");
                li.innerText = person.name;
                peopleList.appendChild(li);
            }
            link = document.getElementById("task-edit-button")
            const url = window.URLS.userPage.replace("__ID__", task.id);
            link.href = url;
            return;
        }
    }
}
window.onload = function() {
    switchTask();
}