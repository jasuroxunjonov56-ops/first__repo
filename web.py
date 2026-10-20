import asyncio
from main import main as run_telegram_bot
import os
import json
import time
import hmac
import hashlib
from pathlib import Path
from urllib.parse import parse_qsl

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="UniXizmat")

templates = Jinja2Templates(
    directory=str(BASE_DIR / "templates")
)

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static"
)

bot_task = None


@app.on_event("startup")
async def start_telegram_bot():
    global bot_task
    bot_task = asyncio.create_task(run_telegram_bot())


@app.on_event("shutdown")
async def stop_telegram_bot():
    if bot_task is not None:
        bot_task.cancel()
        try:
            await bot_task
        except asyncio.CancelledError:
            pass
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )


@app.get("/health")
async def health():
    return {"status": "ok", "app": "UniXizmat"}


def verify_telegram_data(init_data: str, bot_token: str):
    try:
        data = dict(parse_qsl(init_data, keep_blank_values=True))

        received_hash = data.pop("hash", None)
        if not received_hash:
            return None

        data_check_string = "\n".join(
            f"{key}={value}"
            for key, value in sorted(data.items())
        )

        secret_key = hmac.new(
            b"WebAppData",
            bot_token.encode(),
            hashlib.sha256
        ).digest()

        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(calculated_hash, received_hash):
            return None

        auth_date = int(data.get("auth_date", "0"))
        now = int(time.time())

        if auth_date > now + 60 or now - auth_date > 86400:
            return None

        user = json.loads(data.get("user", "{}"))

        if not isinstance(user.get("id"), int):
            return None

        return user

    except (ValueError, TypeError, json.JSONDecodeError):
        return None


@app.post("/api/auth/telegram")
async def telegram_auth(request: Request):
    bot_token = os.getenv("BOT_TOKEN", "")

    if not bot_token:
        raise HTTPException(
            status_code=500,
            detail="Serverda BOT_TOKEN sozlanmagan"
        )

    try:
        body = await request.json()
    except (ValueError, json.JSONDecodeError):
        raise HTTPException(status_code=400, detail="Noto'g'ri so'rov")

    init_data = body.get("initData", "")

    if not isinstance(init_data, str) or not init_data:
        raise HTTPException(
            status_code=401,
            detail="Telegram ma'lumotlari topilmadi"
        )

    user = verify_telegram_data(init_data, bot_token)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Telegram ma'lumotlari tasdiqlanmadi"
        )

    return {
        "ok": True,
        "user": {
            "id": user["id"],
            "first_name": user.get("first_name", ""),
            "username": user.get("username", "")
        }
    }
