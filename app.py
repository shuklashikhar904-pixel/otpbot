import asyncio
import aiohttp
import json
import os
import re
from datetime import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession

API_ID = 33576198
API_HASH = "7b59cd4d6fed5c8aa9c794f204e25050"
BOT_TOKEN = "8936958039:AAF_F4f0VMzc_rZtdhqrKuunSnJ34FvuO94"
ADMIN_IDS = [8646237754]
BOT_USERNAME = "trusteddealers07bot"
UPI_ID = "shikharshukla606@naviaxis"
UPI_NAME = "Shikhar Shukla"
SUPPORT = "@deathalive07"

CHANNELS = [
    {"user": "@trusteddealers07", "link": "https://t.me/trusteddealers07"},
    {"user": "@trusteddealers_07", "link": "https://t.me/trusteddealers_07"}
]

REFERRAL_BONUS = 0.40
MIN_ADD_FUND = 15.00
BONUS_THRESHOLD = 400.00
BONUS_PERCENT = 10
DB_FILE = "/home/container/db.json"
SESSIONS_FILE = "/home/container/sessions.txt"

def load_db():
    if not os.path.exists(DB_FILE):
        return {"users": {}, "accounts": [], "pending": [], "orders": []}
    try:
        with open(DB_FILE) as f:
            return json.load(f)
    except Exception:
        return {"users": {}, "accounts": [], "pending": [], "orders": []}

def save_db():
    try:
        with open(DB_FILE, "w") as f:
            json.dump(DB, f, indent=2)
    except Exception as e:
        print("db save err:", e)

DB = load_db()

def get_user(uid):
    uid = str(uid)
    if uid not in DB["users"]:
        DB["users"][uid] = {"balance": 0.0, "step": "menu", "temp": {}, "refs": [], "orders": []}
    return DB["users"][uid]

HTTP = None

async def api(method, **kwargs):
    url = "https://api.telegram.org/bot" + BOT_TOKEN + "/" + method
    try:
        async with HTTP.post(url, json=kwargs) as r:
            return await r.json()
    except Exception as e:
        print("api err", method, e)
        return {"ok": False}

