import asyncio
import os
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = 33576198
API_HASH = "7b59cd4d6fed5c8aa9c794f204e25050"
SESSIONS_FILE = "/home/container/sessions.txt"

async def login_one(phone):
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.start(phone=phone)
    me = await client.get_me()
    print("LOGIN OK " + phone + " -> " + (me.first_name or "?"))
    sstr = client.session.save()
    with open(SESSIONS_FILE, "a") as f:
        f.write(phone + "|" + sstr + "\n")
    print("SAVED " + phone)
    await client.disconnect()

async def main():
    print("=== LOGIN TOOL ===")
    phones = []
    while True:
        try:
            p = input("phone: ").strip()
        except EOFError:
            break
        if p == "" or p.lower() == "done":
            break
        phones.append(p)
    for phone in phones:
        try:
            await login_one(phone)
        except Exception as e:
            print("FAIL " + phone + ": " + str(e))
    print("=== DONE ===")

if __name__ == "__main__":
    asyncio.run(main())
