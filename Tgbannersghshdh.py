#!/usr/bin/env python3
"""
NIK Report Bot — single-file telegram report automation
run: python3.13 app.py
"""

import asyncio
import json
import os
import re
import sys
from pathlib import Path

try:
    from telethon import TelegramClient, events, functions, types, Button
    from telethon.errors import (
        SessionPasswordNeededError,
        FloodWaitError,
        PhoneCodeExpiredError,
        PhoneCodeInvalidError,
    )
except ImportError:
    print("[!] telethon not installed. run: pip install telethon")
    sys.exit(1)

# ─────────────────────────── CONFIG ───────────────────────────
BOT_TOKEN = "8594487296:AAFBDQq04O0vH01ByUH7okGNTE3NoTbYZV8"
SUPER_ADMIN_USERNAME = "deathalive07"

# api pool — (api_id, api_hash, region_tag, label)
# region_tag: "in" | "ru" | "uk" | "mg" | ...  (short codes)
# any phone from any region can still link — region just controls retry order.
API_POOL = [
    (33576198, "7b59cd4d6fed5c8aa9c794f204e25050", "in", "in-hanuman"),
    (36603675, "178e45d560ea6d3d45ef83603165f25b", "in", "in-shiv"),
    (34540299, "edf6ec574eb38bd1d60facca6ea360e2", "in", "in-krishna"),
    (31222438, "d17172a533c51807a7fc4f91bf73a5f5", "in", "in-laxmi"),
    (37955502, "0826f6dcedf65ea1bf90743f1a577cc4", "ru", "ru-russia07"),
    (33312136, "528c3a422266cff9d8d7568896bdec3e", "ru", "ru-daddy07"),
    (22015656, "23f9446294df969c87a4921a63f2c7c3", "ru", "ru-superhero07"),
    (30787958, "d20dbf7672502bd1af9fa63080580a25", "ru", "ru-naruto07"),
]

# ─────────────────── REPORT REASONS + BODIES ──────────────────
# each reason = (telegram_reason_class_suffix, full_message_body)
REPORT_REASONS = {
    "spam": {
        "reason": "Spam",
        "message": (
            "This account is repeatedly sending unsolicited promotional content, "
            "scam links, and mass-forwarded spam across multiple chats. The user "
            "is running a coordinated spam operation targeting random users with "
            "phishing links and fake investment offers. Please review this account "
            "for violation of Telegram's Terms of Service regarding spam and "
            "unsolicited commercial messaging."
        ),
    },
    "violence": {
        "reason": "Violence",
        "message": (
            "This account is posting content that promotes violence, incites harm "
            "against individuals or groups, and distributes threatening material. "
            "The user has made credible threats and shares content glorifying "
            "violent acts. Requesting review under Telegram's policy against "
            "violence and incitement."
        ),
    },
    "drugs": {
        "reason": "IllegalDrugs",
        "message": (
            "This account is openly advertising and facilitating the sale of illegal "
            "narcotics and controlled substances. The user operates a channel that "
            "promotes drug distribution and provides contact details for purchases. "
            "Please review under Telegram's policy on illegal drug activity."
        ),
    },
    "personal": {
        "reason": "PersonalDetails",
        "message": (
            "This account is sharing personal identifying information without consent, "
            "including phone numbers, addresses, and private photos, in an attempt to "
            "harass and dox individuals. This is a clear violation of Telegram's "
            "policy on sharing private information."
        ),
    },
    "copyright": {
        "reason": "Copyright",
        "message": (
            "This account is distributing copyrighted content without authorization, "
            "including pirated media, software, and paywalled material. Requesting "
            "review under Telegram's copyright infringement policy."
        ),
    },
    "porn": {
        "reason": "Pornography",
        "message": (
            "This account is posting and distributing pornographic content in "
            "violation of Telegram's policy on adult content, including material "
            "shared without the consent of the individuals depicted."
        ),
    },
    "child": {
        "reason": "ChildAbuse",
        "message": (
            "This account is sharing content that endangers minors. Requesting "
            "immediate review under Telegram's child safety policy."
        ),
    },
    "fake": {
        "reason": "Fake",
        "message": (
            "This account is impersonating another individual or organization, "
            "using a fake identity to deceive users. Requesting review under "
            "Telegram's policy on impersonation and fake accounts."
        ),
    },
    "other": {
        "reason": "Other",
        "message": (
            "This account is engaged in activity that violates Telegram's Terms "
            "of Service. Please review the account and its associated chats."
        ),
    },
}

