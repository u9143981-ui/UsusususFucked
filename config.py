import os

API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8862389919:AAG-zWbqshCDAIbmWnvriAVJGpYp50Dyuq8")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "7589355685"))

SESSIONS = {}
ACTIVE_CALLS = {}
WAIT_PHONE = set()
WAIT_OTP = set()
WAIT_PASS = set()
