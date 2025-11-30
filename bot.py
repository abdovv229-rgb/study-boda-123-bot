# ======= BEGIN BOT CODE =======
import os
import json
import time
from datetime import datetime

import requests
import telebot

# ================== الإعدادات الأساسية ==================

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN is not set")

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY is not set")

PAYMENT_NUMBER = "01080332776"
BOT_OWNER_USERNAME = "Abdo_Alpatreak"
OWNER_ID = 8095520384  # ID بتاعك اللي جبناه من /myid

DATA_FILE = "users.json"
CONV_FILE = "conversations.json"

FREE_LIMIT_Q = 30
BASIC_LIMIT_Q = 500
VIP_DAYS = 30

# ================== دوال المستخدمين ==================

def load_users():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def save_users(users):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

_users_cache = load_users()

# ================== دوال المحادثات ==================

def load_conversations():
    if not os.path.exists(CONV_FILE):
        return {}
    try:
        with open(CONV_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def save_conversations(convs):
    with open(CONV_FILE, "w", encoding="utf-8") as f:
        json.dump(convs, f, ensure_ascii=False, indent=2)

convs_cache = load_conversations()

SYSTEM_PROMPT = (
    "انت بوت اسمه روبوت دراسة بودا، تساعد الطلاب في المذاكرة، "
    "تجاوب بالعربي البسيط، ولو السؤال طبي/قانوني خطير تقول لازم متخصص."
)

# ================== الاتصال بـ OpenRouter ==================

def ask_ai(user_id: int, text: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"

    history = convs_cache.get(str(user_id), [])
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for item in history[-5:]:
        messages.append({"role": "user", "content": item["q"]})
        messages.append({"role": "assistant", "content": item["a"]})
    messages.append({"role": "user", "content": text})

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": "google/gemini-2.0-flash-lite-preview-02-05:free",
        "messages": messages,
    }

    resp = requests.post(url, headers=headers, json=data, timeout=60)
    resp.raise_for_status()
    js = resp.json()
    answer = js["choices"][0]["message"]["content"]

    user_key = str(user_id)
    convs_cache.setdefault(user_key, [])
    convs_cache[user_key].append({"q": text, "a": answer})
    save_conversations(convs_cache)

    return answer

# ================== إدارة المستخدمين ==================

def ensure_user(tg_user):
    """
    يسجّل المستخدم لو أول مرة، ويبعت لك رسالة إن في مستخدم جديد دخل.
    """
    global _users_cache
    uid = str(tg_user.id)
    users = _users_cache

    is_new = uid not in users

    if is_new:
        info = {
            "total_questions": 0,
            "free_used": 0,
            "basic_used": 0,
            "vip_used": 0,
            "tier": "free",
            "free_until": 0,
            "basic_until": 0,
            "vip_until": 0,
            "points": 0,
            "name": (tg_user.first_name or "").strip() or "بدون اسم",
            "username": tg_user.username or "",
            "lang": "ar",
            "joined": int(time.time()),
        }
        users[uid] = info
        save_users(users)

        # إشعار ليك إن في مستخدم جديد
        try:
            uname = f"@{tg_user.username}" if tg_user.username else "بدون يوزر"
            join_text = (
                "👤 *مستخدم جديد دخل البوت*\n\n"
                f"🧑‍💻 الاسم: {info['name']}\n"
                f"🆔 ID: `{uid}`\n"
                f"🔗 يوزر: {uname}\n"
            )
            bot.send_message(OWNER_ID, join_text)
        except Exception:
            pass
    else:
        info = users[uid]
        changed = False
        new_name = (tg_user.first_name or "").strip() or "بدون اسم"
        if info.get("name") != new_name:
            info["name"] = new_name
            changed = True
        new_username = tg_user.username or ""
        if info.get("username") != new_username:
            info["username"] = new_username
            changed = True
        if changed:
            save_users(users)

    _users_cache = users
    return users[uid]

def add_question_use(user_id):
    users = _users_cache
    uid = str(user_id)
    if uid not in users:
        return
    info = users[uid]
    info["total_questions"] = info.get("total_questions", 0) + 1
    if info.get("tier") == "vip":
        info["vip_used"] = info.get("vip_used", 0) + 1
    elif info.get("tier") == "basic":
        info["basic_used"] = info.get("basic_used", 0) + 1
    else:
        info["free_used"] = info.get("free_used", 0) + 1
    save_users(users)

# ================== إنشاء البوت ==================

bot = telebot.TeleBot(TELEGRAM_TOKEN, parse_mode="Markdown")

# ================== الأوامر ==================

@bot.message_handler(commands=["start"])
def cmd_start(message):
    user = ensure_user(message.from_user)
    text = (
        f"أهلاً {user['name']} 👋\n\n"
        "أنا *روبوت دراسة بودا* 🤖📚\n"
        "اسألني في المذاكرة وأنا أساعدك.\n\n"
        "للاشتراك في الخطط المدفوعة أو الاستفسار تواصل على:\n"
        f"`{PAYMENT_NUMBER}` أو @{BOT_OWNER_USERNAME}."
    )
    bot.reply_to(message, text)

@bot.message_handler(commands=["myid"])
def cmd_myid(message):
    uid = message.from_user.id
    bot.reply_to(
        message,
        f"🆔 الـ ID بتاعك:\n`{uid}`\n\nخليه معاك لو حابين نفعّل لك باقة 💳",
    )

@bot.message_handler(commands=["users"])
def cmd_users(message):
    # متاح للمالك فقط
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ هذا الأمر متاح لصاحب البوت فقط.")
        return

    users = load_users()
    if not users:
        bot.reply_to(message, "📭 لا يوجد مستخدمين حتى الآن.")
        return

    lines = []
    for uid, info in users.items():
        name = info.get("name") or "بدون اسم"
        username = info.get("username") or ""
        tier = info.get("tier") or "free"
        joined_ts = info.get("joined", 0)
        joined_str = (
            datetime.fromtimestamp(joined_ts).strftime("%Y-%m-%d")
            if joined_ts
            else "غير معروف"
        )

        if username:
            user_line = (
                f"👤 {name}\n"
                f"🆔 `{uid}`\n"
                f"💳 الخطة: *{tier}*\n"
                f"📅 تاريخ الدخول: {joined_str}\n"
                f"🔗 @{username}"
            )
        else:
            user_line = (
                f"👤 {name}\n"
                f"🆔 `{uid}`\n"
                f"💳 الخطة: *{tier}*\n"
                f"📅 تاريخ الدخول: {joined_str}"
            )

        lines.append(user_line)

    text = "📋 *قائمة المستخدمين:*\n\n" + "\n\n".join(lines)
    bot.reply_to(message, text)

# ================== هاندلر الرسائل العامة ==================

@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_text(message):
    user = ensure_user(message.from_user)

    try:
        add_question_use(message.from_user.id)
        answer = ask_ai(message.from_user.id, message.text)
    except Exception as e:
        print("ERROR in ask_ai:", e)
        bot.reply_to(
            message,
            "❌ حصل خطأ وأنا بجاوب.\nحاول تاني بعد شوية، ولو المشكلة كملت ابعت لصاحب البوت.",
        )
        return

    bot.reply_to(message, answer)

# ================== تشغيل البوت ==================

if __name__ == "__main__":
    print("Bot is running...")
    print(f"Owner (code): {BOT_OWNER_USERNAME}")
    bot.infinity_polling(timeout=60, skip_pending=True)
# ======= END BOT CODE =======