DEFAULT_REASON = "spam"
COOLDOWN_SECONDS = 30
REPLY_PER_ACCOUNT = True

# ─────────────────────────── PATHS ────────────────────────────
BASE = Path(__file__).parent
SESSION_DIR = BASE / "sessions"
SESSION_DIR.mkdir(exist_ok=True)
ACCOUNTS_FILE = BASE / "accounts.txt"
STATS_FILE = BASE / "stats.json"
SESSION_API_FILE = BASE / "session_api.json"
ADMINS_FILE = BASE / "admins.json"
BOT_SESSION = str(BASE / "bot_session")

TARGET_RE = re.compile(r"^@([a-zA-Z0-9_]{5,32})$")

# phone prefix → region code (for retry ordering — any country works either way)
PHONE_REGION = {
    "+7":   "ru",  # russia + kazakhstan
    "+91":  "in",  # india
    "+44":  "uk",  # uk
    "+261": "mg",  # madagascar
    "+1":   "us",
    "+234": "ng",
    "+92":  "pk",
    "+880": "bd",
    "+62":  "id",
    "+60":  "my",
    "+63":  "ph",
    "+84":  "vn",
    "+20":  "eg",
    "+212": "ma",
    "+27":  "za",
    "+55":  "br",
    "+52":  "mx",
    "+49":  "de",
    "+33":  "fr",
    "+39":  "it",
    "+34":  "es",
    "+81":  "jp",
    "+82":  "kr",
    "+86":  "cn",
    "+90":  "tr",
    "+98":  "ir",
    "+964": "iq",
    "+963": "sy",
}


# ─────────────────────── BOOT VALIDATION ──────────────────────
def _validate_pool():
    if not API_POOL:
        raise ValueError("API_POOL is empty")
    seen = set()
    for entry in API_POOL:
        if len(entry) != 4:
            raise ValueError(f"pool entry must be (id, hash, region, label): {entry!r}")
        api_id, api_hash, region, label = entry
        if not isinstance(api_id, int):
            raise ValueError(f"api_id must be int: {api_id!r}")
        if api_id in seen:
            raise ValueError(f"duplicate api_id: {api_id}")
        seen.add(api_id)
        if not isinstance(api_hash, str) or len(api_hash) != 32:
            raise ValueError(f"api_hash for {api_id} bad length: {api_hash!r}")
        if not all(c in "0123456789abcdef" for c in api_hash.lower()):
            raise ValueError(f"api_hash for {api_id} non-hex: {api_hash!r}")
        if not isinstance(region, str) or not region:
            raise ValueError(f"region missing for {api_id}")
        if not isinstance(label, str) or not label:
            raise ValueError(f"label missing for {api_id}")


_validate_pool()
print(f"[*] api pool validated: {len(API_POOL)} pair(s)")
print(f"[*] report reasons: {', '.join(REPORT_REASONS.keys())}")


# ─────────────────────── REASON RESOLVER ──────────────────────
def get_reason_obj(reason_key: str):
    """Resolve a report reason tl object across telethon versions."""
    spec = REPORT_REASONS.get(reason_key) or REPORT_REASONS[DEFAULT_REASON]
    suffix = spec["reason"]
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


def get_reason_message(reason_key: str) -> str:
    spec = REPORT_REASONS.get(reason_key) or REPORT_REASONS[DEFAULT_REASON]
    return spec["message"]


