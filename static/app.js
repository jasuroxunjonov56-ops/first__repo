
function showLoginMessage() {
    alert(
        "UniXizmat'ga Telegram orqali kirish funksiyasi hali ulanmagan. " +
        "Keyingi bosqichda uni sozlaymiz!"
    );
}

const loginBtn = document.getElementById("loginBtn");
const bottomLoginBtn = document.getElementById("bottomLoginBtn");

if (loginBtn) {
    loginBtn.addEventListener("click", showLoginMessage);
}

if (bottomLoginBtn) {
    bottomLoginBtn.addEventListener("click", showLoginMessage);
}

