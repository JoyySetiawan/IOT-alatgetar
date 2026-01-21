import logging
import time
from typing import Any, Dict, Optional, Tuple

import httpx
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ===================== CONFIG =====================
TOKEN = "8362801448:AAHX1nIrYOeT5Z8bnAMsTd6R7A_37XJOi6o"

# Flask base URL (kalau bot & flask di mesin yang sama, localhost oke)
FLASK_BASE_URL = "http://localhost:5000"

# Endpoint yang akan dipanggil bot (pastikan route ini ada di app.py)
API_OPEN = f"{FLASK_BASE_URL}/open"
API_CLOSE = f"{FLASK_BASE_URL}/close"
API_REGISTER = f"{FLASK_BASE_URL}/register"

# Samakan dengan BOT_API_KEY di app.py (header: X-API-KEY)
API_KEY = "MY_SECRET_API_KEY"  # boleh "" / None kalau kamu disable cek key di server

# ID mesin default (samakan konsepnya dengan app.py yang pakai default "Loker-Utama")
ID_MESIN_DEFAULT = "Loker-Utama"

# Opsional: kalau kamu mau *double protection* di sisi bot
# - Kosongkan set ini kalau mau semua user tetap bisa klik, lalu server yang menentukan (recommended)
ALLOWED_USERS: set[int] = set()

# Anti-spam klik tombol (detik)
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

    # coba parse JSON yang umum dipakai (status/message), fallback ke text
    msg = ""
    try:
        data = resp.json()
        # fleksibel: dukung beberapa format response
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
        wait = int(COOLDOWN_SECONDS - (now - last) + 0.999)
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
    await update.message.reply_text(text, reply_markup=build_keyboard())


async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    await update.message.reply_text(
        f"Telegram ID kamu: `{u.id}`\nUsername: `{u.username or '-'}`",
        parse_mode="Markdown",
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Perintah:\n"
        "/start - tampilkan tombol kontrol\n"
        "/open - buka loker langsung (cepat)\n"
        "/close - tutup loker langsung (cepat)\n"
        "/myid - lihat telegram ID kamu (untuk dimasukkan ke whitelist web)\n"
        "/register - daftar akun baru ke database\n"
        "/help - bantuan"
    )


async def register_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command untuk registrasi user baru"""
    user = update.effective_user
    user_id = str(user.id)
    username = user.username or user.full_name or str(user_id)

    # Kirim request registrasi ke server
    payload = {
        "user_id": user_id,
        "username": username,
    }

    status_code, msg = await call_flask(API_REGISTER, payload, API_KEY)

    if status_code == 0:
        response = "⚠️ Gagal menghubungi server.\n"
        detail = msg
    elif status_code == 201:
        response = "✅ Registrasi berhasil!\n"
        detail = f"Akun '{username}' sekarang whitelisted dan bisa akses loker."
    elif status_code == 409:
        response = "ℹ️ Akun sudah terdaftar.\n"
        detail = "Kamu sudah di dalam database, tinggal pakai tombol di bawah."
    elif status_code in (401, 403):
        response = "⛔ Akses ditolak.\n"
        detail = "Cek API key atau izin server."
    else:
        response = f"❌ Error ({status_code}).\n"
        detail = msg

    text = f"{response}{detail}"
    await update.message.reply_text(text, reply_markup=build_keyboard())


async def perform_action(update: Update, action: str):
    """Helper function untuk perform open/close action"""
    user = update.effective_user
    user_id = user.id
    username = user.username or user.full_name or str(user_id)

    ok, wait = _cooldown_ok(user_id)
    if not ok:
        await update.message.reply_text(f"⏳ Tunggu {wait} detik sebelum aksi lagi.")
        return

    # Tampilkan status processing
    msg = await update.message.reply_text(
        f"⏳ Memproses: {('BUKA' if action == 'open' else 'TUTUP')} ...",
        reply_markup=build_keyboard(),
    )

    # Payload
    payload = {
        "user_id": str(user_id),
        "username": username,
        "id_mesin": ID_MESIN_DEFAULT,
        "source": "telegram_bot",
        "command": "unlock" if action == "open" else "lock",
    }

    url = API_OPEN if action == "open" else API_CLOSE
    status_code, response_msg = await call_flask(url, payload, API_KEY)

    # Format response
    if status_code == 0:
        prefix = "⚠️"
        detail = "Gagal menghubungi server Flask."
    elif 200 <= status_code < 300:
        prefix = "✅"
        detail = "Berhasil."
    elif status_code in (401, 403):
        prefix = "⛔"
        detail = "Tidak diizinkan (cek API key / whitelist DB)."
    else:
        prefix = "❌"
        detail = "Gagal."

    result_text = (
        f"{prefix} {detail}\n"
        f"Aksi: {action}\n"
        f"HTTP: {status_code}\n"
        f"Response: {response_msg}"
    )

    await msg.edit_text(result_text, reply_markup=build_keyboard())


async def open_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /open - buka loker langsung"""
    await perform_action(update, "open")


async def close_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /close - tutup loker langsung"""
    await perform_action(update, "close")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    action = query.data  # "open" / "close"
    user = query.from_user
    user_id = user.id
    username = user.username or user.full_name or str(user_id)

    # Hilangkan spinner dulu
    await query.answer()

    # Opsional: proteksi di bot (kalau set ALLOWED_USERS diisi)
    if ALLOWED_USERS and user_id not in ALLOWED_USERS:
        logging.warning("UNAUTHORIZED(bot-side) user_id=%s action=%s", user_id, action)
        await query.answer("⛔ Kamu tidak ada di whitelist bot.", show_alert=True)
        return

    ok, wait = _cooldown_ok(user_id)
    if not ok:
        await query.answer(f"Tunggu {wait} detik sebelum klik lagi.", show_alert=True)
        return

    # payload yang cocok dengan endpoint /open /close di app.py (patch sebelumnya)
    payload = {
        "user_id": str(user_id),      # di app.py Pengguna.id_telegram adalah string
        "username": username,
        "id_mesin": ID_MESIN_DEFAULT,
        "source": "telegram_bot",
        "command": "unlock" if action == "open" else "lock",
    }

    url = API_OPEN if action == "open" else API_CLOSE

    # Tampilkan status processing (keyboard tetap ada)
    await query.edit_message_text(
        text=f"⏳ Memproses: {('BUKA' if action == 'open' else 'TUTUP')} ...",
        reply_markup=build_keyboard(),
    )

    status_code, msg = await call_flask(url, payload, API_KEY)

    if status_code == 0:
        prefix = "⚠️"
        detail = "Gagal menghubungi server Flask."
    elif 200 <= status_code < 300:
        prefix = "✅"
        detail = "Berhasil."
    elif status_code in (401, 403):
        prefix = "⛔"
        detail = "Tidak diizinkan (cek API key / whitelist DB)."
    else:
        prefix = "❌"
        detail = "Gagal."

    await query.edit_message_text(
        text=(
            f"{prefix} {detail}\n"
            f"Aksi: {action}\n"
            f"HTTP: {status_code}\n"
            f"Response: {msg}"
        ),
        reply_markup=build_keyboard(),
    )


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("open", open_cmd))
    app.add_handler(CommandHandler("close", close_cmd))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("register", register_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))

    logging.info("Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()