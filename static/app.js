
const tg = window.Telegram?.WebApp;

if (tg) {
    tg.ready();
    tg.expand();
}

async function loginWithTelegram() {
    if (!tg || !tg.initData) {
        alert(
            "Telegram orqali kirish uchun UniXizmat'ni " +
            "Telegram botining Mini App menyusidan oching."
        );
        return;
    }

    try {
        const response = await fetch("/api/auth/telegram", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                initData: tg.initData
            })
        });

        const result = await response.json();

        if (!response.ok || !result.ok) {
            throw new Error(
                result.detail || "Telegram orqali kirish amalga oshmadi."
            );
        }

        const user = result.user;
        const name = user.first_name || "Talaba";

        alert(
            "Muvaffaqiyatli tasdiqlandi, " + name + "!"
        );

        const loginBtn = document.getElementById("loginBtn");

        if (loginBtn) {
            loginBtn.textContent = "Salom, " + name + "!";
        }

        const bottomBtn = document.getElementById("bottomLoginBtn");

        if (bottomBtn) {
            bottomBtn.textContent = "Salom, " + name + "!";
        }

    } catch (error) {
        console.error("Telegram login error:", error);

        alert(
            error.message ||
            "Xatolik yuz berdi. Keyinroq qayta urinib ko'ring."
        );
    }
}

const loginBtn = document.getElementById("loginBtn");
const bottomLoginBtn = document.getElementById("bottomLoginBtn");

if (loginBtn) {
    loginBtn.addEventListener("click", loginWithTelegram);
}

if (bottomLoginBtn) {
    bottomLoginBtn.addEventListener("click", loginWithTelegram);
}
