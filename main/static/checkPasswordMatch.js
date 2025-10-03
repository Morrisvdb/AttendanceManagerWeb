function checkPasswordMatch() {
    var password = document.getElementById("password1").value;
    var confirmPassword = document.getElementById("password2").value;
    if (password !== confirmPassword) {
        document.getElementById("passwordHelp").style.display = "block";
    } else {
        document.getElementById("passwordHelp").style.display = "none";
    }
    console.log("checkPasswordMatch called");
}