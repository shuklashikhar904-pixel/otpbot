import subprocess
import sys

try:
    import telethon
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "telethon", "aiohttp"])

import asyncio
import aiohttp
import json
import os
import re
import random
from urllib.parse import quote
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

COUNTRIES = [
    "India", "Myanmar", "USA", "UK", "Indonesia", "Philippines", "Vietnam",
    "Bangladesh", "Pakistan", "Sri Lanka", "Nepal", "Nigeria", "Ghana",
    "Kenya", "South Africa", "Egypt", "Morocco", "UAE", "Saudi Arabia",
    "Turkey", "Iran", "Iraq", "Israel", "Russia", "Ukraine", "Poland",
    "Germany", "France", "Spain", "Italy", "Portugal", "Netherlands",
    "Belgium", "Sweden", "Norway", "Denmark", "Finland", "Ireland",
    "Switzerland", "Austria", "Greece", "Czech Republic", "Romania",
    "Hungary", "Bulgaria", "Serbia", "Croatia", "Thailand", "Malaysia",
    "Singapore", "China", "Japan", "South Korea", "Taiwan", "Hong Kong",
    "Australia", "New Zealand", "Canada", "Mexico", "Brazil", "Argentina",
    "Chile", "Colombia", "Peru", "Venezuela", "Ecuador", "Bolivia",
    "Paraguay", "Uruguay", "Cuba", "Dominican Republic", "Guatemala",
    "Honduras", "El Salvador", "Nicaragua", "Costa Rica", "Panama",
    "Jamaica", "Haiti", "Puerto Rico", "Afghanistan", "Albania",
    "Algeria", "Angola", "Armenia", "Azerbaijan", "Bahrain", "Belarus",
    "Benin", "Bhutan", "Botswana", "Burkina Faso", "Burundi", "Cambodia",
    "Cameroon", "Chad", "Congo", "Cyprus", "Djibouti", "Estonia",
    "Ethiopia", "Fiji", "Gabon", "Gambia", "Georgia", "Iceland",
    "Ivory Coast", "Jordan", "Kazakhstan", "Kuwait", "Kyrgyzstan",
    "Laos", "Latvia", "Lebanon", "Liberia", "Libya", "Lithuania",
    "Luxembourg", "Madagascar", "Malawi", "Maldives", "Mali", "Malta",
    "Mauritania", "Mauritius", "Moldova", "Mongolia", "Montenegro",
    "Mozambique", "Namibia", "Oman", "Palestine", "Papua New Guinea",
    "Qatar", "Rwanda", "Senegal", "Sierra Leone", "Slovakia", "Slovenia",
    "Somalia", "Sudan", "Syria", "Tajikistan", "Tanzania", "Togo",
    "Tunisia", "Turkmenistan", "Uganda", "Uzbekistan", "Yemen",
    "Zambia", "Zimbabwe"
]

REF_BONUS = 0.40
MIN_FUND = 15.00
BONUS_AT = 400.00
BONUS_PCT = 10

DB_FILE = "/home/container/db.json"
SESS_FILE = "/home/container/sessions.txt"
LINE = "\u2501" * 18

LOGIN_CLIENTS = {}


def load_db():
    if not os.path.exists(DB_FILE):
        return {"users": {}, "accounts": [], "pending": [], "giveaways": []}
    try:
        with open(DB_FILE) as f:
            d = json.load(f)
            if "giveaways" not in d:
                d["giveaways"] = []
            if "pending" not in d:
                d["pending"] = []
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
            "balance": 0.0, "step": "menu", "temp": {},
            "refs": [], "orders": [], "wins": 0, "attempts": {}
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


async def send_photo(cid, photo_url, caption):
    await api("sendPhoto", chat_id=cid, photo=photo_url, caption=caption, parse_mode="HTML")


async def edit(cid, mid, text, kb=None):
    p = {"chat_id": cid, "message_id": mid, "text": text, "parse_mode": "HTML"}
    if kb:
        p["reply_markup"] = json.dumps(kb)
    await api("editMessageText", **p)


