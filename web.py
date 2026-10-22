import asyncio
import os
import json
import time
import hmac
import hashlib
import secrets
from pathlib import Path
from urllib.parse import parse_qsl

import aiosqlite
from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from main import main as run_telegram_bot
from database import init_db
from config import DB_NAME, ENTRY_FEE

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="UniXizmat")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
bot_task = None
SESSION_COOKIE = "unixizmat_session"


@app.on_event("startup")
async def start_telegram_bot():
    global bot_task
    await init_db()
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
    return templates.TemplateResponse(request=request, name="index.html", context={})


@app.get("/health")
async def health():
    return {"status": "ok", "app": "UniXizmat"}


def verify_telegram_data(init_data: str, bot_token: str):
    try:
        data = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = data.pop("hash", None)
        if not received_hash:
            return None
        data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(data.items()))
        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
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


class RegisterBody(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)


class LoginBody(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=1, max_length=128)


class OrderBody(BaseModel):
    description: str = Field(min_length=5, max_length=1000)
    price: int = Field(gt=0, le=100000000)
    contact: str = Field(min_length=3, max_length=100)


class AdminLoginBody(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=128)


def password_hash(password: str, salt: bytes | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310000)
    return salt.hex(), digest.hex()


def check_password(password: str, salt_hex: str, digest_hex: str) -> bool:
    _, candidate = password_hash(password, bytes.fromhex(salt_hex))
    return hmac.compare_digest(candidate, digest_hex)


async def db_connect():
    db = await aiosqlite.connect(DB_NAME)
    db.row_factory = aiosqlite.Row
    return db


async def create_session(account_id: int | None, role: str, username: str) -> str:
    token = secrets.token_urlsafe(36)
    async with await db_connect() as db:
        await db.execute(
            "INSERT INTO web_sessions (token, account_id, role, username, created_at) VALUES (?, ?, ?, ?, ?)",
            (token, account_id, role, username, int(time.time())),
        )
        await db.commit()
    return token


def set_session_cookie(response: Response, token: str):
    response.set_cookie(SESSION_COOKIE, token, httponly=True, secure=True, samesite="lax", max_age=60 * 60 * 24 * 14, path="/")


