import asyncio
from config import SESSIONS, ACTIVE_CALLS

try:
    from pytgcalls import PyTgCalls
    from pytgcalls.types import GroupCallConfig
    ENGINE = "pytgcalls"
except ImportError:
    try:
        from tgcalls import pytgcalls
        ENGINE = "tgcalls"
    except ImportError:
        ENGINE = None

async def join_all(chat_id, delay: float = 0):
    if not ENGINE:
        return [], ["❌ tgcalls/pytgcalls install nahi"]
    if not SESSIONS:
        return [], ["❌ Koi account nahi. /session se add kar"]

    joined, failed = [], []
    items = list(SESSIONS.items())
    for i, (uid, data) in enumerate(items, 1):
        client = data["client"]
        try:
            if ENGINE == "pytgcalls":
                call = PyTgCalls(client)
                await call.start()
                try:
                    await call.join_group_call(chat_id, GroupCallConfig())
                except TypeError:
                    await call.join_group_call(chat_id)
            else:
                call = pytgcalls(client)
                await call.join_group_call(chat_id)
            ACTIVE_CALLS.setdefault(chat_id, []).append({"uid": uid, "call": call})
            joined.append(uid)
        except Exception as e:
            failed.append(f"{uid}: {str(e)[:80]}")
        if delay and i < len(items):
            await asyncio.sleep(delay)
    return joined, failed

async def leave_all(chat_id):
    items = ACTIVE_CALLS.get(chat_id, [])
    left = 0
    for item in items:
        call = item["call"]
        try:
            try:
                await call.leave_group_call(chat_id)
            except AttributeError:
                await call.leave_current_group_call()
            left += 1
        except Exception:
            pass
    ACTIVE_CALLS.pop(chat_id, None)
    return left