async def member(chat_id, user_id):
    r = await api("getChatMember", chat_id=chat_id, user_id=user_id)
    if r.get("ok"):
        return r["result"].get("status", "left")
    return "left"


def qr_url(amount):
    upi = "upi://pay?pa=" + quote(UPI_ID) + "&pn=" + quote(UPI_NAME) + "&am=" + str(round(amount, 2)) + "&cu=INR"
    return "https://api.qrserver.com/v1/create-qr-code/?size=400x400&data=" + quote(upi)


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
        [{"text": "\U0001F510 Login Session"}, {"text": "\U0001F4C1 Sessions"}],
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
            t = "\U0001F4E9 <b>OTP RECEIVED</b>\n" + LINE + "\n\n"
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
        print("[userbot] no sessions file")
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
        rows.append([{"text": "\U0001F4E2 Join " + str(i+1), "url": ch["link"]}])
    rows.append([{"text": "\u2705 Verify", "url": "https://t.me/" + BOT_USER + "?start=verify"}])
    t = "\U0001F510 <b>Access Locked</b>\n" + LINE + "\n\n"
    t += "Hey <b>" + name + "</b>,\n\nJoin both channels to unlock.\n\n"
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


def account_button_label(a):
    return str(a.get("country", "")) + " - " + str(a.get("age", "Fresh")) + " - Rs" + str(a.get("price"))