async def current_session(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    async with await db_connect() as db:
        cursor = await db.execute("SELECT * FROM web_sessions WHERE token = ?", (token,))
        row = await cursor.fetchone()
        return dict(row) if row else None


@app.post("/api/register")
async def register_worker(body: RegisterBody):
    bot_username = os.getenv("BOT_USERNAME", "").strip().lstrip("@")
    if not bot_username:
        raise HTTPException(status_code=503, detail="Serverda BOT_USERNAME sozlanmagan. Render Environment bo‘limiga bot username’ini kiriting.")
    username = body.username.strip().lower()
    salt, digest = password_hash(body.password)
    link_token = secrets.token_urlsafe(28)
    async with await db_connect() as db:
        try:
            cursor = await db.execute(
                "INSERT INTO worker_accounts (username, salt, password_hash, link_token, active, created_at) VALUES (?, ?, ?, ?, 0, ?)",
                (username, salt, digest, link_token, int(time.time())),
            )
            await db.commit()
            account_id = cursor.lastrowid
        except aiosqlite.IntegrityError:
            raise HTTPException(status_code=409, detail="Bu login band. Boshqa login tanlang.")
    telegram_url = f"https://t.me/{bot_username}?start=link_{link_token}"
    return {"ok": True, "account_id": account_id, "link_token": link_token, "telegram_url": telegram_url, "fee": ENTRY_FEE,
            "message": "Login yaratildi. Telegram orqali bir martalik to‘lovni yuboring; admin tasdiqlagach akkaunt faollashadi."}


@app.post("/api/login")
async def login_worker(body: LoginBody, response: Response):
    username = body.username.strip().lower()
    async with await db_connect() as db:
        cursor = await db.execute("SELECT * FROM worker_accounts WHERE username = ?", (username,))
        account = await cursor.fetchone()
    if not account or not check_password(body.password, account["salt"], account["password_hash"]):
        raise HTTPException(status_code=401, detail="Login yoki parol noto‘g‘ri.")
    if not account["active"]:
        raise HTTPException(status_code=403, detail="Akkaunt hali faollashtirilmagan. Telegram orqali to‘lov va admin tasdig‘ini kuting.")
    token = await create_session(account["id"], "worker", username)
    set_session_cookie(response, token)
    return {"ok": True, "username": username, "message": "Kirish muvaffaqiyatli."}


@app.post("/api/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        async with await db_connect() as db:
            await db.execute("DELETE FROM web_sessions WHERE token = ?", (token,))
            await db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


@app.get("/api/me")
async def me(request: Request):
    session = await current_session(request)
    if not session:
        return {"ok": True, "logged_in": False}
    return {"ok": True, "logged_in": True, "username": session["username"], "role": session["role"]}


@app.get("/api/worker/status")
async def worker_status(link_token: str, response: Response):
    async with await db_connect() as db:
        cursor = await db.execute("SELECT * FROM worker_accounts WHERE link_token = ?", (link_token,))
        account = await cursor.fetchone()
    if not account:
        raise HTTPException(status_code=404, detail="Ro‘yxatdan o‘tish havolasi topilmadi.")
    if not account["active"]:
        return {"ok": True, "active": False, "message": "To‘lov tasdig‘i kutilmoqda."}
    token = await create_session(account["id"], "worker", account["username"])
    set_session_cookie(response, token)
    return {"ok": True, "active": True, "username": account["username"]}


@app.post("/api/orders")
async def create_web_order(body: OrderBody):
    description = body.description.strip()
    contact = body.contact.strip()
    student_id = -int(time.time() * 1000)
    async with await db_connect() as db:
        cursor = await db.execute(
            "INSERT INTO orders (student_id, description, price, status, contact, source) VALUES (?, ?, ?, 'open', ?, 'website')",
            (student_id, description, body.price, contact),
        )
        await db.commit()
        order_id = cursor.lastrowid
    return {"ok": True, "order_id": order_id, "description": description, "price": body.price, "message": "Buyurtma qabul qilindi va ijrochilar ro‘yxatiga qo‘shildi."}


@app.get("/api/orders")
async def list_orders():
    async with await db_connect() as db:
        cursor = await db.execute("SELECT id, description, price, status, source FROM orders WHERE status = 'open' ORDER BY id DESC LIMIT 50")
        rows = await cursor.fetchall()
    return {"ok": True, "orders": [dict(row) for row in rows]}


@app.post("/api/orders/{order_id}/take")
async def take_web_order(order_id: int, request: Request):
    session = await current_session(request)
    if not session or session["role"] != "worker" or not session["account_id"]:
        raise HTTPException(status_code=401, detail="Buyurtma olish uchun avval bajaruvchi sifatida kiring.")
    async with await db_connect() as db:
        cursor = await db.execute("SELECT telegram_id, active FROM worker_accounts WHERE id = ?", (session["account_id"],))
        account = await cursor.fetchone()
        if not account or not account["active"] or not account["telegram_id"]:
            raise HTTPException(status_code=403, detail="Bajaruvchi akkauntingiz hali faollashtirilmagan.")
        cursor = await db.execute("UPDATE orders SET status = 'assigned', worker_id = ? WHERE id = ? AND status = 'open'", (account["telegram_id"], order_id))
        if cursor.rowcount == 0:
            await db.rollback()
            raise HTTPException(status_code=409, detail="Bu buyurtma boshqa ijrochiga biriktirilgan yoki yopilgan.")
        cursor = await db.execute("SELECT contact FROM orders WHERE id = ?", (order_id,))
        order = await cursor.fetchone()
        await db.commit()
    return {"ok": True, "contact": order["contact"] if order else None, "message": "Buyurtma sizga biriktirildi."}


@app.post("/api/admin/login")
async def admin_login(body: AdminLoginBody, response: Response):
    expected_user = os.getenv("ADMIN_USERNAME", "")
    expected_pass = os.getenv("ADMIN_PASSWORD", "")
    if not expected_user or not expected_pass:
        raise HTTPException(status_code=503, detail="Admin web login uchun Render Environment’da ADMIN_USERNAME va ADMIN_PASSWORD sozlang.")
    if not hmac.compare_digest(body.username, expected_user) or not hmac.compare_digest(body.password, expected_pass):
        raise HTTPException(status_code=401, detail="Admin login yoki parol noto‘g‘ri.")
    token = await create_session(None, "admin", expected_user)
    set_session_cookie(response, token)
    return {"ok": True}


@app.get("/api/admin/orders")
async def admin_orders(request: Request):
    session = await current_session(request)
    if not session or session["role"] != "admin":
        raise HTTPException(status_code=401, detail="Admin sifatida kiring.")
    async with await db_connect() as db:
        cursor = await db.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 100")
        rows = await cursor.fetchall()
    return {"ok": True, "orders": [dict(row) for row in rows]}


@app.post("/api/auth/telegram")
async def telegram_auth(request: Request):
    bot_token = os.getenv("BOT_TOKEN", "")
    if not bot_token:
        raise HTTPException(status_code=500, detail="Serverda BOT_TOKEN sozlanmagan")
    try:
        body = await request.json()
    except (ValueError, json.JSONDecodeError):
        raise HTTPException(status_code=400, detail="Noto‘g‘ri so‘rov")
    init_data = body.get("initData", "")
    if not isinstance(init_data, str) or not init_data:
        raise HTTPException(status_code=401, detail="Telegram ma’lumotlari topilmadi")
    user = verify_telegram_data(init_data, bot_token)
    if not user:
        raise HTTPException(status_code=401, detail="Telegram ma’lumotlari tasdiqlanmadi")
    return {"ok": True, "user": {"id": user["id"], "first_name": user.get("first_name", ""), "username": user.get("username", "")}}