async def send(chat_id, text, kb=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if kb:
        payload["reply_markup"] = json.dumps(kb)
    await api("sendMessage", **payload)

async def get_member(chat_id, user_id):
    r = await api("getChatMember", chat_id=chat_id, user_id=user_id)
    if r.get("ok"):
        return r["result"].get("status", "left")
    return "left"
  def user_kb():
    return {"keyboard": [
        [{"text": "Buy Account"}, {"text": "My Orders"}],
        [{"text": "Add Funds"}, {"text": "Profile"}],
        [{"text": "Earn Opportunity"}, {"text": "Guide"}],
        [{"text": "Support"}, {"text": "Channel"}]
    ], "resize_keyboard": True}

def admin_kb():
    return {"keyboard": [
        [{"text": "Add Account"}, {"text": "List Accounts"}],
        [{"text": "Pending Payments"}, {"text": "Stats"}],
        [{"text": "Broadcast"}, {"text": "Back"}]
    ], "resize_keyboard": True}

def menu_kb(uid):
    return admin_kb() if uid in ADMIN_IDS else user_kb()

USERBOTS = []

async def deliver_otp(phone, otp):
    for a in DB["accounts"]:
        if a.get("phone") == phone and a.get("sold_to"):
            buyer = int(a["sold_to"])
            try:
                await send(buyer, "<b>OTP Received</b>\n\nNumber: <code>" + phone + "</code>\nOTP: <code>" + otp + "</code>\n\nEnter it fast.")
            except Exception as e:
                print("otp send err", e)
            for adm in ADMIN_IDS:
                try:
                    await send(adm, "OTP for " + phone + " -> " + otp)
                except Exception:
                    pass
            return

async def start_userbots():
    if not os.path.exists(SESSIONS_FILE):
        print("[userbot] no sessions file")
        return
    with open(SESSIONS_FILE) as f:
        lines = [l.strip() for l in f if l.strip() and "|" in l]
    print("[userbot] loading", len(lines), "sessions")
    for line in lines:
        phone, sstr = line.split("|", 1)
        try:
            c = TelegramClient(StringSession(sstr), API_ID, API_HASH)
            await c.connect()
            if not await c.is_user_authorized():
                print("[userbot]", phone, "not authorized")
                await c.disconnect()
                continue
            me = await c.get_me()
            print("[userbot]", phone, "online as", me.first_name)

            @c.on(events.NewMessage(from_users=777000))
            async def h(event, phone=phone):
                txt = event.raw_text or ""
                m = re.search(r"(\d{4,6})", txt)
                if not m:
                    return
                otp = m.group(1)
                print("[OTP]", phone, "->", otp)
                await deliver_otp(phone, otp)

            USERBOTS.append((phone, c))
        except Exception as e:
            print("[userbot]", phone, "fail:", e)

async def check_join(uid):
    for ch in CHANNELS:
        st = await get_member(ch["user"], uid)
        if st not in ("creator", "administrator", "member", "restricted"):
            return False
    return True

async def join_msg(cid, name):
    rows = []
    for i, ch in enumerate(CHANNELS):
        rows.append([{"text": "Join Channel " + str(i+1), "url": ch["link"]}])
    rows.append([{"text": "Verify Join", "url": "https://t.me/" + BOT_USERNAME + "?start=verify"}])
    await send(cid, "Hey " + name + ",\n\nJoin both channels then tap Verify.", {"inline_keyboard": rows})

async def handle(update):
    msg = update.get("message")
    if not msg:
        return
    chat = msg.get("chat", {})
    user = msg.get("from", {})
    uid = user.get("id", 0)
    cid = chat.get("id", uid)
    fname = user.get("first_name", "user")
    text = msg.get("text", "")
    cmd = text.split("@")[0].strip()
    low = cmd.lower()

    u = get_user(uid)
    save_db()

    if not await check_join(uid):
        await join_msg(cid, fname)
        return

    is_admin = uid in ADMIN_IDS
    kb = menu_kb(uid)

    if "ref_" in text:
        m = re.search(r"ref_(\d+)", text)
        if m:
            ref_id = int(m.group(1))
            if ref_id != uid and not u.get("referred_by"):
                u["referred_by"] = ref_id
                ref_u = get_user(ref_id)
                ref_u["refs"].append(uid)
                ref_u["balance"] += REFERRAL_BONUS
                save_db()
                try:
                    await send(ref_id, "New referral! +Rs" + str(REFERRAL_BONUS))
                except Exception:
                    pass

    if low in ("/start", "/menu", "/cancel", "back", ""):
        u["step"] = "menu"
        u["temp"] = {}
        save_db()
        if is_admin:
            stock = len([a for a in DB["accounts"] if not a.get("sold")])
            await send(cid,
                "<b>ADMIN PANEL</b>\n\nStock: " + str(stock) +
                "\nUsers: " + str(len(DB["users"])) +
                "\nPending: " + str(len(DB["pending"])), kb)
        else:
            await send(cid,
                "<b>Premium Telegram Accounts Store</b>\n\nWelcome, " + fname +
                "!\nID: <code>" + str(uid) + "</code>\nBalance: Rs" + str(round(u["balance"],2)) +
                "\n\nChoose an option below:", kb)
        return

    if low == "buy account":
        avail = [a for a in DB["accounts"] if not a.get("sold")]
        if not avail:
            await send(cid, "No accounts in stock.", kb)
            return
        countries = sorted(set(a.get("country", "Unknown") for a in avail))
        u["step"] = "buy_country"
        u["temp"] = {"countries": countries}
        save_db()
        lines = "\n".join(str(i+1) + ". " + c for i, c in enumerate(countries))
        await send(cid, "<b>Choose country</b>\n\n" + lines + "\n\nReply with the number.", kb)
        return

    if u["step"] == "buy_country":
        try:
            country = u["temp"]["countries"][int(cmd) - 1]
        except Exception:
            await send(cid, "Invalid.", kb)
            return
        avail = [a for a in DB["accounts"] if not a.get("sold") and a.get("country") == country]
        u["step"] = "buy_pick"
        u["temp"]["filtered"] = [a["id"] for a in avail]
        save_db()
        lines = []
        for i, a in enumerate(avail):
            lines.append(str(i+1) + ". " + a.get("age","Fresh") + " - Rs" + str(a.get("price",0)))
        await send(cid, "<b>" + country + "</b>\n\n" + "\n".join(lines) + "\n\nReply with the number.", kb)
        return

    if u["step"] == "buy_pick":
        try:
            acc_id = u["temp"]["filtered"][int(cmd) - 1]
        except Exception:
            await send(cid, "Invalid.", kb)
            return
        acc = next((a for a in DB["accounts"] if a["id"] == acc_id and not a.get("sold")), None)
        if not acc:
            u["step"] = "menu"; save_db()
            await send(cid, "Not available.", kb)
            return
        if u["balance"] < acc.get("price", 0):
            u["step"] = "menu"; save_db()
            await send(cid, "Insufficient balance.\nPrice: Rs" + str(acc["price"]) +
                       "\nYour balance: Rs" + str(round(u["balance"],2)) + "\n\nTap Add Funds.", kb)
            return
        u["step"] = "buy_confirm"
        u["temp"]["acc_id"] = acc_id
        save_db()
        await send(cid, "<b>Confirm Purchase</b>\n\nCountry: " + str(acc.get("country")) +
                   "\nAge: " + str(acc.get("age","Fresh")) +
                   "\nPrice: Rs" + str(acc["price"]) + "\n\nReply YES or NO.", kb)
        return

    if u["step"] == "buy_confirm":
        ans = cmd.upper()
        if ans in ("NO", "N", "CANCEL"):
            u["step"] = "menu"; save_db()
            await send(cid, "Cancelled.", kb)
            return
        if ans not in ("YES", "Y"):
            await send(cid, "Reply YES or NO.", kb)
            return
        acc = next((x for x in DB["accounts"] if x["id"] == u["temp"]["acc_id"] and not x.get("sold")), None)
        if not acc:
            u["step"] = "menu"; save_db()
            await send(cid, "Already sold.", kb)
            return
        if u["balance"] < acc["price"]:
            u["step"] = "menu"; save_db()
            await send(cid, "Insufficient.", kb)
            return
        acc["sold"] = True
        acc["sold_to"] = uid
        u["balance"] -= acc["price"]
        u["orders"].append({"acc_id": acc["id"], "phone": acc.get("phone")})
        u["step"] = "menu"
        save_db()
        txt = ("<b>Purchase Successful!</b>\n\n"
               "Country: " + str(acc.get("country")) + "\n"
               "Age: " + str(acc.get("age","Fresh")) + "\n"
               "Phone: <code>" + str(acc.get("phone")) + "</code>\n"
               "2FA Password: <code>" + str(acc.get("twofa","none")) + "</code>\n\n"
               "<b>How to log in:</b>\n"
               "1. Open Telegram\n"
               "2. Log in with this phone number\n"
               "3. OTP will arrive here automatically\n"
               "4. If asked for 2FA, use the password above\n\n"
               "Support: " + SUPPORT)
        await send(cid, txt, kb)
        for adm in ADMIN_IDS:
            try:
                await send(adm, "Sale! User " + str(uid) + " bought " + str(acc.get("phone")))
            except Exception:
                pass
        return

    if low == "my orders":
        if not u["orders"]:
            await send(cid, "No orders yet.", kb)
            return
        lines = []
        for i, o in enumerate(u["orders"]):
            lines.append(str(i+1) + ". Phone: <code>" + str(o.get("phone")) + "</code>")
        await send(cid, "<b>Your Orders</b>\n\n" + "\n".join(lines), kb)
        return

    if low == "add funds":
        u["step"] = "fund_amount"
        save_db()
        await send(cid,
            "<b>Add Funds</b>\n\n"
            "Min: Rs" + str(MIN_ADD_FUND) + "\n"
            "Bonus: " + str(BONUS_PERCENT) + "% above Rs" + str(int(BONUS_THRESHOLD)) + "\n\n"
            "Pay via UPI:\nUPI ID: <code>" + UPI_ID + "</code>\nName: " + UPI_NAME + "\n\n"
            "Send the amount in rupees.", kb)
        return

    if u["step"] == "fund_amount":
        try:
            amt = float(cmd)
        except Exception:
            await send(cid, "Invalid amount.", kb)
            return
        if amt < MIN_ADD_FUND:
            await send(cid, "Min is Rs" + str(MIN_ADD_FUND), kb)
            return
        u["step"] = "fund_utr"
        u["temp"]["amt"] = amt
        save_db()
        preview = ""
        if amt >= BONUS_THRESHOLD:
            b = amt * BONUS_PERCENT / 100
            preview = "\nBonus: +Rs" + str(round(b,2)) + " -> total Rs" + str(round(amt + b,2))
        await send(cid,
            "<b>Amount: Rs" + str(round(amt,2)) + "</b>" + preview + "\n\n"
            "Pay to UPI: <code>" + UPI_ID + "</code>\nName: " + UPI_NAME + "\n\n"
            "After paying, send the UTR here.", kb)
        return

    if u["step"] == "fund_utr":
        DB["pending"].append({
            "uid": uid,
            "amount": u["temp"]["amt"],
            "proof": cmd,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        u["step"] = "menu"
        save_db()
        await send(cid, "Submitted. Admin will verify.", kb)
        for adm in ADMIN_IDS:
            try:
                await send(adm, "<b>Payment Claim</b>\nUser: " + str(uid) +
                           "\nAmount: Rs" + str(u["temp"]["amt"]) + "\nUTR: " + cmd)
            except Exception:
                pass
        return

    if low == "profile":
        await send(cid,
            "<b>Profile</b>\n\n"
            "ID: <code>" + str(uid) + "</code>\n"
            "Balance: Rs" + str(round(u["balance"],2)) + "\n"
            "Orders: " + str(len(u["orders"])) + "\n"
            "Referrals: " + str(len(u["refs"])) + "\n\n"
            "Referral link:\nhttps://t.me/" + BOT_USERNAME + "?start=ref_" + str(uid), kb)
        return

    if low == "earn opportunity":
        await send(cid,
            "<b>Earn Opportunity</b>\n\n"
            "Earn Rs" + str(REFERRAL_BONUS) + " per friend.\n\n"
            "Your link:\nhttps://t.me/" + BOT_USERNAME + "?start=ref_" + str(uid), kb)
        return

    if low == "guide":
        await send(cid,
            "<b>Guide</b>\n\n"
            "1. Add funds via UPI\n"
            "2. Buy Account\n"
            "3. Bot gives phone number + 2FA\n"
            "4. Log in on Telegram\n"
            "5. OTP arrives here automatically\n"
            "6. Enter OTP, done", kb)
        return

    if low == "support":
        await send(cid, "Contact: " + SUPPORT, kb)
        return

    if low == "channel":
        links = "\n".join(ch["link"] for ch in CHANNELS)
        await send(cid, "<b>Channels</b>\n\n" + links, kb)
        return    if is_admin:
        if low == "add account":
            u["step"] = "add_phone"
            save_db()
            await send(cid, "Add Account - Send phone number with country code, no +.", admin_kb())
            return
        if u["step"] == "add_phone":
            u["temp"]["phone"] = cmd
            u["step"] = "add_country"
            save_db()
            await send(cid, "Send country.", admin_kb())
            return
        if u["step"] == "add_country":
            u["temp"]["country"] = cmd
            u["step"] = "add_age"
            save_db()
            await send(cid, "Send age (Fresh / 7d / 30d).", admin_kb())
            return
        if u["step"] == "add_age":
            u["temp"]["age"] = cmd
            u["step"] = "add_twofa"
            save_db()
            await send(cid, "Send 2FA password (or none).", admin_kb())
            return
        if u["step"] == "add_twofa":
            u["temp"]["twofa"] = cmd
            u["step"] = "add_price"
            save_db()
            await send(cid, "Send price in rupees.", admin_kb())
            return
        if u["step"] == "add_price":
            try:
                price = float(cmd)
            except Exception:
                await send(cid, "Invalid price.", admin_kb())
                return
            DB["accounts"].append({
                "id": len(DB["accounts"]) + 1,
                "phone": u["temp"]["phone"],
                "country": u["temp"]["country"],
                "age": u["temp"]["age"],
                "twofa": u["temp"]["twofa"],
                "price": price,
                "sold": False,
                "sold_to": None
            })
            u["step"] = "menu"
            u["temp"] = {}
            save_db()
            await send(cid, "Account added.", admin_kb())
            return

        if low == "list accounts":
            if not DB["accounts"]:
                await send(cid, "No accounts.", admin_kb())
                return
            lines = []
            for a in DB["accounts"][-30:]:
                s = "SOLD" if a.get("sold") else "OK"
                lines.append("#" + str(a["id"]) + " " + str(a.get("phone")) +
                             " " + str(a.get("country")) + " Rs" + str(a.get("price")) + " " + s)
            await send(cid, "<b>Accounts</b>\n\n" + "\n".join(lines), admin_kb())
            return

        if low == "pending payments":
            if not DB["pending"]:
                await send(cid, "No pending.", admin_kb())
                return
            lines = []
            for i, p in enumerate(DB["pending"]):
                lines.append("[" + str(i+1) + "] " + str(p["uid"]) + " Rs" + str(p["amount"]) + " | UTR " + str(p["proof"]))
            u["step"] = "pending_action"
            save_db()
            await send(cid, "<b>Pending Payments</b>\n\n" + "\n".join(lines) + "\n\nReply OK 1 or NO 1", admin_kb())
            return

        if u["step"] == "pending_action":
            m = re.match(r"^(OK|NO)\s+(\d+)$", cmd, re.I)
            if not m:
                await send(cid, "Reply OK 1 or NO 1.", admin_kb())
                return
            act = m.group(1).upper()
            idx = int(m.group(2)) - 1
            if idx < 0 or idx >= len(DB["pending"]):
                await send(cid, "Invalid index.", admin_kb())
                return
            item = DB["pending"].pop(idx)
            if act == "OK":
                buyer = get_user(item["uid"])
                bonus = 0
                if item["amount"] >= BONUS_THRESHOLD:
                    bonus = item["amount"] * BONUS_PERCENT / 100
                buyer["balance"] += item["amount"] + bonus
                save_db()
                try:
                    await send(item["uid"],
                        "Payment Approved!\nRecharged: Rs" + str(item["amount"]) +
                        "\nBonus: Rs" + str(round(bonus,2)) +
                        "\nBalance: Rs" + str(round(buyer["balance"],2)))
                except Exception:
                    pass
                await send(cid, "Approved.", admin_kb())
            else:
                try:
                    await send(item["uid"], "Payment rejected.")
                except Exception:
                    pass
                await send(cid, "Rejected.", admin_kb())
            u["step"] = "menu"
            save_db()
            return

        if low == "stats":
            stock = len([a for a in DB["accounts"] if not a.get("sold")])
            sold = len([a for a in DB["accounts"] if a.get("sold")])
            rev = sum(a.get("price", 0) for a in DB["accounts"] if a.get("sold"))
            await send(cid,
                "<b>Stats</b>\n\nUsers: " + str(len(DB["users"])) +
                "\nTotal: " + str(len(DB["accounts"])) +
                "\nStock: " + str(stock) +
                "\nSold: " + str(sold) +
                "\nRevenue: Rs" + str(round(rev,2)) +
                "\nPending: " + str(len(DB["pending"])), admin_kb())
            return

        if low == "broadcast":
            u["step"] = "bc"
            save_db()
            await send(cid, "Send message to broadcast.", admin_kb())
            return
        if u["step"] == "bc":
            ok = 0
            fail = 0
            for uid2 in list(DB["users"].keys()):
                try:
                    await send(int(uid2), cmd)
                    ok += 1
                except Exception:
                    fail += 1
            u["step"] = "menu"
            save_db()
            await send(cid, "Sent: " + str(ok) + ", Failed: " + str(fail), admin_kb())
            return

    await send(cid, "Unknown command. Use buttons.", kb)

async def poll():
    offset = 0
    while True:
        try:
            r = await api("getUpdates", offset=offset, timeout=25)
            if r.get("ok"):
                for up in r["result"]:
                    offset = up["update_id"] + 1
                    asyncio.create_task(handle(up))
        except Exception as e:
            print("poll err", e)
            await asyncio.sleep(3)

async def main():
    global HTTP
    HTTP = aiohttp.ClientSession()
    print("=== BOT STARTED ===")
    await start_userbots()
    print("=== POLLING ===")
    await poll()

if __name__ == "__main__":
    asyncio.run(main())