# ─────────────────────── ADMIN MANAGEMENT ─────────────────────
def load_admins():
    if ADMINS_FILE.exists():
        try:
            return json.loads(ADMINS_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_admins(data):
    ADMINS_FILE.write_text(json.dumps(data, indent=2))


def is_super(user_id: int) -> bool:
    entry = load_admins().get(str(user_id))
    return bool(entry and entry.get("super"))


def is_admin(user_id: int) -> bool:
    return str(user_id) in load_admins()


def is_premium(user_id: int) -> bool:
    entry = load_admins().get(str(user_id))
    return bool(entry and entry.get("premium"))


def add_admin(user_id: int, username: str, premium: bool = False, super_: bool = False):
    admins = load_admins()
    admins[str(user_id)] = {"username": username, "premium": premium, "super": super_}
    save_admins(admins)


def remove_admin(user_id: int):
    admins = load_admins()
    admins.pop(str(user_id), None)
    save_admins(admins)


# ─────────────────── REGION / PAIR PICKERS ───────────────────
def region_of_phone(phone: str) -> str:
    if not phone:
        return "unknown"
    matches = [p for p in PHONE_REGION if phone.startswith(p)]
    if not matches:
        return "unknown"
    return PHONE_REGION[max(matches, key=len)]


def ordered_pairs_for(phone: str, preferred: int = None):
    """preferred → region match → everything else. any country works."""
    want = region_of_phone(phone)
    pref = [p for p in API_POOL if p[0] == preferred]
    region = [p for p in API_POOL if p[2] == want and p[0] != preferred]
    rest = [p for p in API_POOL if p not in pref and p not in region]
    return pref + region + rest


# ─────────────────────────── HELPERS ──────────────────────────
def list_sessions():
    return sorted([f for f in os.listdir(SESSION_DIR) if f.endswith(".session")])


def load_stats():
    if STATS_FILE.exists():
        try:
            return json.loads(STATS_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_stats(stats):
    STATS_FILE.write_text(json.dumps(stats, indent=2))


def load_session_api():
    if SESSION_API_FILE.exists():
        try:
            return json.loads(SESSION_API_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_session_api(session_name: str, api_id: int, api_hash: str, region: str, label: str):
    data = load_session_api()
    data[session_name] = {"api_id": api_id, "api_hash": api_hash, "region": region, "label": label}
    SESSION_API_FILE.write_text(json.dumps(data, indent=2))


def get_session_api(session_name: str):
    entry = load_session_api().get(session_name)
    if not entry:
        return None
    return entry["api_id"], entry["api_hash"]


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
        sess.unlink(); removed = True
    if ACCOUNTS_FILE.exists():
        lines = [l for l in ACCOUNTS_FILE.read_text().splitlines() if l.strip() != phone]
        ACCOUNTS_FILE.write_text("\n".join(lines) + ("\n" if lines else ""))
    data = load_session_api()
    data.pop(phone.replace("+", "") + ".session", None)
    SESSION_API_FILE.write_text(json.dumps(data, indent=2))
    return removed


# ─────────────────────── SYNC INPUT BRIDGE ────────────────────
async def async_input(prompt: str) -> str:
    return await asyncio.get_event_loop().run_in_executor(None, lambda: input(prompt))


# ─────────────────── CONNECT (PAIR-PINNED) ────────────────────
_connect_lock = asyncio.Lock()


async def connect_one(phone: str, preferred_api: int = None, max_resends: int = 3) -> bool:
    session_path = str(SESSION_DIR / phone.replace("+", ""))
    session_name = os.path.basename(session_path) + ".session"
    session_file = Path(session_path + ".session")

    ordered = ordered_pairs_for(phone, preferred=preferred_api)
    print(f"\n[*] connecting {phone}")
    print(f"[*] region={region_of_phone(phone)} · preferred={preferred_api} · {len(ordered)} pair(s)")

    for attempt, (api_id, api_hash, region, label) in enumerate(ordered, 1):
        if session_file.exists():
            try: session_file.unlink()
            except Exception: pass

        print(f"[*] attempt {attempt}/{len(ordered)} — {label} (api_id={api_id})")
        client = TelegramClient(session_path, api_id, api_hash)

        try:
            await client.connect()

            if await client.is_user_authorized():
                me = await client.get_me()
                print(f"[+] {phone} already linked as {me.username or me.id}")
                await client.disconnect()
                save_session_api(session_name, api_id, api_hash, region, label)
                return True

            sent = await client.send_code_request(phone)
            print(f"[*] code sent via {sent.type.__class__.__name__}")

            resend_count = 0
            signed_in = False

            while not signed_in:
                print(f"[*] enter code, or type 'resend' to request another:")
                code = (await async_input(f"[?] code for {phone}: ")).strip().replace(" ", "")

                if code.lower() in ("resend", "again", "r", ""):
                    if resend_count >= max_resends:
                        print(f"[x] too many resends on {label}. next pair...")
                        break
                    resend_count += 1
                    print(f"[*] requesting fresh code ({resend_count}/{max_resends})...")
                    try:
                        sent = await client.send_code_request(phone)
                        print(f"[*] fresh code sent. paste it:")
                        continue
                    except FloodWaitError as e:
                        print(f"[x] flood wait {e.seconds}s on resend. next pair...")
                        break

                try:
                    await client.sign_in(phone, code, phone_code_hash=sent.phone_code_hash)
                    signed_in = True
                except SessionPasswordNeededError:
                    pw = (await async_input(f"[?] 2FA for {phone}: ")).strip()
                    await client.sign_in(password=pw)
                    signed_in = True
                except (PhoneCodeExpiredError, PhoneCodeInvalidError) as e:
                    if resend_count >= max_resends:
                        print(f"[x] {type(e).__name__} and resend limit hit. next pair...")
                        break
                    resend_count += 1
                    print(f"[x] {type(e).__name__}. sending fresh code ({resend_count}/{max_resends})...")
                    try:
                        sent = await client.send_code_request(phone)
                    except FloodWaitError as e2:
                        print(f"[x] flood {e2.seconds}s. next pair...")
                        break

            if signed_in:
                me = await client.get_me()
                print(f"[+] {phone} linked as {me.username or me.id} via {label}")
                await client.disconnect()
                save_session_api(session_name, api_id, api_hash, region, label)
                return True
            else:
                try: await client.disconnect()
                except Exception: pass
                continue

        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            print(f"[x] {label} failed: {err}")
            try: await client.disconnect()
            except Exception: pass
            low = err.lower()
            if any(k in low for k in ("api_id", "api_hash", "phone", "expired", "invalid", "flood", "auth")):
                continue
            return False

    print(f"[!] {phone} failed on all {len(ordered)} pair(s).")
    return False


async def connect_all_pending(api_override: int = None):
    async with _connect_lock:
        if not ACCOUNTS_FILE.exists():
            print("[*] no accounts.txt found.")
            return 0, 0
        phones = [l.strip() for l in ACCOUNTS_FILE.read_text().splitlines() if l.strip()]
        pending = [p for p in phones if not (SESSION_DIR / (p.replace("+", "") + ".session")).exists()]

        if not pending:
            print("[*] all accounts already linked.")
            return 0, 0

        print(f"\n[*] {len(pending)} pending. starting connect wizard.")
        print("[*] paste codes into THIS console. type 'resend' for a new code.\n")
        ok = 0
        for p in pending:
            if await connect_one(p, preferred_api=api_override):
                ok += 1
            print()
        return ok, len(pending)


# ─────────────────────────── REPORTER ─────────────────────────
async def report_from_session(session_path, target_username, reason_obj, message):
    session_name = os.path.basename(session_path)
    bound = get_session_api(session_name)
    if bound:
        api_id, api_hash = bound
    else:
        api_id, api_hash, _, _ = API_POOL[abs(hash(session_name)) % len(API_POOL)]

    client = TelegramClient(session_path, api_id, api_hash)
    result = {"session": session_name, "ok": False, "error": None}
    try:
        await client.connect()
        if not await client.is_user_authorized():
            result["error"] = "not_authorized"; return result
        try:
            target = await client.get_entity(target_username)
        except Exception as e:
            result["error"] = f"resolve_fail: {e}"; return result
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
        try: await client.disconnect()
        except Exception: pass
    return result


async def run_report(target_username: str, reason_key: str = None):
    reason_key = reason_key or DEFAULT_REASON
    sessions = list_sessions()
    if not sessions:
        return {"error": "no_sessions_linked", "total": 0, "ok": 0, "fail": 0, "results": []}

    reason_obj = get_reason_obj(reason_key)
    if reason_obj is None:
        return {"error": "could_not_resolve_report_reason", "total": 0, "ok": 0, "fail": 0, "results": []}

    message = get_reason_message(reason_key)
    target = target_username.lstrip("@")
    results, ok_count = [], 0

    for sess in sessions:
        path = str(SESSION_DIR / sess)
        try:
            r = await report_from_session(path, target, reason_obj, message)
        except Exception as e:
            r = {"session": sess, "ok": False, "error": f"crash: {e}"}
        results.append(r)
        if r["ok"]: ok_count += 1
        await asyncio.sleep(COOLDOWN_SECONDS)

    summary = {"target": target, "reason": reason_key, "total": len(sessions),
               "ok": ok_count, "fail": len(sessions) - ok_count, "results": results}

    stats = load_stats()
    stats.setdefault(target, {"ok": 0, "fail": 0, "runs": 0})
    stats[target]["ok"] += ok_count
    stats[target]["fail"] += summary["fail"]
    stats[target]["runs"] += 1
    save_stats(stats)
    return summary


# ─────────────────── INLINE PICKERS ──────────────────────────
def pair_buttons():
    rows, row = [], []
    for api_id, _, region, label in API_POOL:
        row.append(Button.inline(f"{label} ({region})", data=f"pair:{api_id}".encode()))
        if len(row) == 2:
            rows.append(row); row = []
    if row:
        rows.append(row)
    rows.append([Button.inline("cancel", data=b"pair:cancel")])
    return rows


def reason_buttons():
    rows, row = [], []
    for key in REPORT_REASONS.keys():
        row.append(Button.inline(key, data=f"reason:{key}".encode()))
        if len(row) == 3:
            rows.append(row); row = []
    if row:
        rows.append(row)
    rows.append([Button.inline("cancel", data=b"reason:cancel")])
    return rows


# ─────────────────────────── BOT ──────────────────────────────
BOT_API_ID, BOT_API_HASH, _, _ = API_POOL[0]
bot = TelegramClient(BOT_SESSION, BOT_API_ID, BOT_API_HASH)
SUPER_ID = None
_pending_connect = {}   # uid → {stage, phone}
_pending_report = {}    # uid → {"target": str}


def user_can_add(uid): return is_admin(uid)
def user_can_remove(uid): return is_admin(uid)
def user_can_report(uid): return is_admin(uid)


@bot.on(events.NewMessage(pattern=r"^/start"))
async def cmd_start(e):
    uid = e.sender_id
    if not is_admin(uid):
        await e.reply("you don't have access. ask the super admin to grant you.")
        return
    if is_super(uid):
        await e.reply(
            "**NIK report bot — super admin**\n\n"
            "/add +phone — queue account\n"
            "/connect — link accounts\n"
            "/remove +phone — unlink\n"
            "/list — linked accounts\n"
            "/status — report stats\n"
            "/admins — list admins\n"
            "/grant @user — basic admin\n"
            "/grantpremium @user — premium admin\n"
            "/revoke @user — remove admin\n\n"
            "send `@username` → pick reason → fire reports"
        )
    else:
        await e.reply(
            "**NIK report bot — admin**\n\n"
            "/add +phone — queue account\n"
            "/connect — link accounts\n"
            "/remove +phone — unlink\n"
            "/list — linked accounts\n\n"
            "send `@username` → pick reason → fire reports"
        )


@bot.on(events.NewMessage(pattern=r"^/help"))
async def cmd_help(e):
    uid = e.sender_id
    if not is_admin(uid): return
    if is_super(uid):
        await e.reply("/add · /connect · /remove · /list · /status · /admins · /grant · /grantpremium · /revoke")
    else:
        await e.reply("/add +phone · /connect · /remove · /list · send @username")


@bot.on(events.NewMessage(pattern=r"^/list"))
async def cmd_list(e):
    if not is_admin(e.sender_id): return
    sessions = list_sessions()
    if not sessions:
        await e.reply("no accounts linked yet."); return
    bound = load_session_api()
    lines = []
    for s in sessions:
        info = bound.get(s, {})
        lines.append(f"• {s[:-8]}  [{info.get('label','?')}/{info.get('region','?')}]")
    await e.reply(f"{len(sessions)} linked:\n" + "\n".join(lines))


@bot.on(events.NewMessage(pattern=r"^/status"))
async def cmd_status(e):
    if not is_admin(e.sender_id): return
    stats = load_stats()
    if not stats:
        await e.reply("no reports yet."); return
    lines = [f"@{t}: {s['ok']} ok / {s['fail']} fail / {s['runs']} runs" for t, s in stats.items()]
    await e.reply("\n".join(lines))


@bot.on(events.NewMessage(pattern=r"^/add\s+(\+?\d{7,15})\s*$"))
async def cmd_add(e):
    if not user_can_add(e.sender_id):
        await e.reply("no access."); return
    phone = e.pattern_match.group(1)
    if not phone.startswith("+"):
        phone = "+" + phone
    if append_account(phone):
        await e.reply(f"queued `{phone}` (region={region_of_phone(phone)}).\nsend `/connect` to link.")
    else:
        await e.reply(f"`{phone}` already queued.")


@bot.on(events.NewMessage(pattern=r"^/remove\s+(\+?\d{7,15})\s*$"))
async def cmd_remove(e):
    if not user_can_remove(e.sender_id):
        await e.reply("no access."); return
    phone = e.pattern_match.group(1)
    if not phone.startswith("+"):
        phone = "+" + phone
    removed = remove_account(phone)
    await e.reply(f"{'unlinked' if removed else 'not found'}: `{phone}`")


@bot.on(events.NewMessage(pattern=r"^/connect\s*$"))
async def cmd_connect(e):
    if not user_can_add(e.sender_id):
        await e.reply("no access."); return
    phones = []
    if ACCOUNTS_FILE.exists():
        phones = [l.strip() for l in ACCOUNTS_FILE.read_text().splitlines() if l.strip()]
    pending = [p for p in phones if not (SESSION_DIR / (p.replace("+", "") + ".session")).exists()]
    if not pending:
        await e.reply(f"nothing pending. {len(list_sessions())} linked."); return
    _pending_connect[e.sender_id] = {"stage": "pick_phone", "phones": pending}
    buttons = [[Button.inline(p, data=f"phone:{p}".encode())] for p in pending[:20]]
    buttons.append([Button.inline("cancel", data=b"phone:cancel")])
    await e.reply("pick which phone to link:", buttons=buttons)


@bot.on(events.CallbackQuery(pattern=rb"^phone:"))
async def cb_phone(event):
    uid = event.sender_id
    if uid not in _pending_connect or not user_can_add(uid):
        await event.answer("expired"); return
    data = event.data.decode().split(":", 1)[1]
    if data == "cancel":
        _pending_connect.pop(uid, None)
        await event.edit("cancelled."); return
    _pending_connect[uid] = {"stage": "pick_pair", "phone": data}
    await event.edit(f"linking `{data}` — pick api pair:", buttons=pair_buttons())


@bot.on(events.CallbackQuery(pattern=rb"^pair:"))
async def cb_pair(event):
    uid = event.sender_id
    if uid not in _pending_connect or not user_can_add(uid):
        await event.answer("expired"); return
    data = event.data.decode().split(":", 1)[1]
    if data == "cancel":
        _pending_connect.pop(uid, None)
        await event.edit("cancelled."); return
    api_id = int(data)
    phone = _pending_connect[uid]["phone"]
    _pending_connect.pop(uid, None)
    label = next((p[3] for p in API_POOL if p[0] == api_id), str(api_id))
    await event.edit(f"linking `{phone}` via {label}. **check console**. type 'resend' for new code.")
    ok = await connect_one(phone, preferred_api=api_id)
    if ok:
        await event.respond(f"✅ `{phone}` linked via {label}")
    else:
        await event.respond(f"❌ `{phone}` failed. try /connect again.")


# ─── report reason picker ───
@bot.on(events.CallbackQuery(pattern=rb"^reason:"))
async def cb_reason(event):
    uid = event.sender_id
    if uid not in _pending_report or not user_can_report(uid):
        await event.answer("expired"); return
    key = event.data.decode().split(":", 1)[1]
    if key == "cancel":
        _pending_report.pop(uid, None)
        await event.edit("cancelled."); return
    target = _pending_report.pop(uid)["target"]
    await event.edit(f"firing @{target} with reason **{key}** from {len(list_sessions())} accounts...")
    summary = await run_report(target, reason_key=key)
    if summary.get("error"):
        await event.edit(f"[x] {summary['error']}"); return
    out = f"@{target} · reason={key}\n{summary['ok']}/{summary['total']} ok · {summary['fail']} fail"
    if REPLY_PER_ACCOUNT:
        fails = [r for r in summary["results"] if not r["ok"]]
        if fails:
            out += "\n\nfails:\n" + "\n".join(
                f"• {r['session'][:-8]}: {r['error'][:60]}" for r in fails[:15]
            )
    await event.edit(out)


# ─── admin management ───
@bot.on(events.NewMessage(pattern=r"^/admins\s*$"))
async def cmd_admins(e):
    if not is_super(e.sender_id): return
    admins = load_admins()
    if not admins:
        await e.reply("no admins registered."); return
    lines = []
    for uid_str, info in admins.items():
        tier = "super" if info.get("super") else ("premium" if info.get("premium") else "basic")
        lines.append(f"• @{info.get('username','?')} · id={uid_str} · {tier}")
    await e.reply("\n".join(lines))


@bot.on(events.NewMessage(pattern=r"^/grant(?:premium)?\s+@?(\w+)\s*$"))
async def cmd_grant(e):
    if not is_super(e.sender_id): return
    is_prem = e.raw_text.lower().startswith("/grantpremium")
    username = e.pattern_match.group(1)
    try:
        entity = await bot.get_entity("@" + username)
    except Exception as ex:
        await e.reply(f"couldn't resolve @{username}: {ex}"); return
    add_admin(entity.id, username, premium=is_prem, super_=False)
    tier = "premium" if is_prem else "basic"
    await e.reply(f"granted {tier} admin: @{username} (id={entity.id})")


@bot.on(events.NewMessage(pattern=r"^/revoke\s+@?(\w+)\s*$"))
async def cmd_revoke(e):
    if not is_super(e.sender_id): return
    username = e.pattern_match.group(1)
    admins = load_admins()
    target_id = None
    for uid_str, info in admins.items():
        if info.get("username", "").lower() == username.lower():
            target_id = uid_str; break
    if not target_id:
        await e.reply(f"@{username} not found in admins."); return
    if target_id == str(SUPER_ID):
        await e.reply("can't revoke super admin."); return
    remove_admin(int(target_id))
    await e.reply(f"revoked: @{username}")


# ─── watcher: target → reason picker ───
@bot.on(events.NewMessage())
async def watcher(event):
    uid = event.sender_id
    text = (event.raw_text or "").strip()
    if not text or text.startswith("/") or text.startswith("+"):
        return
    if not user_can_report(uid):
        return
    m = TARGET_RE.match(text)
    if not m:
        return
    target = m.group(1)
    _pending_report[uid] = {"target": target}
    await event.reply(
        f"@{target} — pick a report reason:",
        buttons=reason_buttons()
    )


# ─────────────────────────── MAIN ─────────────────────────────
async def main():
    global SUPER_ID
    await bot.start(bot_token=BOT_TOKEN)

    try:
        entity = await bot.get_entity("@" + SUPER_ADMIN_USERNAME)
        SUPER_ID = entity.id
        print(f"[*] super admin: @{SUPER_ADMIN_USERNAME} (id={SUPER_ID})")
    except Exception as e:
        print(f"[!] could not resolve @{SUPER_ADMIN_USERNAME}: {e}")

    admins = load_admins()
    if SUPER_ID and str(SUPER_ID) not in admins:
        add_admin(SUPER_ID, SUPER_ADMIN_USERNAME, premium=False, super_=True)
        print(f"[*] super admin registered.")

    if SUPER_ID is None:
        @bot.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
        async def _catch(ev):
            global SUPER_ID
            sender = await ev.get_sender()
            uname = getattr(sender, "username", None)
            if uname and uname.lower() == SUPER_ADMIN_USERNAME.lower():
                SUPER_ID = sender.id
                add_admin(sender.id, uname, premium=False, super_=True)
                print(f"[*] super admin captured: {SUPER_ID}")

    print("[*] bot online.")
    print(f"[*] linked accounts: {len(list_sessions())}")
    print(f"[*] api pairs: {len(API_POOL)}")
    print(f"[*] report reasons: {', '.join(REPORT_REASONS.keys())}")

    await bot.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[*] shut down.")
