#!/usr/bin/env python3
"""
NIK Report Bot — multi-user premium telegram report automation
run: python3 app.py
"""

import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path

try:
    from telethon import TelegramClient, events, functions, types, Button
    from telethon.errors import SessionPasswordNeededError, FloodWaitError
except ImportError:
    print("[!] telethon missing. run: pip install telethon")
    sys.exit(1)

# ─────────────────────────── CONFIG ───────────────────────────
API_ID = 33576198
API_HASH = "7b59cd4d6fed5c8aa9c794f204e25050"
BOT_TOKEN = "8594487296:AAFBDQq04O0vH01ByUH7okGNTE3NoTbYZV8"
ADMIN_USERNAME = "deathalive07"

REPORT_REASON = "spam"
REPORT_MESSAGE = "This account is engaged in spam and scam activity."
COOLDOWN_SECONDS = 30

# ─────────────────────────── PATHS ────────────────────────────
BASE = Path(__file__).parent
SESSION_DIR = BASE / "sessions"
SESSION_DIR.mkdir(exist_ok=True)
ACCOUNTS_FILE = BASE / "accounts.txt"
STATS_FILE = BASE / "stats.json"
USERS_FILE = BASE / "users.json"
BOT_SESSION = str(BASE / "bot_session")

# stricter: must start with a letter, 5-32 chars
USERNAME_RE = re.compile(r"^@?([a-zA-Z][a-zA-Z0-9_]{4,31})$")


# ─────────────────────── JSON PERSISTENCE ─────────────────────
def _load(path, default):
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return default
    return default


def _save(path, data):
    try:
        path.write_text(json.dumps(data, indent=2))
    except Exception as e:
        print(f"[!] save failed {path}: {e}")


def load_users():
    return _load(USERS_FILE, {})


def save_users(u):
    _save(USERS_FILE, u)


def load_stats():
    return _load(STATS_FILE, {})


def save_stats(s):
    _save(STATS_FILE, s)


# ─────────────────────────── HELPERS ──────────────────────────
def list_sessions():
    try:
        return sorted([f for f in os.listdir(SESSION_DIR) if f.endswith(".session")])
    except Exception:
        return []


def append_account(phone: str):
    if not ACCOUNTS_FILE.exists():
        ACCOUNTS_FILE.write_text("")
    existing = [l.strip() for l in ACCOUNTS_FILE.read_text().splitlines() if l.strip()]
    if phone in existing:
        return False
    with ACCOUNTS_FILE.open("a") as f:
        f.write(phone + "\n")
    return True


def remove_account(phone: str):
    sess = SESSION_DIR / (phone.replace("+", "") + ".session")
    removed = False
    if sess.exists():
        try:
            sess.unlink()
            removed = True
        except Exception:
            pass
    if ACCOUNTS_FILE.exists():
        lines = [l for l in ACCOUNTS_FILE.read_text().splitlines() if l.strip() != phone]
        ACCOUNTS_FILE.write_text("\n".join(lines) + ("\n" if lines else ""))
    return removed


def is_premium(rec):
    if not rec:
        return False
    return rec.get("premium_until", 0) > time.time()


