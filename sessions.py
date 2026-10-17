from pyrogram import Client
from pyrogram.errors import SessionPasswordNeeded, PhoneCodeInvalid, PhoneCodeExpired
from config import API_ID, API_HASH, SESSIONS

_PENDING = {}

async def start_session(admin_id: int, phone: str):
    if admin_id in _PENDING:
        try:
            await _PENDING[admin_id]["client"].disconnect()
        except Exception:
            pass
    client = Client(
        name=f"tmp_{admin_id}_{phone}",
        api_id=API_ID,
        api_hash=API_HASH,
        in_memory=True,
    )
    await client.connect()
    sent = await client.send_code(phone)
    _PENDING[admin_id] = {
        "client": client,
        "phone": phone,
        "hash": sent.phone_code_hash,
    }
    return True

async def verify_otp(admin_id: int, otp: str):
    p = _PENDING.get(admin_id)
    if not p:
        return "error", "Pehle /session se number bhej"
    client = p["client"]
    try:
        await client.sign_in(p["phone"], p["hash"], otp)
    except SessionPasswordNeeded:
        return "password", "🔐 2FA on hai. Password bhej: `/password <pass>`"
    except PhoneCodeInvalid:
        return "error", "❌ OTP galat"
    except PhoneCodeExpired:
        return "error", "❌ OTP expire ho gaya, /session dobara"
    except Exception as e:
        return "error", f"❌ {e}"
    return await _finalize(admin_id, client)

async def verify_password(admin_id: int, password: str):
    p = _PENDING.get(admin_id)
    if not p:
        return "error", "Pehle /session"
    client = p["client"]
    try:
        await client.check_password(password)
    except Exception as e:
        return "error", f"❌ {e}"
    return await _finalize(admin_id, client)

async def _finalize(admin_id: int, client: Client):
    me = await client.get_me()
    if me.id in SESSIONS:
        return "ok", f"⚠️ Ye account pehle se added hai: {me.first_name}"
    SESSIONS[me.id] = {
        "client": client,
        "me": {
            "id": me.id,
            "name": me.first_name or "?",
            "username": me.username,
        },
    }
    _PENDING.pop(admin_id, None)
    return "ok", f"✅ Account add: **{me.first_name}** (`{me.id}`)\nTotal: {len(SESSIONS)}"
