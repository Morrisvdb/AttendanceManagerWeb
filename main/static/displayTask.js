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
            delete_button = document.getElementById("task-delete-button")
            const task_url = window.URLS.taskPage.replace("__ID__", task.id);
            const delete_url = window.URLS.deletePage.replace("__ID__", task.id);
            link.href = task_url;
            delete_button.href = delete_url;
            return;
        }
    }
}
window.onload = function() {
    switchTask();
}