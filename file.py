# bot.py — File Store Bot
# Owner: 8646237754
# Run: python bot.py

import os
import time
import sqlite3
import logging
from datetime import datetime

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from telegram.constants import ChatMemberStatus

# ================= CONFIG =================
BOT_TOKEN = "8919561650:AAErt6SOp7cT_q5Da1gEEotiJFRE6kLdLyc"
OWNER_ID = 8646237754

FORCED_CHANNELS = [
    {"id": "@trusteddealers07",  "name": "Trusted Dealers", "link": "https://t.me/trusteddealers07"},
    {"id": "@trusteddealers_07", "name": "Trusted backup",  "link": "https://t.me/trusteddealers_07"},
    {"id": "@trustmebaby07",     "name": "Trust Me Baby",   "link": "https://t.me/trustmebaby07"},
]

DB_PATH = "data/bot.db"
FILES_DIR = "files"

COIN_PER_REFERRAL = 40
POINT_PER_REFERRAL = 10
BONUS_AT_POINTS = 10
BONUS_COINS = 40

# ================= DB =================
def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = _conn(); c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY,
        username TEXT, first_name TEXT,
        coins INTEGER DEFAULT 0, points INTEGER DEFAULT 0,
        referred_by INTEGER, joined_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS files(
        file_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, file_path TEXT, price INTEGER,
        uploader_id INTEGER, uploaded_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS admins(
        user_id INTEGER PRIMARY KEY, username TEXT,
        added_by INTEGER, added_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS purchases(
        user_id INTEGER, file_id INTEGER, price INTEGER,
        purchased_at TEXT, PRIMARY KEY(user_id, file_id))""")
    conn.commit(); conn.close()

def get_user(uid):
    conn = _conn(); c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE user_id=?", (uid,))
    r = c.fetchone(); conn.close(); return r

def create_user(uid, username, first_name, referred_by=None):
    conn = _conn(); c = conn.cursor()
    coins = COIN_PER_REFERRAL if referred_by else 0
    c.execute("""INSERT OR IGNORE INTO users
        (user_id,username,first_name,coins,points,referred_by,joined_at)
        VALUES(?,?,?,?,0,?,?)""",
        (uid, username, first_name, coins, referred_by, datetime.now().isoformat()))
    conn.commit(); conn.close()

def add_coins(uid, amt):
    conn = _conn(); c = conn.cursor()
    c.execute("UPDATE users SET coins = MAX(0, coins + ?) WHERE user_id=?", (amt, uid))
    conn.commit(); conn.close()

def set_coins(uid, amt):
    conn = _conn(); c = conn.cursor()
    c.execute("UPDATE users SET coins=? WHERE user_id=?", (max(0, amt), uid))
    conn.commit(); conn.close()

def get_coins(uid):
    conn = _conn(); c = conn.cursor()
    c.execute("SELECT coins FROM users WHERE user_id=?", (uid,))
    r = c.fetchone(); conn.close(); return r[0] if r else 0

def add_refer_point(uid):
    conn = _conn(); c = conn.cursor()
    c.execute("UPDATE users SET points=points+1 WHERE user_id=?", (uid,))
    c.execute("SELECT points FROM users WHERE user_id=?", (uid,))
    r = c.fetchone()
    pts = r[0] if r else 0
    conn.commit(); conn.close(); return pts

def get_points(uid):
    conn = _conn(); c = conn.cursor()
    c.execute("SELECT points FROM users WHERE user_id=?", (uid,))
    r = c.fetchone(); conn.close(); return r[0] if r else 0

def count_referrals(uid):
    conn = _conn(); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE referred_by=?", (uid,))
    r = c.fetchone(); conn.close(); return r[0] if r else 0

def add_file(name, path, price, uploader):
    conn = _conn(); c = conn.cursor()
    c.execute("""INSERT INTO files(name,file_path,price,uploader_id,uploaded_at)
        VALUES(?,?,?,?,?)""", (name, path, price, uploader, datetime.now().isoformat()))
    fid = c.lastrowid; conn.commit(); conn.close(); return fid

def list_files():
    conn = _conn(); c = conn.cursor()
    c.execute("SELECT file_id,name,price FROM files ORDER BY file_id")
    r = c.fetchall(); conn.close(); return r

def get_file(fid):
    conn = _conn(); c = conn.cursor()
    c.execute("SELECT * FROM files WHERE file_id=?", (fid,))
    r = c.fetchone(); conn.close(); return r

def set_file_price(fid, price):
    conn = _conn(); c = conn.cursor()
    c.execute("UPDATE files SET price=? WHERE file_id=?", (price, fid))
    changed = c.rowcount
    conn.commit(); conn.close(); return changed > 0

def has_purchased(uid, fid):
    conn = _conn(); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM purchases WHERE user_id=? AND file_id=?", (uid, fid))
    r = c.fetchone(); conn.close(); return (r[0] > 0) if r else False

def add_purchase(uid, fid, price):
    conn = _conn(); c = conn.cursor()
    c.execute("""INSERT OR IGNORE INTO purchases(user_id,file_id,price,purchased_at)
        VALUES(?,?,?,?)""", (uid, fid, price, datetime.now().isoformat()))
    conn.commit(); conn.close()

def add_admin(uid, username, added_by):
    conn = _conn(); c = conn.cursor()
    c.execute("""INSERT OR REPLACE INTO admins(user_id,username,added_by,added_at)
        VALUES(?,?,?,?)""", (uid, username, added_by, datetime.now().isoformat()))
    conn.commit(); conn.close()

def remove_admin(uid):
    conn = _conn(); c = conn.cursor()
    c.execute("DELETE FROM admins WHERE user_id=?", (uid,))
    conn.commit(); conn.close()

def is_admin_db(uid):
    conn = _conn(); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM admins WHERE user_id=?", (uid,))
    r = c.fetchone(); conn.close(); return (r[0] > 0) if r else False

def list_admins():
    conn = _conn(); c = conn.cursor()
    c.execute("SELECT user_id,username FROM admins")
    r = c.fetchall(); conn.close(); return r

# ================= HELPERS =================
logging.basicConfig(level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

user_state = {}

def is_owner(uid):
    return uid == OWNER_ID

def is_admin(uid):
    return uid == OWNER_ID or is_admin_db(uid)

async def check_join(bot, uid):
    missing = []
    for ch in FORCED_CHANNELS:
        try:
            m = await bot.get_chat_member(ch["id"], uid)
            if m.status in (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED):
                missing.append(ch)
        except Exception as e:
            logger.warning(f"join check failed for {ch['id']}: {e}")
    return missing

def join_keyboard(missing):
    kb = []
    for ch in missing:
        kb.append([InlineKeyboardButton(f"📢 Join {ch['name']}", url=ch["link"])])
    kb.append([InlineKeyboardButton("✅ I Joined — Check", callback_data="check_join")])
    return InlineKeyboardMarkup(kb)

# ================= HANDLERS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id
    args = context.args or []

    referred_by = None
    if args and isinstance(args, list) and args[0].startswith("ref_"):
        try:
            r = int(args[0][4:])
            if r != uid: referred_by = r
        except (ValueError, IndexError):
            pass

    if get_user(uid) is None:
        create_user(uid, user.username, user.first_name, referred_by)
        if referred_by:
            pts = add_refer_point(referred_by)
            if pts % BONUS_AT_POINTS == 0:
                add_coins(referred_by, BONUS_COINS)
                try:
                    await context.bot.send_message(referred_by,
                        f"🎉 *Bonus Unlocked!*\n\nYou reached *{pts} points*!\n+{BONUS_COINS} coins.",
                        parse_mode='Markdown')
                except Exception:
                    pass

    missing = await check_join(context.bot, uid)
    if missing:
        await update.message.reply_text(
            "🔒 *Please join all channels to use this bot.*",
            parse_mode='Markdown', reply_markup=join_keyboard(missing))
        return
    await show_main_menu(update, context, uid)

async def show_main_menu(update, context, uid, edit=False):
    coins = get_coins(uid)
    kb = [
        [InlineKeyboardButton("📁 Browse Files", callback_data="menu_browse"),
         InlineKeyboardButton(f"💰 Coins: {coins}", callback_data="menu_coins")],
        [InlineKeyboardButton("🎁 Refer & Earn", callback_data="menu_refer"),
         InlineKeyboardButton("📤 Upload File", callback_data="menu_upload")],
    ]
    if is_owner(uid):
        kb.append([InlineKeyboardButton("👥 Admins", callback_data="menu_admins"),
                   InlineKeyboardButton("💸 Give Coins", callback_data="menu_givecoins")])
        kb.append([InlineKeyboardButton("🛠 Set Price", callback_data="menu_setprice")])
    text = f"🏠 *MAIN MENU*\n\n💰 Your coins: *{coins}*"
    markup = InlineKeyboardMarkup(kb)
    if edit and update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=markup)
            return
        except Exception:
            pass
    if update.message:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text(text, parse_mode='Markdown', reply_markup=markup)

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    data = q.data
    try:
        await q.answer()
    except Exception:
        pass

    if data == "check_join":
        missing = await check_join(context.bot, uid)
        if missing:
            await q.edit_message_text("❌ *Not joined all channels yet.*",
                parse_mode='Markdown', reply_markup=join_keyboard(missing))
            return
        await q.edit_message_text("✅ *Verified!*", parse_mode='Markdown')
        await show_main_menu(update, context, uid)
        return

    if data == "menu_main":
        await show_main_menu(update, context, uid, edit=True)
        return

    if data == "menu_coins":
        txt = f"💰 *Your Balance*\n\n*{get_coins(uid)} coins*\n⭐ Points: *{get_points(uid)}*"
        await q.edit_message_text(txt, parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu_main")]]))
        return

    if data == "menu_refer":
        bot_username = (await context.bot.get_me()).username
        link = f"https://t.me/{bot_username}?start=ref_{uid}"
        pts = get_points(uid)
        refs = count_referrals(uid)
        txt = (f"🎁 *Refer & Earn*\n\n🔗 Your link:\n`{link}`\n\n"
               f"👥 Referred: *{refs}*\n⭐ Points: *{pts}*\n\n"
               f"• New user: +{COIN_PER_REFERRAL} coins\n"
               f"• You: +{POINT_PER_REFERRAL} points per referral\n"
               f"• Every {BONUS_AT_POINTS} points → +{BONUS_COINS} coins")
        await q.edit_message_text(txt, parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu_main")]]))
        return

    if data == "menu_browse":
        files = list_files()
        if not files:
            await q.edit_message_text("📁 *File Store*\n\n_No files._", parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu_main")]]))
            return
        kb = []
        for fid, name, price in files:
            own = has_purchased(uid, fid)
            kb.append([InlineKeyboardButton(
                f"{'✅' if own else '📄'} {name} — {price}c", callback_data=f"file_{fid}")])
        kb.append([InlineKeyboardButton("🔙 Back", callback_data="menu_main")])
        await q.edit_message_text("📁 *File Store*\n\nTap a file:", parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(kb))
        return

    if data.startswith("file_"):
        fid = int(data.split("_", 1)[1])
        row = get_file(fid)
        if not row:
            await q.answer("Not found.", show_alert=True); return
        _, name, path, price, up, at = row
        own = has_purchased(uid, fid)
        coins = get_coins(uid)
        txt = f"📄 *{name}*\n\n💵 Price: *{price} coins*\n💰 You have: *{coins}*"
        kb = []
        if own:
            kb.append([InlineKeyboardButton("⬇️ Download", callback_data=f"dl_{fid}")])
        elif coins >= price:
            kb.append([InlineKeyboardButton(f"🛒 Buy for {price}", callback_data=f"buy_{fid}")])
        else:
            txt += "\n\n❌ _Not enough coins._"
        kb.append([InlineKeyboardButton("🔙 Back", callback_data="menu_browse")])
        await q.edit_message_text(txt, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(kb))
        return

    if data.startswith("buy_"):
        fid = int(data.split("_", 1)[1])
        row = get_file(fid)
        if not row:
            await q.answer("Not found.", show_alert=True); return
        _, name, path, price, up, at = row
        if has_purchased(uid, fid):
            await q.answer("Already bought.", show_alert=True); return
        if get_coins(uid) < price:
            await q.answer("Not enough coins.", show_alert=True); return
        add_coins(uid, -price)
        add_purchase(uid, fid, price)
        await q.answer("✅ Purchased!", show_alert=True)
        try:
            with open(path, "rb") as f:
                await context.bot.send_document(chat_id=q.message.chat_id,
                    document=InputFile(f, filename=name), caption=f"✅ {name}")
        except Exception as e:
            await context.bot.send_message(q.message.chat_id, f"⚠️ File missing: {e}")
        return

    if data.startswith("dl_"):
        fid = int(data.split("_", 1)[1])
        if not has_purchased(uid, fid):
            await q.answer("Not purchased.", show_alert=True); return
        row = get_file(fid)
        if not row or not os.path.exists(row[2]):
            await q.answer("File missing.", show_alert=True); return
        try:
            with open(row[2], "rb") as f:
                await context.bot.send_document(chat_id=q.message.chat_id,
                    document=InputFile(f, filename=row[1]), caption=f"✅ {row[1]}")
        except Exception as e:
            await q.answer(f"Error: {e}", show_alert=True)
        return

    if data == "menu_upload":
        if not is_admin(uid):
            await q.answer("Unauthorized.", show_alert=True); return
        user_state[uid] = {"step": "upload_name"}
        await q.edit_message_text("📤 *Upload — Step 1/3*\n\nSend the *file name*.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu_main")]]))
        return

    if data == "upload_cancel":
        st = user_state.pop(uid, None)
        if st and st.get("file_path") and os.path.exists(st["file_path"]):
            try: os.remove(st["file_path"])
            except Exception: pass
        await q.edit_message_text("❌ Cancelled.")
        return

    if data == "upload_confirm":
        st = user_state.get(uid)
        if not st or st.get("step") != "upload_confirm":
            await q.answer("Nothing to save.", show_alert=True); return
        fid = add_file(st["name"], st["file_path"], st["price"], uid)
        user_state.pop(uid, None)
        await q.edit_message_text(
            f"✅ *Saved!*\n\n🆔 `{fid}`\n📄 `{st['name']}`\n💵 *{st['price']} coins*",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu_main")]]))
        return

    if data == "menu_admins":
        if not is_owner(uid):
            await q.answer("Owner only.", show_alert=True); return
        rows = list_admins()
        txt = "👥 *Admins*\n\n" + ("\n".join(f"• `{u}` — {n or 'n/a'}" for u, n in rows) if rows else "_None._")
        await q.edit_message_text(txt, parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Add Admin", callback_data="adm_add")],
                [InlineKeyboardButton("🔙 Back", callback_data="menu_main")]]))
        return

    if data == "adm_add":
        if not is_owner(uid):
            await q.answer("Owner only.", show_alert=True); return
        user_state[uid] = {"step": "adm_add_id"}
        await q.edit_message_text("👥 *Add Admin*\n\nSend the user ID.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu_main")]]))
        return

    if data == "menu_givecoins":
        if not is_owner(uid):
            await q.answer("Owner only.", show_alert=True); return
        user_state[uid] = {"step": "givecoins_user"}
        await q.edit_message_text("💸 *Give Coins*\n\nSend the target user ID.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu_main")]]))
        return

    if data == "menu_setprice":
        if not is_owner(uid):
            await q.answer("Owner only.", show_alert=True); return
        user_state[uid] = {"step": "setprice_file"}
        await q.edit_message_text("🛠 *Set Price*\n\nSend the file ID.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu_main")]]))
        return

    await q.answer()

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.strip()
    st = user_state.get(uid)
    if not st: return
    step = st.get("step")

    if step == "upload_name":
        st["name"] = text
        st["step"] = "upload_file"
        await update.message.reply_text("📤 *Step 2/3*\n\nSend the *file*.",
            parse_mode='Markdown')
        return

    if step == "upload_price":
        try:
            price = int(text)
            if price < 0: raise ValueError
        except ValueError:
            await update.message.reply_text("❌ Send a valid number."); return
        st["price"] = price
        st["step"] = "upload_confirm"
        await update.message.reply_text(
            f"📤 *Step 3/3*\n\n📄 `{st['name']}`\n💵 *{price} coins*\n\nSave?",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Confirm", callback_data="upload_confirm"),
                 InlineKeyboardButton("❌ Cancel", callback_data="upload_cancel")]]))
        return

    if step == "adm_add_id":
        try: tid = int(text)
        except ValueError:
            await update.message.reply_text("❌ Invalid ID."); return
        try:
            chat = await context.bot.get_chat(tid)
            uname = chat.username
        except Exception:
            uname = None
        add_admin(tid, uname, uid)
        user_state.pop(uid, None)
        await update.message.reply_text(f"✅ Admin added: `{tid}`", parse_mode='Markdown')
        return

    if step == "givecoins_user":
        try: tid = int(text)
        except ValueError:
            await update.message.reply_text("❌ Invalid ID."); return
        st["target"] = tid
        st["step"] = "givecoins_amount"
        await update.message.reply_text("Send amount.")
        return

    if step == "givecoins_amount":
        try: amt = int(text)
        except ValueError:
            await update.message.reply_text("❌ Invalid number."); return
        add_coins(st["target"], amt)
        user_state.pop(uid, None)
        await update.message.reply_text(f"✅ +{amt} coins to `{st['target']}`.", parse_mode='Markdown')
        return

    if step == "setprice_file":
        try: fid = int(text)
        except ValueError:
            await update.message.reply_text("❌ Invalid ID."); return
        st["fid"] = fid
        st["step"] = "setprice_value"
        await update.message.reply_text("Send new price.")
        return

    if step == "setprice_value":
        try: p = int(text)
        except ValueError:
            await update.message.reply_text("❌ Invalid number."); return
        ok = set_file_price(st["fid"], p)
        user_state.pop(uid, None)
        if ok:
            await update.message.reply_text(f"✅ Price set to {p}.")
        else:
            await update.message.reply_text(f"❌ File ID {st['fid']} not found.")

async def file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    st = user_state.get(uid)
    if not st or st.get("step") != "upload_file": return

    msg = update.message
    os.makedirs(FILES_DIR, exist_ok=True)
    file_obj = None; suggested = None
    if msg.document:
        file_obj = await msg.document.get_file(); suggested = msg.document.file_name
    elif msg.video:
        file_obj = await msg.video.get_file(); suggested = msg.video.file_name or f"video_{msg.message_id}.mp4"
    elif msg.photo:
        file_obj = await msg.photo[-1].get_file(); suggested = f"photo_{msg.message_id}.jpg"
    elif msg.audio:
        file_obj = await msg.audio.get_file(); suggested = msg.audio.file_name or f"audio_{msg.message_id}.mp3"
    else:
        await msg.reply_text("❌ Send a document, video, photo, or audio."); return

    safe = st["name"].replace("/", "_").replace("\\", "_")
    ext = os.path.splitext(suggested)[1] if suggested else ""
    save_name = f"{safe}{ext}"
    save_path = os.path.join(FILES_DIR, save_name)
    try:
        await file_obj.download_to_drive(save_path)
    except Exception as e:
        await msg.reply_text(f"❌ Download failed: {e}"); return
    st["file_path"] = save_path
    st["step"] = "upload_price"
    await msg.reply_text(f"✅ File received: `{save_name}`\n\n💰 *Send the price in coins.*",
        parse_mode='Markdown')

async def owner_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    await update.message.reply_text(
        f"🆔 `{uid}`\n💰 Coins: *{get_coins(uid)}*\n⭐ Points: *{get_points(uid)}*",
        parse_mode='Markdown')

# ================= RUN =================
def build_app():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("me", owner_me))
    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(MessageHandler(
        filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO,
        file_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    return app

def run_loop():
    attempt = 0
    while True:
        attempt += 1
        try:
            print(f"🚀 Attempt {attempt} at {datetime.now()}")
            app = build_app()
            app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
            print("🛑 Stopped cleanly.")
            break
        except KeyboardInterrupt:
            print("👋 Ctrl+C. Exiting.")
            break
        except Exception as e:
            wait = min(attempt * 5, 60)
            print(f"⚠️ Crashed: {e}\n⏳ Restart in {wait}s...")
            time.sleep(wait)

if __name__ == "__main__":
    init_db()
    os.makedirs(FILES_DIR, exist_ok=True)
    os.makedirs("data", exist_ok=True)
    print("=" * 50)
    print(f"Owner: {OWNER_ID}")
    print(f"Files: {FILES_DIR}")
    print("=" * 50)
    run_loop()
