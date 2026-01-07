// WARNING: This is hard coded for 5 minutes, other expiry times may not display correctly.
function startCountdownTimer(unixTimestamp) {
    const targetTime = unixTimestamp * 1000; // Convert to milliseconds
    const countDownElement = document.getElementById("countdown-timer");
    const resendEmailButton = document.getElementById("resend-email-button");

    function updateTimer() {
        const now = Date.now();
        const timeRemaining = targetTime - now;

        if (timeRemaining <= 0) {
            countDownElement.textContent = _("Email expired, use the button below to request a new one.");
            return;
        }


        if (timeRemaining < 4 * 60 * 1000) {
            // resendEmailButton.disabled = false;
            resendEmailButton.classList.remove("disabled");
        } else {
            resendEmailButton.classList.add("disabled");
        }

        let seconds = Math.floor((timeRemaining / 1000) % 60);
        const minutes = Math.floor((timeRemaining / (1000 * 60)) % 60);

        seconds = seconds < 10 ? '0' + seconds : seconds;

        countDownElement.textContent = _("Email expires in: ") + `${minutes}m ${seconds}s`;

    }

    updateTimer();
    setInterval(updateTimer, 1000);
}



onload = function() {
    // Example usage: start a countdown to a specific Unix timestamp
    const timestamp = document.getElementById("expiry_timestamp").getAttribute("data-other");
    startCountdownTimer(timestamp);
}