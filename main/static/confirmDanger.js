function confirmDanger(message, actionUrl) {
    const userInput = prompt(`${message}\n\nType "CONFIRM" to proceed:`);
    return userInput === "CONFIRM"
}
