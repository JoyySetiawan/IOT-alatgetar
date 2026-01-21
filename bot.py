import logging
import time
import asyncio
from typing import Any, Dict, Optional, Tuple

import httpx
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ===================== CONFIG =====================
TOKEN = "8362801448:AAHX1nIrYOeT5Z8bnAMsTd6R7A_37XJOi6o"

# Flask base URL
FLASK_BASE_URL = "http://127.0.0.1:5000"

API_OPEN = f"{FLASK_BASE_URL}/open"
API_CLOSE = f"{FLASK_BASE_URL}/close"
API_REGISTER = f"{FLASK_BASE_URL}/register"

# API Key
API_KEY = "MY_SECRET_API_KEY"

ID_MESIN_DEFAULT = "Loker-Utama"
ALLOWED_USERS: set[int] = set()
COOLDOWN_SECONDS = 3
_last_action_ts: dict[int, float] = {}
# ==================================================


def build_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("🔓 Buka Loker", callback_data="open"),
            InlineKeyboardButton("🔒 Tutup Loker", callback_data="close"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def build_reply_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard standar yang replace keyboard Android"""
    keyboard = [
        [
            KeyboardButton("/open"),
            KeyboardButton("/close"),
        ],
        [
            KeyboardButton("/register"),
            KeyboardButton("/help"),
        ],
        [
            KeyboardButton("/myid"),
            KeyboardButton("/start"),
        ]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)


def _display_name(update: Update) -> str:
    u = update.effective_user
    if not u:
        return "-"
    return u.username or u.full_name or str(u.id)


async def call_flask(url: str, payload: Dict[str, Any], api_key: Optional[str]) -> Tuple[int, str]:
    headers = {}
    if api_key:
        headers["X-API-KEY"] = api_key

    try:
        timeout = httpx.Timeout(10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)
    except httpx.RequestError as e:
        return 0, f"RequestError: {e}"

    msg = ""
    try:
        data = resp.json()
        msg = (
            data.get("message")
            or data.get("status")
            or data.get("pesan")
            or data.get("msg")
            or str(data)
        )
    except Exception:
        msg = resp.text.strip()

    return resp.status_code, msg


def _cooldown_ok(user_id: int) -> Tuple[bool, int]:
    now = time.time()
    last = _last_action_ts.get(user_id, 0.0)
    if now - last < COOLDOWN_SECONDS:
        wait = int(COOLDOWN_SECONDS - (now - last) + 1)
        return False, wait
    _last_action_ts[user_id] = now
    return True, 0


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = _display_name(update)
    text = (
        f"Halo, {name}!\n\n"
        "Gunakan tombol di bawah untuk kontrol loker.\n"
        "Akses akan diputuskan oleh server (whitelist di database web)."
    )
    await update.message.reply_text(
        text,
        reply_markup=build_reply_keyboard()
    )


async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    await update.message.reply_text(
        f"Telegram ID kamu: `{u.id}`\nUsername: `{u.username or '-'}`",
        parse_mode="Markdown",
        reply_markup=build_reply_keyboard()
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Perintah:\n"
        "/start - tampilkan tombol kontrol\n"
        "/open - buka loker langsung (cepat)\n"
        "/close - tutup loker langsung (cepat)\n"
        "/myid - lihat telegram ID kamu\n"
        "/register - daftar akun baru ke database\n"
        "/help - bantuan",
        reply_markup=build_reply_keyboard()
    )


async def register_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command untuk registrasi user baru"""
    user = update.effective_user
    user_id = str(user.id)
    username = user.username or user.full_name or str(user_id)

    payload = {
        "user_id": user_id,
        "username": username,
    }

    status_code, msg = await call_flask(API_REGISTER, payload, API_KEY)

    if status_code == 0:
        response = "⚠️ Gagal menghubungi server.\n"
        detail = msg
    elif 200 <= status_code < 300:
        response = "✅ Registrasi berhasil!\n"
        detail = f"Akun '{username}' sekarang whitelisted."
    elif status_code == 409:
        response = "ℹ️ Akun sudah terdaftar.\n"
        detail = "Kamu sudah ada di database."
    elif status_code in (401, 403):
        response = "⛔ Akses ditolak.\n"
        detail = "Cek API key."
    else:
        response = f"❌ Error ({status_code}).\n"
        detail = msg

    text = f"{response}{detail}"
    await update.message.reply_text(text, reply_markup=build_reply_keyboard())


async def perform_action(update: Update, action: str):
    """Helper function untuk command /open dan /close"""
    user = update.effective_user
    user_id = user.id
    username = user.username or user.full_name or str(user_id)

    ok, wait = _cooldown_ok(user_id)
    if not ok:
        await update.message.reply_text(f"⏳ Tunggu {wait} detik sebelum aksi lagi.")
        return

    msg = await update.message.reply_text(
        f"⏳ Memproses: {('BUKA' if action == 'open' else 'TUTUP')} ..."
    )

    payload = {
        "user_id": str(user_id),
        "username": username,
        "id_mesin": ID_MESIN_DEFAULT,
        "source": "telegram_bot",
        "command": "unlock" if action == "open" else "lock",
    }

    url = API_OPEN if action == "open" else API_CLOSE
    status_code, response_msg = await call_flask(url, payload, API_KEY)

    if status_code == 0:
        prefix = "⚠️"
        detail = "Gagal menghubungi server."
    elif 200 <= status_code < 300:
        prefix = "✅"
        detail = "Berhasil."
    elif status_code in (401, 403):
        prefix = "⛔"
        detail = "Akses Ditolak."
    else:
        prefix = "❌"
        detail = "Gagal."

    result_text = (
        f"{prefix} {detail}\n"
        f"Aksi: {action.upper()}\n"
        f"Pesan: {response_msg}"
    )

    await msg.edit_text(result_text)


async def open_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await perform_action(update, "open")


async def close_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await perform_action(update, "close")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    action = query.data
    user = query.from_user
    user_id = user.id
    username = user.username or user.full_name or str(user_id)

    await query.answer()

    if ALLOWED_USERS and user_id not in ALLOWED_USERS:
        await query.answer("⛔ Kamu tidak ada di whitelist bot.", show_alert=True)
        return

    ok, wait = _cooldown_ok(user_id)
    if not ok:
        await query.answer(f"⏳ Tunggu {wait} detik lagi.", show_alert=True)
        return

    payload = {
        "user_id": str(user_id),
        "username": username,
        "id_mesin": ID_MESIN_DEFAULT,
        "source": "telegram_bot",
        "command": "unlock" if action == "open" else "lock",
    }

    url = API_OPEN if action == "open" else API_CLOSE

    await query.edit_message_text(
        text=f"⏳ Memproses: {('BUKA' if action == 'open' else 'TUTUP')} ..."
    )

    status_code, msg = await call_flask(url, payload, API_KEY)

    if status_code == 0:
        prefix = "⚠️"
        detail = "Gagal menghubungi Flask."
    elif 200 <= status_code < 300:
        prefix = "✅"
        detail = "Berhasil."
    elif status_code in (401, 403):
        prefix = "⛔"
        detail = "Akses Ditolak."
    else:
        prefix = "❌"
        detail = f"Gagal ({status_code})."

    await query.edit_message_text(
        text=(
            f"{prefix} {detail}\n"
            f"Aksi: {action.upper()}\n"
            f"Response: {msg}"
        )
    )


async def echo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk message text biasa - tampilkan keyboard"""
    await update.message.reply_text(
        "📱 Gunakan tombol di bawah:",
        reply_markup=build_reply_keyboard()
    )


# --- FUNGSI UTAMA UNTUK DIPANGGIL APP.PY ---
def start_bot():
    """Fungsi ini akan dijalankan oleh Threading di app.py"""
    
    # 1. Setup Logging
    logging.basicConfig(
        format="%(asctime)s - BOT - %(levelname)s - %(message)s", 
        level=logging.INFO
    )
    
    # 2. Setup Loop Asyncio Baru (Wajib untuk Threading)
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    except Exception as e:
        print(f"Warning Loop: {e}")

    # 3. Build & Run Bot
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("open", open_cmd))
    app.add_handler(CommandHandler("close", close_cmd))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("register", register_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_handler))

    logging.info("🤖 Bot Telegram Berjalan di Background...")
    app.run_polling()

if __name__ == "__main__":
    start_bot()