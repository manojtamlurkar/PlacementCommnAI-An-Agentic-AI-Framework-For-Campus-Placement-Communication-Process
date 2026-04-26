"""
One-time setup script: run this ONCE to authenticate Telethon and save the session file.
After this, the backend can create Telegram groups without any manual OTP input.

Run: venv\Scripts\python setup_telegram_session.py
"""
import os
from dotenv import load_dotenv
load_dotenv()

from telethon.sync import TelegramClient

API_ID   = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
PHONE    = os.getenv("TELEGRAM_PHONE")
SESSION  = "telegram_session"

print(f"Authenticating {PHONE} with Telegram...")
print("You will receive an OTP code on your Telegram app or via SMS.")
print()

with TelegramClient(SESSION, API_ID, API_HASH) as client:
    client.start(phone=PHONE)
    me = client.get_me()
    print(f"✅ Authenticated successfully as: {me.first_name} ({me.username})")
    print(f"Session saved to: {SESSION}.session")
    print()
    print("You can now start the backend — group creation will work automatically.")
