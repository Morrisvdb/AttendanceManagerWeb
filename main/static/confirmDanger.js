function confirmDanger(message, actionUrl) {
    const userInput = prompt(`${message}\n\n` + _(`Type "CONFIRM" to proceed:`));
    return userInput === "CONFIRM"
}