async def handle_callback(cq):
    uid = cq["from"]["id"]
    cid = cq["message"]["chat"]["id"]
    mid = cq["message"]["message_id"]
    data = cq.get("data", "")
    u = get_user(uid)
    kb = menu_kb(uid)

    await api("answerCallbackQuery", callback_query_id=cq["id"])

    if data == "menu":
        await edit(cid, mid, "\u2728 Use the buttons below.", kb)
        return

    if data.startswith("acp_"):
        if uid not in ADMIN_IDS:
            return
        pg = int(data.split("_")[1])
        per_page = 6
        total = len(COUNTRIES)
        start = pg * per_page
        end = min(start + per_page, total)
        rows = []
        for i in range(start, end, 2):
            rows.append([{"text": c, "callback_data": "ac_" + c} for c in COUNTRIES[i:i+2]])
        nav = []
        if pg > 0:
            nav.append({"text": "\u25C0 Prev", "callback_data": "acp_" + str(pg-1)})
        if end < total:
            nav.append({"text": "More \u25B6", "callback_data": "acp_" + str(pg+1)})
        if nav:
            rows.append(nav)
        rows.append([{"text": "\u2B05\uFE0F Back", "callback_data": "menu"}])
        await edit(cid, mid, "\u2795 <b>Add Account</b> \u2022 page " + str(pg+1) + "\n" + LINE + "\n\nTap the <b>country</b>:", {"inline_keyboard": rows})
        return

    if data.startswith("ac_"):
        if uid not in ADMIN_IDS:
            return
        country = data.replace("ac_", "", 1)
        u["step"] = "add_pending"
        u["temp"] = {"add_country": country}
        save_db()
        t = "\U0001F30D <b>" + country + "</b>\n" + LINE + "\n\n"
        t += "Send in ONE line separated by <b>|</b> :\n\n"
        t += "<code>phone|age|2fa|price</code>\n\n"
        t += "Example:\n<code>919999999999|Fresh|pass123|50</code>\n\n"
        t += "Tags: Fresh / Rare / Old / 1 Year / 6 Months / anything"
        await edit(cid, mid, t, admin_kb())
        return

    if data.startswith("cc_"):
        country = data.replace("cc_", "", 1)
        avail = [a for a in DB["accounts"] if not a.get("sold") and a.get("country") == country]
        if not avail:
            await edit(cid, mid, "\u274C No accounts left for " + country, kb)
            return
        rows = []
        for a in avail:
            rows.append([{"text": account_button_label(a), "callback_data": "buy_" + str(a["id"])}])
        rows.append([{"text": "\u2B05\uFE0F Back", "callback_data": "menu"}])
        t = "<b>" + country + "</b>\n" + LINE + "\n\nTap an account to buy:"
        await edit(cid, mid, t, {"inline_keyboard": rows})
        return

    if data.startswith("buy_"):
        acc_id = int(data.replace("buy_", ""))
        acc = next((a for a in DB["accounts"] if a["id"] == acc_id and not a.get("sold")), None)
        if not acc:
            await edit(cid, mid, "\u274C Not available.", kb)
            return
        if u["balance"] < acc.get("price", 0):
            t = "\u26A0\uFE0F <b>Low Balance</b>\n" + LINE + "\n\n"
            t += "Price: Rs" + str(acc["price"]) + "\n"
            t += "Balance: Rs" + str(round(u["balance"], 2)) + "\n\nTap Add Funds"
            await edit(cid, mid, t, kb)
            return
        u["step"] = "confirm_" + str(acc_id)
        save_db()
        t = "\U0001F6D2 <b>Confirm Purchase</b>\n" + LINE + "\n\n"
        t += "Country: " + str(acc.get("country")) + "\n"
        t += "Age: " + str(acc.get("age", "Fresh")) + "\n"
        t += "Price: Rs" + str(acc.get("price")) + "\n\n"
        t += "Reply <b>YES</b> or <b>NO</b>"
        await edit(cid, mid, t, kb)
        return

    if data.startswith("approve_"):
        if uid not in ADMIN_IDS:
            return
        idx = int(data.split("_")[1])
        if idx < 0 or idx >= len(DB["pending"]):
            await edit(cid, mid, "\u274C Item gone.", admin_kb())
            return
        item = DB["pending"].pop(idx)
        buyer = get_user(item["uid"])
        bonus = 0
        if item["amount"] >= BONUS_AT:
            bonus = item["amount"] * BONUS_PCT / 100
        buyer["balance"] += item["amount"] + bonus
        save_db()
        try:
            t = "\u2705 <b>Approved</b>\n" + LINE + "\n\n"
            t += "Rs" + str(item["amount"])
            if bonus:
                t += " + Rs" + str(round(bonus, 2)) + " bonus"
            t += "\n\nNew balance Rs" + str(round(buyer["balance"], 2))
            await send(item["uid"], t)
        except Exception:
            pass
        await edit(cid, mid, "\u2705 Approved Rs" + str(item["amount"]), admin_kb())
        return

    if data.startswith("reject_"):
        if uid not in ADMIN_IDS:
            return
        idx = int(data.split("_")[1])
        if idx < 0 or idx >= len(DB["pending"]):
            await edit(cid, mid, "\u274C Item gone.", admin_kb())
            return
        item = DB["pending"].pop(idx)
        save_db()
        try:
            await send(item["uid"], "\u274C Rejected. Contact " + SUPPORT)
        except Exception:
            pass
        await edit(cid, mid, "\u274C Rejected.", admin_kb())
        return


