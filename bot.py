import re
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from config import (
    API_ID, API_HASH, BOT_TOKEN, ADMIN_ID,
    SESSIONS, ACTIVE_CALLS, WAIT_PHONE, WAIT_OTP, WAIT_PASS,
)
from sessions import start_session, verify_otp, verify_password
from vc_joiner import join_all, leave_all

if not API_ID or not API_HASH or not BOT_TOKEN:
    print("❌ API_ID / API_HASH / BOT_TOKEN missing")
    raise SystemExit(1)

app = Client("admin_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def is_admin(_, __, message):
    return message.from_user and message.from_user.id == ADMIN_ID
admin_only = filters.create(is_admin)

def panel():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Stats", callback_data="stats"),
         InlineKeyboardButton("📋 Accounts", callback_data="accounts")],
        [InlineKeyboardButton("⏹ Leave All", callback_data="leaveall")],
    ])

def parse_vc(link: str):
    m = re.search(r"t\.me/(?:c/)?([\w/+-]+)", link)
    raw = (m.group(1) if m else link).strip("/")
    if raw.startswith("c/"):
        raw = raw[2:]
    if raw.lstrip("-").isdigit():
        return int(raw) if str(raw).startswith("-") else int(f"-100{raw}")
    return raw

@app.on_message(filters.command("start") & admin_only)
async def start(client, message):
    await message.reply(
        f"👋 Admin: `{message.from_user.id}`\n\n"
        "**Commands:**\n"
        "`/session` — naya account add\n"
        "`/stats` — loaded accounts\n"
        "`/join <vc_link> [delay_sec]` — sab accounts join\n"
        "`/leave` — sab accounts leave\n"
        "`/password <pass>` — 2FA password\n\n"
        "⚠️ Sessions RAM-only. Restart = reset.",
        reply_markup=panel(),
    )

@app.on_message(filters.command("session") & admin_only)
async def session_cmd(client, message):
    WAIT_PHONE.add(message.from_user.id)
    WAIT_OTP.discard(message.from_user.id)
    WAIT_PASS.discard(message.from_user.id)
    await message.reply("📱 Number bhej (format: `+91xxxxxxxxxx`)")

@app.on_message(filters.command("password") & admin_only)
async def password_cmd(client, message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.reply("Usage: `/password <2fa_pass>`")
    status, msg = await verify_password(message.from_user.id, parts[1])
    WAIT_PASS.discard(message.from_user.id)
    await message.reply(msg)

@app.on_message(filters.command("stats") & admin_only)
async def stats(client, message):
    lines = [f"👥 **Loaded accounts:** {len(SESSIONS)}\n"]
    for uid, d in SESSIONS.items():
        lines.append(f"• `{uid}` — {d['me']['name']}")
    if ACTIVE_CALLS:
        lines.append(f"\n🎙 **Active VC:** {len(ACTIVE_CALLS)}")
        for cid, arr in ACTIVE_CALLS.items():
            lines.append(f"• `{cid}` — {len(arr)} accounts")
    await message.reply("\n".join(lines) if lines else "Koi account nahi")

@app.on_message(filters.command("join") & admin_only)
async def join_cmd(client, message):
    parts = message.text.split()
    if len(parts) < 2:
        return await message.reply(
            "Usage:\n`/join <vc_link>` — no delay\n"
            "`/join <vc_link> <sec>` — delay between accounts"
        )
    if not SESSIONS:
        return await message.reply("❌ Koi account load nahi. /session chala")
    link = parts[1]
    delay = 0.0
    if len(parts) >= 3:
        try:
            delay = float(parts[2])
        except ValueError:
            return await message.reply("❌ delay number hona chahiye (e.g. 3)")
    chat_id = parse_vc(link)
    m = await message.reply(
        f"⏳ Joining **{len(SESSIONS)}** accounts...\n"
        f"VC: `{chat_id}` | Delay: `{delay}s`"
    )
    joined, failed = await join_all(chat_id, delay)
    text = f"✅ **Joined:** {len(joined)}\n"
    if failed:
        text += f"❌ **Failed:** {len(failed)}\n"
        for f in failed[:5]:
            text += f"`{f}`\n"
        if len(failed) > 5:
            text += f"...and {len(failed)-5} more\n"
    await m.edit(text)

@app.on_message(filters.command("leave") & admin_only)
async def leave_cmd(client, message):
    if not ACTIVE_CALLS:
        return await message.reply("Koi active VC nahi")
    total = 0
    for cid in list(ACTIVE_CALLS.keys()):
        total += await leave_all(cid)
    await message.reply(f"⏹ **{total}** accounts ne leave kiya")

@app.on_message(filters.private & admin_only & filters.text)
async def text_handler(client, message):
    uid = message.from_user.id
    text = message.text.strip()
    if text.startswith("/"):
        return
    if uid in WAIT_PHONE:
        WAIT_PHONE.discard(uid)
        if not text.startswith("+"):
            return await message.reply("❌ Format: `+91xxxxxxxxxx`")
        try:
            await start_session(uid, text)
            WAIT_OTP.add(uid)
            await message.reply("📩 OTP bhej")
        except Exception as e:
            await message.reply(f"❌ {e}")
        return
    if uid in WAIT_OTP:
        WAIT_OTP.discard(uid)
        status, msg = await verify_otp(uid, text)
        if status == "password":
            WAIT_PASS.add(uid)
        await message.reply(msg)
        return

@app.on_callback_query()
async def cb(client, q: CallbackQuery):
    if q.from_user.id != ADMIN_ID:
        return await q.answer("❌ Unauthorized", show_alert=True)
    if q.data == "stats":
        await q.answer(f"Accounts: {len(SESSIONS)} | Active VC: {len(ACTIVE_CALLS)}", show_alert=True)
    elif q.data == "accounts":
        names = ", ".join(d["me"]["name"] for d in SESSIONS.values()) or "none"
        await q.answer(f"{len(SESSIONS)}: {names[:180]}", show_alert=True)
    elif q.data == "leaveall":
        total = 0
        for cid in list(ACTIVE_CALLS.keys()):
            total += await leave_all(cid)
        await q.answer(f"{total} left", show_alert=True)

@app.on_message(filters.private & ~admin_only)
async def unauthorized(client, message):
    return

if __name__ == "__main__":
    print("🤖 Bot start...")
    app.run()