def premium_days_left(rec):
    if not rec:
        return 0
    until = rec.get("premium_until", 0)
    if until <= time.time():
        return 0
    return int((until - time.time()) // 86400)


def register_user(uid, username=None):
    users = load_users()
    key = str(uid)
    if key not in users:
        users[key] = {
            "username": username or "",
            "premium_until": 0,
            "first_seen": int(time.time()),
            "reports_sent": 0,
            "linked_sessions": [],
        }
        save_users(users)
    elif username and users[key].get("username") != username:
        users[key]["username"] = username
        save_users(users)
    return users[key]


# ─────────────────────── REASON RESOLVER ──────────────────────
def get_reason(name: str):
    key = name.strip().lower()
    suffix_map = {
        "spam": "Spam", "violence": "Violence", "drugs": "IllegalDrugs",
        "illegal": "IllegalDrugs", "personal": "PersonalDetails",
        "copyright": "Copyright", "other": "Other", "fake": "Fake",
        "porn": "Pornography", "child": "ChildAbuse",
    }
    suffix = suffix_map.get(key, "Spam")
    for c in (f"InputReportReason{suffix}", f"ReportReason{suffix}"):
        cls = getattr(types, c, None)
        if cls is not None:
            try:
                return cls()
            except Exception:
                continue
    try:
        from telethon.tl.types import InputReportReasonSpam
        return InputReportReasonSpam()
    except Exception:
        return None


# ─────────────────────────── REPORTER ─────────────────────────
async def report_from_session(session_path, target_ref, reason_obj, message):
    client = TelegramClient(session_path, API_ID, API_HASH)
    result = {"session": os.path.basename(session_path), "ok": False, "error": None}
    try:
        await client.connect()
        if not await client.is_user_authorized():
            result["error"] = "not_authorized"
            return result
        try:
            target = await client.get_entity(target_ref)
        except Exception as e:
            result["error"] = f"resolve_fail: {e}"
            return result
        peer = await client.get_input_entity(target)
        await client(functions.messages.ReportRequest(
            peer=peer, reason=reason_obj, message=message,
        ))
        result["ok"] = True
    except FloodWaitError as e:
        result["error"] = f"flood_wait: {e.seconds}s"
    except Exception as e:
        result["error"] = str(e)[:150]
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass
    return result


async def run_report(target_ref: str, progress_cb=None):
    sessions = list_sessions()
    if not sessions:
        return {"error": "no_sessions_linked", "total": 0, "ok": 0, "fail": 0, "results": []}

    reason_obj = get_reason(REPORT_REASON)
    if reason_obj is None:
        return {"error": "reason_unresolved", "total": 0, "ok": 0, "fail": 0, "results": []}

    clean = target_ref.strip()
    clean = clean.replace("https://t.me/", "").replace("http://t.me/", "")
    clean = clean.lstrip("@").split("/")[0]
    target_key = clean

    results = []
    ok_count = 0

    for i, sess in enumerate(sessions, 1):
        path = str(SESSION_DIR / sess)
        try:
            r = await report_from_session(path, clean, reason_obj, REPORT_MESSAGE)
        except Exception as e:
            r = {"session": sess, "ok": False, "error": f"crash: {e}"}
        results.append(r)
        if r["ok"]:
            ok_count += 1
        if progress_cb:
            try:
                await progress_cb(i, len(sessions), ok_count)
            except Exception:
                pass
        if i < len(sessions):
            await asyncio.sleep(COOLDOWN_SECONDS)

    summary = {
        "target": target_key, "total": len(sessions),
        "ok": ok_count, "fail": len(sessions) - ok_count, "results": results,
    }
    stats = load_stats()
    stats.setdefault(target_key, {"ok": 0, "fail": 0, "runs": 0})
    stats[target_key]["ok"] += ok_count
    stats[target_key]["fail"] += summary["fail"]
    stats[target_key]["runs"] += 1
    save_stats(stats)
    return summary


# ─────────────────────────── BOT ──────────────────────────────
bot = TelegramClient(BOT_SESSION, API_ID, API_HASH)
ADMIN_ID = None

PENDING_CONNECT = {}
PENDING_REPORT = {}
PENDING_ADD = {}
PENDING_REMOVE = {}
PENDING_PREMIUM_GRANT = {}
PENDING_PREMIUM_REVOKE = {}


def is_admin(event):
    return ADMIN_ID is not None and event.sender_id == ADMIN_ID


# ─────────────────────── KEYBOARDS ────────────────────────────
def user_menu(admin=False):
    rows = [
        [Button.inline("🚨 report user", b"u:report"), Button.inline("📡 report channel", b"u:report_ch")],
        [Button.inline("💎 my premium", b"u:premium"), Button.inline("❓ help", b"u:help")],
    ]
    if admin:
        rows.append([Button.inline("⚙️ admin panel", b"a:home")])
    return rows


def admin_menu():
    return [
        [Button.inline("📊 stats", b"a:stats"), Button.inline("👥 accounts", b"a:accounts")],
        [Button.inline("🔗 connect accounts", b"a:connect"), Button.inline("➕ add account", b"a:add")],
        [Button.inline("➖ remove account", b"a:remove"), Button.inline("💎 premium manager", b"a:premium")],
        [Button.inline("👤 users list", b"a:users"), Button.inline("🔑 reveal sessions", b"a:reveal")],
        [Button.inline("◀️ main menu", b"m:home")],
    ]


def premium_menu():
    return [
        [Button.inline("➕ grant premium", b"a:p_grant"), Button.inline("➖ revoke premium", b"a:p_revoke")],
        [Button.inline("📋 premium users", b"a:p_list"), Button.inline("◀️ back", b"a:home")],
    ]


def back_to(menu="a:home"):
    return [[Button.inline("◀️ back", menu.encode())]]


def user_back():
    return [[Button.inline("◀️ back", b"m:home")]]


# ─────────────────────── MENU RENDER ──────────────────────────
async def show_user_menu(event, edit=False):
    uid = event.sender_id
    rec = register_user(uid)
    tag = "💎 premium" if is_premium(rec) else "🆓 free"
    days = premium_days_left(rec)
    extra = f" · {days}d left" if days else ""
    text = (
        f"**NIK report bot**\n"
        f"status: {tag}{extra}\n\n"
        f"report a username or channel — tap below."
    )
    btns = user_menu(is_admin(event))
    if edit:
        try:
            await event.edit(text, buttons=btns, parse_mode="md")
            return
        except Exception:
            pass
    await event.reply(text, buttons=btns, parse_mode="md")


async def show_admin_menu(event, edit=True):
    if not is_admin(event):
        try:
            await event.answer("not authorized", alert=True)
        except Exception:
            pass
        return
    text = "**⚙️ admin panel** — full control"
    if edit:
        try:
            await event.edit(text, buttons=admin_menu(), parse_mode="md")
            return
        except Exception:
            pass
    await event.reply(text, buttons=admin_menu(), parse_mode="md")


# ─────────────────────── COMMAND HANDLERS ─────────────────────
@bot.on(events.NewMessage(pattern=r"^/start"))
async def cmd_start(e):
    register_user(e.sender_id)
    await show_user_menu(e)


@bot.on(events.NewMessage(pattern=r"^/(help|menu)"))
async def cmd_help(e):
    await show_user_menu(e)


@bot.on(events.NewMessage(pattern=r"^/admin"))
async def cmd_admin(e):
    if not is_admin(e):
        return
    await show_admin_menu(e, edit=False)


# ─────────────────────── CALLBACK ROUTER ──────────────────────
@bot.on(events.CallbackQuery())
async def on_button(event):
    uid = event.sender_id
    register_user(uid)
    data = event.data.decode() if isinstance(event.data, bytes) else str(event.data)

    try:
        # ── universal home
        if data == "m:home":
            await show_user_menu(event, edit=True)
            return

        # ── user help
        if data == "u:help":
            rec = register_user(uid)
            prem = is_premium(rec)
            body = (
                "**how to use**\n\n"
                "• 🚨 report user — report a `@username`\n"
                "• 📡 report channel — report a channel link / @username\n"
                "• 💎 my premium — check your status\n\n"
                + ("you have premium — reports enabled."
                   if prem else
                   "**no premium** — ask the admin to grant access.\n"
                   "reports are locked without premium.")
            )
            await event.edit(body, buttons=user_back(), parse_mode="md")
            return

        # ── user premium view
        if data == "u:premium":
            rec = register_user(uid)
            if is_premium(rec):
                d = premium_days_left(rec)
                body = f"💎 **premium active**\n\n`{d}` day(s) remaining."
            else:
                body = "🆓 **free tier**\n\nno premium. contact the admin to unlock reports."
            await event.edit(body, buttons=user_back(), parse_mode="md")
            return

        # ── report by username
        if data == "u:report":
            if not is_premium(register_user(uid)):
                await event.answer("premium required", alert=True)
                await event.edit(
                    "🚫 **premium required**\n\nask the admin to grant you premium.",
                    buttons=user_back(), parse_mode="md",
                )
                return
            PENDING_REPORT[uid] = {"stage": "await_username"}
            await event.edit(
                "🚨 **report user**\n\nsend the target `@username` now.",
                buttons=[[Button.inline("◀️ cancel", b"m:home")]], parse_mode="md",
            )
            return

        # ── report by channel
        if data == "u:report_ch":
            if not is_premium(register_user(uid)):
                await event.answer("premium required", alert=True)
                await event.edit(
                    "🚫 **premium required**\n\nask the admin to grant you premium.",
                    buttons=user_back(), parse_mode="md",
                )
                return
            PENDING_REPORT[uid] = {"stage": "await_channel"}
            await event.edit(
                "📡 **report channel**\n\nsend the channel `@name` or `https://t.me/name`.",
                buttons=[[Button.inline("◀️ cancel", b"m:home")]], parse_mode="md",
            )
            return

        # ── admin branch
        if not is_admin(event):
            await event.answer("not authorized", alert=True)
            return

        if data == "a:home":
            await show_admin_menu(event, edit=True)
            return

        if data == "a:stats":
            await event.edit(render_status(), buttons=back_to("a:home"), parse_mode="md")
            return

        if data == "a:accounts":
            sessions = list_sessions()
            if not sessions:
                body = "no reporting accounts linked yet."
            else:
                body = f"**{len(sessions)} reporting accounts:**\n" + \
                       "\n".join(f"• `{s[:-8]}`" for s in sessions)
            await event.edit(body, buttons=back_to("a:home"), parse_mode="md")
            return

        if data == "a:connect":
            await event.edit("🔗 starting connect wizard…", buttons=back_to("a:home"))
            await start_connect_wizard(event, edit_message=False)
            return

        if data == "a:add":
            PENDING_ADD[event.chat_id] = True
            await event.edit(
                "➕ **add account**\n\nsend the phone number as `+1234567890`.",
                buttons=back_to("a:home"), parse_mode="md",
            )
            return

        if data == "a:remove":
            PENDING_REMOVE[event.chat_id] = True
            await event.edit(
                "➖ **remove account**\n\nsend the phone as `+1234567890`.",
                buttons=back_to("a:home"), parse_mode="md",
            )
            return

        if data == "a:premium":
            await event.edit("💎 **premium manager**", buttons=premium_menu(), parse_mode="md")
            return

        if data == "a:p_grant":
            PENDING_PREMIUM_GRANT[event.chat_id] = {"stage": "await_id"}
            await event.edit(
                "➕ **grant premium**\n\nstep 1/2: send the target's **telegram numeric ID** or `@username`.",
                buttons=back_to("a:premium"), parse_mode="md",
            )
            return

        if data == "a:p_revoke":
            PENDING_PREMIUM_REVOKE[event.chat_id] = {"stage": "await_id"}
            await event.edit(
                "➖ **revoke premium**\n\nsend the target's **telegram numeric ID** or `@username`.",
                buttons=back_to("a:premium"), parse_mode="md",
            )
            return

        if data == "a:p_list":
            users = load_users()
            now = time.time()
            prem = [(k, v) for k, v in users.items() if v.get("premium_until", 0) > now]
            if not prem:
                body = "no premium users yet."
            else:
                lines = ["**💎 premium users**\n"]
                for k, v in prem:
                    days = int((v["premium_until"] - now) // 86400)
                    uname = v.get("username") or "—"
                    lines.append(f"• `{k}` (@{uname}) — `{days}d` left")
                body = "\n".join(lines)
            await event.edit(body, buttons=back_to("a:premium"), parse_mode="md")
            return

        if data == "a:users":
            users = load_users()
            now = time.time()
            if not users:
                body = "no users registered yet."
            else:
                lines = [f"**👤 users ({len(users)})**\n"]
                for k, v in list(users.items())[:80]:
                    tag = "💎" if v.get("premium_until", 0) > now else "🆓"
                    uname = v.get("username") or "—"
                    reps = v.get("reports_sent", 0)
                    lines.append(f"{tag} `{k}` (@{uname}) · reports: `{reps}`")
                body = "\n".join(lines)
            await event.edit(body, buttons=back_to("a:home"), parse_mode="md")
            return

        if data == "a:reveal":
            sessions = list_sessions()
            users = load_users()
            stats = load_stats()
            body = (
                f"**🔑 full reveal (admin only)**\n\n"
                f"**session dir:** `{SESSION_DIR}`\n"
                f"**accounts file:** `{ACCOUNTS_FILE}`\n"
                f"**users file:** `{USERS_FILE}`\n\n"
                f"**sessions on disk ({len(sessions)}):**\n"
                + ("\n".join(f"• `{s}`" for s in sessions) if sessions else "  none")
                + f"\n\n**registered users:** `{len(users)}`\n"
                f"**tracked targets:** `{len(stats)}`"
            )
            await event.edit(body, buttons=back_to("a:home"), parse_mode="md")
            return

        await event.answer()

    except Exception as ex:
        print(f"[!] callback error: {ex}")


# ─────────────────────── RENDER HELPERS ───────────────────────
def render_status():
    stats = load_stats()
    sessions = list_sessions()
    users = load_users()
    now = time.time()
    prem_count = sum(1 for v in users.values() if v.get("premium_until", 0) > now)
    head = (
        f"**📊 bot stats**\n\n"
        f"reporting accounts: `{len(sessions)}`\n"
        f"registered users: `{len(users)}`\n"
        f"premium users: `{prem_count}`\n"
        f"tracked targets: `{len(stats)}`\n"
    )
    if not stats:
        return head + "\nno reports fired yet."
    lines = [head, "\n**per-target:**"]
    for target, s in stats.items():
        lines.append(f"• @{target}: `{s['ok']} ok / {s['fail']} fail / {s['runs']} runs`")
    return "\n".join(lines)


# ─────────────────── CONNECT WIZARD (ADMIN ONLY) ──────────────
async def start_connect_wizard(event, edit_message=False):
    if not is_admin(event):
        return
    phones = []
    if ACCOUNTS_FILE.exists():
        phones = [l.strip() for l in ACCOUNTS_FILE.read_text().splitlines() if l.strip()]
    pending = [p for p in phones if not (SESSION_DIR / (p.replace("+", "") + ".session")).exists()]

    if not pending:
        text = "**all accounts already linked.**" if phones else "no accounts queued. add one first."
        btns = back_to("a:home")
        if edit_message:
            try:
                await event.edit(text, buttons=btns)
                return
            except Exception:
                pass
        await event.reply(text, buttons=btns)
        return

    chat_id = event.chat_id
    PENDING_CONNECT[chat_id] = {
        "queue": pending, "current": None, "stage": "start",
        "client": None, "phone_code_hash": None,
    }
    await _advance_connect(event, chat_id)


async def _advance_connect(event, chat_id):
    state = PENDING_CONNECT.get(chat_id)
    if not state:
        return
    if not state["queue"]:
        PENDING_CONNECT.pop(chat_id, None)
        await event.respond("✅ all pending accounts processed.", buttons=back_to("a:home"))
        return

    phone = state["queue"].pop(0)
    state["current"] = phone
    state["stage"] = "await_code"
    session_path = str(SESSION_DIR / phone.replace("+", ""))
    client = TelegramClient(session_path, API_ID, API_HASH)
    state["client"] = client

    try:
        await client.connect()
        if await client.is_user_authorized():
            me = await client.get_me()
            await client.disconnect()
            await event.respond(f"✅ `{phone}` already linked as `{me.username or me.id}`",
                                buttons=back_to("a:home"))
            await _advance_connect(event, chat_id)
            return
        sent = await client.send_code_request(phone)
        state["phone_code_hash"] = sent.phone_code_hash
        await event.respond(
            f"📲 code sent to `{phone}`.\n**send the code now — only you see it.**",
            buttons=back_to("a:home"),
        )
    except Exception as ex:
        state["stage"] = "error"
        await event.respond(f"❌ `{phone}` failed: `{ex}`", buttons=back_to("a:home"))
        try:
            await client.disconnect()
        except Exception:
            pass
        await _advance_connect(event, chat_id)


# ─────────────────────── MESSAGE WATCHER ──────────────────────
@bot.on(events.NewMessage())
async def watcher(event):
    if event.out:
        return
    text = (event.raw_text or "").strip()
    if not text or text.startswith("/"):
        return

    uid = event.sender_id
    chat_id = event.chat_id
    admin = is_admin(event)

    # ── admin: connect wizard code/password
    state = PENDING_CONNECT.get(chat_id) if admin else None
    if state:
        if state["stage"] == "await_code":
            client = state["client"]
            phone = state["current"]
            try:
                await client.sign_in(phone, text, phone_code_hash=state["phone_code_hash"])
                me = await client.get_me()
                await client.disconnect()
                await event.reply(f"✅ `{phone}` linked as `{me.username or me.id}`")
                await _advance_connect(event, chat_id)
                return
            except SessionPasswordNeededError:
                state["stage"] = "await_password"
                await event.reply(f"🔐 2fa for `{phone}` — send the password.")
                return
            except Exception as ex:
                await event.reply(f"❌ code rejected for `{phone}`: `{ex}`")
                try:
                    await client.disconnect()
                except Exception:
                    pass
                await _advance_connect(event, chat_id)
                return

        if state["stage"] == "await_password":
            client = state["client"]
            phone = state["current"]
            try:
                await client.sign_in(password=text)
                me = await client.get_me()
                await client.disconnect()
                await event.reply(f"✅ `{phone}` linked as `{me.username or me.id}`")
            except Exception as ex:
                await event.reply(f"❌ 2fa failed for `{phone}`: `{ex}`")
                try:
                    await client.disconnect()
                except Exception:
                    pass
            await _advance_connect(event, chat_id)
            return

    # ── admin: add phone
    if admin and chat_id in PENDING_ADD:
        PENDING_ADD.pop(chat_id, None)
        phone = text.strip()
        if not phone.startswith("+"):
            phone = "+" + phone
        added = append_account(phone)
        await event.reply(
            f"{'queued' if added else 'already queued'} `{phone}`. tap 🔗 connect accounts.",
            buttons=back_to("a:home"), parse_mode="md",
        )
        return

    # ── admin: remove phone
    if admin and chat_id in PENDING_REMOVE:
        PENDING_REMOVE.pop(chat_id, None)
        phone = text.strip()
        if not phone.startswith("+"):
            phone = "+" + phone
        removed = remove_account(phone)
        await event.reply(f"{'unlinked' if removed else 'not found'}: `{phone}`",
                          buttons=back_to("a:home"), parse_mode="md")
        return

    # ── admin: premium grant
    if admin and chat_id in PENDING_PREMIUM_GRANT:
        st = PENDING_PREMIUM_GRANT[chat_id]
        if st["stage"] == "await_id":
            st["target"] = text.strip()
            st["stage"] = "await_days"
            await event.reply(
                f"target: `{st['target']}`\n\n**step 2/2: how many days?** send a number.",
                buttons=back_to("a:premium"), parse_mode="md",
            )
            return
        if st["stage"] == "await_days":
            try:
                days = int(text.strip())
                if days <= 0:
                    raise ValueError
            except ValueError:
                await event.reply("send a positive integer number of days.")
                return
            PENDING_PREMIUM_GRANT.pop(chat_id, None)
            await _grant_premium(event, st["target"], days)
            return

    # ── admin: premium revoke
    if admin and chat_id in PENDING_PREMIUM_REVOKE:
        PENDING_PREMIUM_REVOKE.pop(chat_id, None)
        await _revoke_premium(event, text.strip())
        return

    # ── user: report flow
    rstate = PENDING_REPORT.get(uid)
    if rstate:
        stage = rstate.get("stage")
        if stage == "await_username":
            if not USERNAME_RE.match(text):
                await event.reply("that doesn't look like a valid username. try `@name`.")
                return
            PENDING_REPORT.pop(uid, None)
            await fire_report_flow(event, text.strip(), kind="username")
            return
        if stage == "await_channel":
            ref = text.strip()
            if not (USERNAME_RE.match(ref) or "t.me/" in ref):
                await event.reply("send a channel `@name` or `https://t.me/name`.")
                return
            PENDING_REPORT.pop(uid, None)
            await fire_report_flow(event, ref, kind="channel")
            return

    # ── bare @username shortcut — premium only, non-admin only
    if USERNAME_RE.match(text):
        if admin:
            return
        rec = register_user(uid)
        if not is_premium(rec):
            await event.reply("🚫 premium required. tap 💎 my premium.")
            return
        await fire_report_flow(event, text.strip(), kind="username")


# ─────────────────── PREMIUM GRANT/REVOKE ─────────────────────
async def _resolve_target_key(target: str):
    t = target.strip().lstrip("@")
    if t.isdigit():
        return t
    t = t.replace("https://t.me/", "").replace("http://t.me/", "").split("/")[0]
    try:
        ent = await bot.get_entity("@" + t)
        return str(ent.id)
    except Exception:
        return None


async def _grant_premium(event, target: str, days: int):
    key = await _resolve_target_key(target)
    if not key:
        await event.reply(f"❌ couldn't resolve `{target}`. use numeric id or a username the bot can see.")
        return
    users = load_users()
    rec = users.get(key, {
        "username": target.lstrip("@") if not target.lstrip("@").isdigit() else "",
        "premium_until": 0,
        "first_seen": int(time.time()),
        "reports_sent": 0,
        "linked_sessions": [],
    })
    now = time.time()
    base = rec["premium_until"] if rec["premium_until"] > now else now
    rec["premium_until"] = int(base + days * 86400)
    users[key] = rec
    save_users(users)
    await event.reply(
        f"✅ premium granted\n`{key}` for **{days} day(s)**\nexpires: "
        f"`{time.strftime('%Y-%m-%d %H:%M', time.localtime(rec['premium_until']))}`",
        buttons=back_to("a:premium"), parse_mode="md",
    )


async def _revoke_premium(event, target: str):
    key = await _resolve_target_key(target)
    if not key:
        await event.reply(f"❌ couldn't resolve `{target}`.")
        return
    users = load_users()
    if key not in users:
        await event.reply(f"`{key}` not registered.")
        return
    users[key]["premium_until"] = 0
    save_users(users)
    await event.reply(f"✅ premium revoked for `{key}`.",
                      buttons=back_to("a:premium"), parse_mode="md")


# ─────────────────── REPORT FLOW (ALL USERS) ──────────────────
async def fire_report_flow(event, target_ref, kind="username"):
    uid = event.sender_id
    sessions = list_sessions()
    label = "channel" if kind == "channel" else "user"
    msg = await event.reply(f"🚨 firing on **{label}** `{target_ref}` from `{len(sessions)}` accounts…")

    async def progress(done, total, ok):
        try:
            await msg.edit(f"🚨 `{target_ref}` — `{done}/{total}` done · `{ok}` ok")
        except Exception:
            pass

    summary = await run_report(target_ref, progress_cb=progress)

    if summary.get("error"):
        await msg.edit(f"[x] {summary['error']}")
        return

    users = load_users()
    key = str(uid)
    if key in users:
        users[key]["reports_sent"] = users[key].get("reports_sent", 0) + 1
        save_users(users)

    out = (
        f"✅ **report sent**\n\n"
        f"target: `{target_ref}`\n"
        f"`{summary['ok']}/{summary['total']}` ok · `{summary['fail']}` fail"
    )
    fails = [r for r in summary["results"] if not r["ok"]]
    if fails:
        out += "\n\n**failed sessions:**\n" + "\n".join(
            f"• `{r['session'][:-8]}`: {r['error'][:60]}" for r in fails[:10]
        )
    await msg.edit(out, buttons=user_back(), parse_mode="md")


# ─────────────────────────── MAIN ─────────────────────────────
async def main():
    global ADMIN_ID

    await bot.start(bot_token=BOT_TOKEN)

    try:
        entity = await bot.get_entity("@" + ADMIN_USERNAME)
        ADMIN_ID = entity.id
        print(f"[*] admin resolved: @{ADMIN_USERNAME} (id={ADMIN_ID})")
        register_user(ADMIN_ID, ADMIN_USERNAME)
    except Exception as e:
        print(f"[!] could not resolve admin @{ADMIN_USERNAME}: {e}")
        print("[!] admin id will be captured from the first dm by that username.")

        @bot.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
        async def _catch_admin(ev):
            global ADMIN_ID
            try:
                sender = await ev.get_sender()
                uname = getattr(sender, "username", None)
                if uname and uname.lower() == ADMIN_USERNAME.lower():
                    ADMIN_ID = sender.id
                    register_user(ADMIN_ID, ADMIN_USERNAME)
                    print(f"[*] admin captured: {ADMIN_ID}")
            except Exception:
                pass

    print("[*] bot online.")
    print(f"[*] linked reporting accounts: {len(list_sessions())}")
    print("[*] send /start to open your menu.")

    await bot.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[*] shut down.")
    except Exception as e:
        print(f"[!] fatal: {e}")