async def handle(update):
    cq = update.get("callback_query")
    if cq:
        await handle_callback(cq)
        return

    msg = update.get("message")
    if not msg:
        return
    chat = msg.get("chat", {})
    user = msg.get("from", {})
    uid = user.get("id", 0)
    cid = chat.get("id", uid)
    fname = user.get("first_name", "user")
    text = msg.get("text", "")
    photo = msg.get("photo")
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
                    await send(ref_id, "\U0001F381 New referral +Rs" + str(REF_BONUS))
                except Exception:
                    pass

    if low in ("/start", "/menu", "/cancel", "back", "") or low == "\u2b05\ufe0f back":
        u["step"] = "menu"
        u["temp"] = {}
        save_db()
        if is_admin:
            stock = len([a for a in DB["accounts"] if not a.get("sold")])
            t = "\U0001F510 <b>ADMIN CONSOLE</b>\n" + LINE + "\n\n"
            t += "Stock <b>" + str(stock) + "</b>\n"
            t += "Users <b>" + str(len(DB["users"])) + "</b>\n"
            t += "Pending <b>" + str(len(DB["pending"])) + "</b>\n\n"
            t += "\u2728 Choose an option"
            await send(cid, t, kb)
        else:
            t = "\U0001F48E <b>PREMIUM TG STORE</b>\n" + LINE + "\n\n"
            t += "\U0001F44B Welcome <b>" + fname + "</b>\n\n"
            t += "ID <code>" + str(uid) + "</code>\n"
            t += "Balance <b>Rs" + str(round(u["balance"], 2)) + "</b>\n"
            t += "Wins <b>" + str(u["wins"]) + "</b>\n\n"
            t += "\u2728 Choose an option"
            await send(cid, t, kb)
        return

    if low in ("buy account", "\U0001F6D2 buy account"):
        avail = [a for a in DB["accounts"] if not a.get("sold")]
        if not avail:
            await send(cid, "\u274C No accounts in stock.", kb)
            return
        countries = sorted(set(a.get("country", "Unknown") for a in avail))
        rows = []
        for c in countries:
            cnt = len([a for a in avail if a.get("country") == c])
            rows.append([{"text": c + " (" + str(cnt) + ")", "callback_data": "cc_" + c}])
        rows.append([{"text": "\u2B05\uFE0F Back", "callback_data": "menu"}])
        await send(cid, "Choose Country\n" + LINE + "\n\nTap a country:", {"inline_keyboard": rows})
        return

    if u["step"].startswith("confirm_"):
        acc_id = int(u["step"].replace("confirm_", ""))
        ans = cmd.upper()
        if ans in ("NO", "N", "CANCEL"):
            u["step"] = "menu"
            save_db()
            await send(cid, "\U0001F6AB Cancelled.", kb)
            return
        if ans not in ("YES", "Y"):
            await send(cid, "Reply YES or NO.", kb)
            return
        acc = next((x for x in DB["accounts"] if x["id"] == acc_id and not x.get("sold")), None)
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
        t = "\u2705 <b>PURCHASED</b>\n" + LINE + "\n\n"
        t += "Phone <code>" + str(acc.get("phone")) + "</code>\n"
        t += "2FA <code>" + str(acc.get("twofa", "none")) + "</code>\n\n"
        t += "<b>How to Login</b>\n"
        t += "1. Open Telegram\n"
        t += "2. Log in with the phone above\n"
        t += "3. OTP arrives in this chat\n"
        t += "4. Enter 2FA when asked\n\n"
        t += "Support: " + SUPPORT
        await send(cid, t, kb)
        for adm in ADMIN_IDS:
            try:
                await send(adm, "Sale " + str(uid) + " bought " + str(acc.get("phone")))
            except Exception:
                pass
        return

    if low in ("my orders", "\U0001F4E6 my orders"):
        if not u["orders"]:
            await send(cid, "No orders yet.", kb)
            return
        t = "<b>Your Orders</b>\n" + LINE + "\n\n"
        for i, o in enumerate(u["orders"]):
            t += str(i+1) + ". <code>" + str(o.get("phone")) + "</code>\n"
        await send(cid, t, kb)
        return

    if low in ("add funds", "\U0001F4B0 add funds"):
        u["step"] = "fund_amount"
        save_db()
        t = "Add Funds\n" + LINE + "\n\n"
        t += "Minimum Rs" + str(int(MIN_FUND)) + "\n"
        t += "Bonus " + str(BONUS_PCT) + "% above Rs" + str(int(BONUS_AT)) + "\n\n"
        t += "Send the amount you want to add.\nExample: <code>100</code>"
        await send(cid, t, kb)
        return

    if u["step"] == "fund_amount":
        try:
            amt = float(cmd.replace("Rs", "").replace("rs", "").replace("\u20B9", "").strip())
        except Exception:
            await send(cid, "Send a number only. Example: 100", kb)
                        return

        if amt < MIN_FUND:
            await send(cid, "Minimum is Rs" + str(int(MIN_FUND)), kb)
            return
        u["step"] = "fund_utr"
        u["temp"]["amt"] = amt
        save_db()
        preview = ""
        if amt >= BONUS_AT:
            b = amt * BONUS_PCT / 100
            preview = "\n+" + str(round(b, 2)) + " bonus -> total Rs" + str(round(amt + b, 2))
        cap = "Pay Rs" + str(round(amt, 2)) + " to " + UPI_ID
        try:
            await send_photo(cid, qr_url(amt), cap)
        except Exception:
            pass
        t = "Pay Rs" + str(round(amt, 2)) + preview + "\n" + LINE + "\n\n"
        t += "UPI ID: <code>" + UPI_ID + "</code>\n"
        t += "Name: " + UPI_NAME + "\n\n"
        t += "Scan QR above or pay to UPI ID.\n\n"
        t += "After paying, send the UTR number here.\nYou can also send a screenshot."
        await send(cid, t, kb)
        return

    if u["step"] == "fund_utr":
        if not cmd and not photo:
            await send(cid, "Send UTR text or screenshot.", kb)
            return
        if photo and cmd:
            proof = cmd + " (+screenshot)"
        elif photo:
            proof = "screenshot only"
        else:
            proof = cmd
        DB["pending"].append({
            "uid": uid, "amount": u["temp"]["amt"],
            "proof": proof,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        u["step"] = "menu"
        save_db()
        await send(cid, "Submitted! Admin will verify soon.", kb)
        idx = len(DB["pending"]) - 1
        for adm in ADMIN_IDS:
            try:
                t = "NEW CLAIM\n" + LINE + "\n\n"
                t += "User <code>" + str(uid) + "</code>\n"
                t += "Rs" + str(u["temp"]["amt"]) + "\n"
                t += proof
                rows = [[
                    {"text": "\u2705 Approve", "callback_data": "approve_" + str(idx)},
                    {"text": "\u274C Reject", "callback_data": "reject_" + str(idx)}
                ]]
                await send(adm, t, {"inline_keyboard": rows})
            except Exception:
                pass
        return

    if low in ("profile", "\U0001F464 profile"):
        t = "Profile\n" + LINE + "\n\n"
        t += "<code>" + str(uid) + "</code>\n"
        t += "Balance Rs" + str(round(u["balance"], 2)) + "\n"
        t += "Orders " + str(len(u["orders"])) + "\n"
        t += "Refs " + str(len(u["refs"])) + "\n"
        t += "Wins " + str(u["wins"]) + "\n\n"
        t += "https://t.me/" + BOT_USER + "?start=ref_" + str(uid)
        await send(cid, t, kb)
        return

    if low in ("earn", "earn 5%", "\U0001F3AF earn 5%"):
        t = "Earn 5%\n" + LINE + "\n\n"
        t += "Invite friends, earn 5% of their first deposit.\n\n"
        t += "https://t.me/" + BOT_USER + "?start=ref_" + str(uid)
        await send(cid, t, kb)
        return

    if low in ("giveaway", "\U0001F381 giveaway"):
        g = current_giveaway()
        if not g:
            await send(cid, "No giveaway active.", kb)
            return
        if u["attempts"].get(str(g["id"])):
            await send(cid, "One chance only!", kb)
            return
        q, ans = math_question()
        u["temp"]["ga_ans"] = ans
        u["temp"]["ga_id"] = g["id"]
        u["step"] = "ga_answer"
        save_db()
        t = "GIVEAWAY\n" + LINE + "\n\n"
        t += "Prize Rs" + str(g["prize"]) + "\n\n"
        t += "<b>" + q + " = ?</b>\n\n"
        t += "One wrong = miss"
        await send(cid, t, kb)
        return

    if u["step"] == "ga_answer":
        g = next((x for x in DB["giveaways"] if x["id"] == u["temp"].get("ga_id")), None)
        if not g or not g.get("active"):
            u["step"] = "menu"
            save_db()
            await send(cid, "Giveaway ended.", kb)
            return
        if u["attempts"].get(str(g["id"])):
            u["step"] = "menu"
            save_db()
            await send(cid, "Already tried.", kb)
            return
        try:
            ans_int = int(cmd.strip())
        except Exception:
            await send(cid, "Reply with a number.", kb)
            return
        u["attempts"][str(g["id"])] = True
        if ans_int == u["temp"]["ga_ans"]:
            u["balance"] += g["prize"]
            u["wins"] += 1
            u["step"] = "menu"
            save_db()
            t = "CORRECT!\n" + LINE + "\n\n"
            t += "Won Rs" + str(g["prize"]) + "\n\n"
            t += "New balance Rs" + str(round(u["balance"], 2))
            await send(cid, t, kb)
        else:
            u["step"] = "menu"
            save_db()
            t = "WRONG\n" + LINE + "\n\n"
            t += "Correct was <b>" + str(u["temp"]["ga_ans"]) + "</b>"
            await send(cid, t, kb)
        return

    if low in ("guide", "\U0001F4D6 guide"):
        t = "Guide\n" + LINE + "\n\n"
        t += "1. Add funds via UPI QR\n"
        t += "2. Buy Account\n"
        t += "3. Get phone + 2FA after payment\n"
        t += "4. Log in Telegram\n"
        t += "5. OTP arrives here automatically\n\n"
        t += "Support: " + SUPPORT
        await send(cid, t, kb)
        return

    if low in ("support", "\U0001F198 support"):
        await send(cid, "Contact " + SUPPORT, kb)
        return

    if low in ("channel", "\U0001F4E2 channel"):
        links = "\n".join(ch["link"] for ch in CHANNELS)
        await send(cid, "Channels\n" + LINE + "\n\n" + links, kb)
        return

    if is_admin:

        if low in ("add account", "\u2795 add account"):
            per_page = 6
            total = len(COUNTRIES)
            start = 0
            end = min(per_page, total)
            rows = []
            for i in range(start, end, 2):
                rows.append([{"text": c, "callback_data": "ac_" + c} for c in COUNTRIES[i:i+2]])
            nav = []
            if end < total:
                nav.append({"text": "More \u25B6", "callback_data": "acp_1"})
            if nav:
                rows.append(nav)
            rows.append([{"text": "\u2B05\uFE0F Back", "callback_data": "menu"}])
            await send(cid, "Add Account\n" + LINE + "\n\nTap the country:", {"inline_keyboard": rows})
            return

        if u["step"] == "add_pending":
            country = u["temp"].get("add_country", "Unknown")
            parts = cmd.split("|")
            if len(parts) != 4:
                t = "Wrong format.\n\nSend: <code>phone|age|2fa|price</code>\n\nExample: <code>919999999999|Fresh|pass123|50</code>"
                await send(cid, t, admin_kb())
                return
            try:
                price = float(parts[3].strip())
            except Exception:
                await send(cid, "Invalid price.", admin_kb())
                return
            DB["accounts"].append({
                "id": len(DB["accounts"]) + 1,
                "phone": parts[0].strip(),
                "country": country,
                "age": parts[1].strip(),
                "twofa": parts[2].strip(),
                "price": price,
                "sold": False,
                "sold_to": None
            })
            u["step"] = "menu"
            u["temp"] = {}
            save_db()
            t = "Added\n" + LINE + "\n\n"
            t += country + "\n"
            t += parts[0].strip() + "\n"
            t += parts[1].strip() + "\n"
            t += parts[2].strip() + "\n"
            t += "Rs" + str(price)
            await send(cid, t, admin_kb())
            return

        if low in ("list accounts", "\U0001F4CB list accounts"):
            if not DB["accounts"]:
                await send(cid, "No accounts.", admin_kb())
                return
            t = "Accounts\n" + LINE + "\n\n"
            for a in DB["accounts"][-30:]:
                s = "SOLD" if a.get("sold") else "OK"
                t += "#" + str(a["id"]) + " " + str(a.get("country")) + " " + str(a.get("phone")) + " Rs" + str(a.get("price")) + " " + s + "\n"
            await send(cid, t, admin_kb())
            return

        if low in ("pending", "\U0001F4B8 pending"):
            if not DB["pending"]:
                await send(cid, "No pending.", admin_kb())
                return
            for i, p in enumerate(DB["pending"]):
                t = "CLAIM #" + str(i+1) + "\n" + LINE + "\n\n"
                t += "<code>" + str(p["uid"]) + "</code>\n"
                t += "Rs" + str(p["amount"]) + "\n"
                t += str(p["proof"]) + "\n"
                t += str(p["time"])
                rows = [[
                    {"text": "\u2705 Approve", "callback_data": "approve_" + str(i)},
                    {"text": "\u274C Reject", "callback_data": "reject_" + str(i)}
                ]]
                await send(cid, t, {"inline_keyboard": rows})
            return

        if low in ("login session", "\U0001F510 login session"):
            u["step"] = "login_phone"
            save_db()
            await send(cid, "Login Session\n" + LINE + "\n\nSend phone number (with country code, no +).\nExample: <code>919876543210</code>", admin_kb())
            return

        if u["step"] == "login_phone":
            phone = cmd.strip()
            try:
                client = TelegramClient(StringSession(), API_ID, API_HASH)
                await client.connect()
                sent = await client.send_code_request(phone)
                LOGIN_CLIENTS[str(uid)] = {"phone": phone, "client": client, "hash": sent.phone_code_hash}
                u["step"] = "login_code"
                save_db()
                await send(cid, "Code sent to Telegram app.\n\nSend the login code here.", admin_kb())
            except Exception as e:
                u["step"] = "menu"
                save_db()
                await send(cid, "Error: " + str(e), admin_kb())
            return

        if u["step"] == "login_code":
            info = LOGIN_CLIENTS.get(str(uid))
            if not info:
                u["step"] = "menu"
                save_db()
                await send(cid, "Lost. Start over.", admin_kb())
                return
            code = cmd.strip()
            try:
                await info["client"].sign_in(phone=info["phone"], code=code, phone_code_hash=info["hash"])
                me = await info["client"].get_me()
                sstr = info["client"].session.save()
                with open(SESS_FILE, "a") as f:
                    f.write(info["phone"] + "|" + sstr + "\n")
                await info["client"].disconnect()
                LOGIN_CLIENTS.pop(str(uid), None)
                u["step"] = "menu"
                save_db()
                await send(cid, "Logged in as " + (me.first_name or "?") + "\nSession saved!\n\nRestart the server to activate.", admin_kb())
            except Exception as e:
                err = str(e)
                if "password" in err.lower() or "SessionPasswordNeeded" in err:
                    u["step"] = "login_2fa"
                    save_db()
                    await send(cid, "2FA enabled.\n\nSend your 2FA password.", admin_kb())
                else:
                    u["step"] = "menu"
                    save_db()
                    try:
                        await info["client"].disconnect()
                    except Exception:
                        pass
                    LOGIN_CLIENTS.pop(str(uid), None)
                    await send(cid, "Error: " + err + "\n\nTry again with Login Session.", admin_kb())
            return

        if u["step"] == "login_2fa":
            info = LOGIN_CLIENTS.get(str(uid))
            if not info:
                u["step"] = "menu"
                save_db()
                await send(cid, "Lost. Start over.", admin_kb())
                return
            pwd = cmd.strip()
            try:
                await info["client"].sign_in(password=pwd)
                me = await info["client"].get_me()
                sstr = info["client"].session.save()
                with open(SESS_FILE, "a") as f:
                    f.write(info["phone"] + "|" + sstr + "\n")
                await info["client"].disconnect()
                LOGIN_CLIENTS.pop(str(uid), None)
                u["step"] = "menu"
                save_db()
                await send(cid, "Logged in as " + (me.first_name or "?") + "\nSession saved!\n\nRestart the server to activate.", admin_kb())
            except Exception as e:
                u["step"] = "menu"
                save_db()
                try:
                    await info["client"].disconnect()
                except Exception:
                    pass
                LOGIN_CLIENTS.pop(str(uid), None)
                await send(cid, "2FA wrong: " + str(e) + "\n\nStart over with Login Session.", admin_kb())
            return

        if low in ("sessions", "\U0001F4C1 sessions"):
            if not os.path.exists(SESS_FILE):
                await send(cid, "No sessions.", admin_kb())
                return
            with open(SESS_FILE) as f:
                lines = [l.strip() for l in f if l.strip() and "|" in l]
            t = "Sessions\n" + LINE + "\n\n"
            t += "Total: " + str(len(lines)) + "\n\n"
            for i, l in enumerate(lines):
                t += str(i+1) + ". " + l.split("|")[0] + "\n"
            await send(cid, t, admin_kb())
            return

        if low in ("add balance", "\U0001F4B5 add balance"):
            u["step"] = "ab_uid"
            save_db()
            await send(cid, "Send user UID.", admin_kb())
            return
        if u["step"] == "ab_uid":
            u["temp"]["uid"] = cmd
            u["step"] = "ab_amt"
            save_db()
            await send(cid, "Send amount.", admin_kb())
            return
        if u["step"] == "ab_amt":
            try:
                amt = float(cmd)
            except Exception:
                await send(cid, "Invalid.", admin_kb())
                return
            target = get_user(u["temp"]["uid"])
            target["balance"] += amt
            u["step"] = "menu"
            save_db()
            await send(cid, "Added Rs" + str(amt) + " to " + u["temp"]["uid"], admin_kb())
            try:
                await send(int(u["temp"]["uid"]), "Rs" + str(amt) + " added. New balance Rs" + str(round(target["balance"], 2)))
            except Exception:
                pass
            return

        if low in ("deduct balance", "\U0001F4B8 deduct balance"):
            u["step"] = "db_uid"
            save_db()
            await send(cid, "Send user UID.", admin_kb())
            return
        if u["step"] == "db_uid":
            u["temp"]["uid"] = cmd
            u["step"] = "db_amt"
            save_db()
            await send(cid, "Send amount.", admin_kb())
            return
        if u["step"] == "db_amt":
            try:
                amt = float(cmd)
            except Exception:
                await send(cid, "Invalid.", admin_kb())
                return
            target = get_user(u["temp"]["uid"])
            target["balance"] -= amt
            u["step"] = "menu"
            save_db()
            await send(cid, "Deducted Rs" + str(amt) + " from " + u["temp"]["uid"], admin_kb())
            return

        if low in ("create giveaway", "\U0001F381 create giveaway"):
            u["step"] = "ga_prize"
            save_db()
            await send(cid, "Send prize amount.", admin_kb())
            return
        if u["step"] == "ga_prize":
            try:
                prize = float(cmd)
            except Exception:
                await send(cid, "Invalid.", admin_kb())
                return
            for g in DB["giveaways"]:
                g["active"] = False
            DB["giveaways"].append({
                "id": len(DB["giveaways"]) + 1,
                "prize": prize,
                "active": True,
                "created": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            u["step"] = "menu"
            save_db()
            await send(cid, "Giveaway created Rs" + str(prize), admin_kb())
            return

        if low in ("stats", "\U0001F4CA stats"):
            stock = len([a for a in DB["accounts"] if not a.get("sold")])
            sold = len([a for a in DB["accounts"] if a.get("sold")])
            rev = sum(a.get("price", 0) for a in DB["accounts"] if a.get("sold"))
            t = "Stats\n" + LINE + "\n\n"
            t += "Users " + str(len(DB["users"])) + "\n"
            t += "Accounts " + str(len(DB["accounts"])) + "\n"
            t += "Stock " + str(stock) + "\n"
            t += "Sold " + str(sold) + "\n"
            t += "Revenue Rs" + str(round(rev, 2)) + "\n"
            t += "Pending " + str(len(DB["pending"]))
            await send(cid, t, admin_kb())
            return

        if low in ("broadcast", "\U0001F4E3 broadcast"):
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
            await send(cid, "Sent " + str(ok) + " Failed " + str(fail), admin_kb())
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
