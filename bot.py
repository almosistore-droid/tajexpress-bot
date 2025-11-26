import os
import json
import re
import time
import threading
from telebot import TeleBot, types
from telebot.apihelper import ApiTelegramException
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ================== НАСТРОЙКИ ==================
UPDATE_INTERVAL = 5 * 60  # обновление трек-кеша каждые 5 минут
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN не задан!")

bot = TeleBot(TOKEN, threaded=False)

ADMINS = [1324431208]
ADMIN_LOGIN = os.getenv("ADMIN_LOGIN", "Tajexpress")
ADMIN_PASS = os.getenv("ADMIN_PASS", "T@jexpre$$")
user_data = {}

DELIVERY_GROUP_ID = int(os.getenv("DELIVERY_GROUP_ID", "-1003338345257"))

# ================== GOOGLE SHEETS ==================
GOOGLE_CREDS_PATH = os.getenv("GOOGLE_CREDENTIALS_JSON", "/opt/render/secrets/credentials.json")
if not os.path.exists(GOOGLE_CREDS_PATH):
    raise RuntimeError(f"❌ Файл Google credentials не найден: {GOOGLE_CREDS_PATH}")

with open(GOOGLE_CREDS_PATH, "r") as f:
    creds_dict = json.load(f)

scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gc = gspread.authorize(creds)

SHEET_NAME = "Tracks"
try:
    sheet = gc.open(SHEET_NAME).sheet1
except Exception as e:
    print("❌ Ошибка подключения к таблице:", e)
    sheet = None

# ================== КЭШ ТРЕКОВ ==================
track_cache = {}  # {track_code: row_data}

def normalize_track(track):
    return re.sub(r"[^A-Z0-9]", "", str(track).upper())

def load_cache():
    global track_cache
    if not sheet:
        print("[ERROR] Лист Google Sheets не найден")
        return
    try:
        records = sheet.get_all_records()
        track_cache = {}
        for r in records:
            if "Track" in r and r["Track"]:
                key = normalize_track(r["Track"])
                track_cache[key] = r
        print(f"[INFO] Загружено треков: {len(track_cache)}")
    except Exception as e:
        print(f"[ERROR] Ошибка загрузки треков: {e}")

def update_cache_periodically():
    while True:
        load_cache()
        time.sleep(UPDATE_INTERVAL)

threading.Thread(target=update_cache_periodically, daemon=True).start()

# ================== МЕНЮ ==================
BTN_DELIVERY = "🚚 Доставка"
BTN_ADDRESS = "🇨🇳 Гирифтани адрес ва код"
BTN_DUSHANBE = "🇹🇯 Адрес Душанбе"
BTN_PRICE_LIST = "📦 Нархнома"
BTN_TRACK = "🔍 Проверка трек-кода"
BTN_BANNED = "🚫 Молхои манъшуда"
BTN_CONTACTS = "📞 Контакты"
BTN_REGISTER = "📝 Регистрация"

MAIN_MENU = [
    [BTN_REGISTER],
    [BTN_DELIVERY, BTN_ADDRESS],
    [BTN_TRACK, BTN_DUSHANBE],
    [BTN_PRICE_LIST, BTN_BANNED],
    [BTN_CONTACTS]
]

def send_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for row in MAIN_MENU:
        markup.add(*[types.KeyboardButton(text) for text in row])
    bot.send_message(chat_id, "Меню:", reply_markup=markup)

# ================== START ==================
@bot.message_handler(commands=["start", "help"])
def start_handler(message):
    chat_id = message.chat.id
    welcome_text = (
        "🚀 TAJEXPRESS – каргои боваринок ва бехатар!\n\n"
        "📦 Борҳои худро зуд фиристед\n"
        "⏱️ Дархостҳоро осон иҷро намоед\n"
        "🇨🇳 Суроғаи қулай дар Чин\n\n"
        "Менюи зерро интихоб кунед:"
    )
    bot.send_message(chat_id, welcome_text)
    send_main_menu(chat_id)

# ================== MAIN HANDLER ==================
@bot.message_handler(func=lambda m: True)
def main_handler(message):
    chat_id = message.chat.id
    text = message.text

    if text == BTN_REGISTER:
        msg = bot.send_message(chat_id, "Номи худро ворид кунед:")
        bot.register_next_step_handler(msg, register_step_name)
    elif text == BTN_DELIVERY:
        msg = bot.send_message(chat_id, "Номи худро ворид кунед:")
        bot.register_next_step_handler(msg, delivery_step_name)
    elif text == BTN_ADDRESS:
        msg = bot.send_message(chat_id, "Номи худро ворид кунед (Танҳо ҳарфҳои англисӣ):")
        bot.register_next_step_handler(msg, address_step_name)
    elif text == BTN_PRICE_LIST:
        bot.send_message(chat_id, "📦 Нархнома:\n• Аз 200кг то 1000кг — 1.8$\n• Аз 0.1кг то 200кг — 3$")
    elif text == BTN_TRACK:
        msg = bot.send_message(chat_id, "Треккоди худро равон кунед:")
        bot.register_next_step_handler(msg, track_step)
    elif text == BTN_DUSHANBE:
        bot.send_message(chat_id, "🇹🇯 Душанбе, 103 мкр \nТел: +992 985171732")
    elif text == BTN_BANNED:
                             bot.send_message(chat_id,
                         "⚠️ Маҳсулотҳои манъшуда:\n"
                         "🔥 1. Маводҳои тарканда\n"
                         "🔋 2. Батареяҳо, аккумуляторҳо, магнитҳо ва повербанкҳо\n"
                         "🥗 3. Хӯрокворӣ, тухмӣ ва шинонандаҳо\n"
                         "🔫 4. Ҳарбу зарфҳо (аз ҷумла бозичаҳо), кастет ва кордҳо\n"
                         "⛽ 5. Маводи сӯзишворӣ, равған ва косметика\n"
                         "💎 6. Нуқра, тилло ва маҳсулоти қиматбаҳо\n"
                         "💧 7. Моеъҳо, аэрозолҳо ва моддаҳои кимиёвӣ\n")
    elif text == BTN_CONTACTS:
        show_contacts(chat_id)
    else:
        send_main_menu(chat_id)

# ================== РЕГИСТРАЦИЯ ==================
def register_step_name(message):
    chat_id = message.chat.id
    user_data[chat_id] = {"name": message.text}
    msg = bot.send_message(chat_id, "Рақами телефони худро ворид кунед:")
    bot.register_next_step_handler(msg, register_step_phone)

def register_step_phone(message):
    chat_id = message.chat.id
    user_data[chat_id]["phone"] = message.text
    bot.send_message(chat_id, f"✅ Бақайдгирӣ анҷом ёфт!\nИмя: {user_data[chat_id]['name']}\nТел: {user_data[chat_id]['phone']}")
    send_main_menu(chat_id)

# ================== TRACK ==================
def track_step(message):
    chat_id = message.chat.id
    code = normalize_track(message.text)
    row = track_cache.get(code)
    if row:
        info_text = (
            f"🔢 Трек-код: {row.get('Track', '-')}\n"
            f"📦 Статус: {row.get('Status', '-')}\n"
            f"📅 Дата: {row.get('Date', '-')}\n"
            f"👤 Имя клиента: {row.get('Name', '-')}\n"
            f"📞 Код клиента: {row.get('ClientCode', '-')}\n"
            f"⚖ Вес: {row.get('Weight(kg)', '-')}\n"
            f"💰 Цена/кг: {row.get('Price/kg', '-')}\n"
            f"💵 Всего: {row.get('Total', '-')}"
        )
    else:
        info_text = "❌ Трек-код не найден. Проверьте номер и попробуйте ещё раз."
    bot.send_message(chat_id, info_text)
    send_main_menu(chat_id)

# ================== CONTACTS ==================
def show_contacts(chat_id):
    text = "📞 *Ракамхо мо*\n\n"
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("📱 +992 985 171 732", url="https://t.me/zubaidullo_tjk"))
    markup.add(types.InlineKeyboardButton("📱 +992 933 055 707", url="https://t.me/zubaidullo_tjk"))
    markup.add(types.InlineKeyboardButton("📱 +992 007 282 626", url="https://t.me/Fayoz_7707"))
    markup.add(types.InlineKeyboardButton("📢 Канал Telegram", url="https://t.me/TAJEXPRESSCARGO"))
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

# ================== ADMIN / ADD TRACK ==================
@bot.message_handler(commands=["addtrack"])
def add_track(message):
    chat_id = message.chat.id
    if chat_id not in ADMINS:
        bot.send_message(chat_id, "❌ Доступ только для админов")
        return
    msg = bot.send_message(chat_id, "Введите трек-код:")
    bot.register_next_step_handler(msg, add_track_step)

def add_track_step(message):
    chat_id = message.chat.id
    code = normalize_track(message.text)
    user_data[chat_id] = {"code": code}
    msg = bot.send_message(chat_id, "Введите статус:")
    bot.register_next_step_handler(msg, add_track_status)

def add_track_status(message):
    chat_id = message.chat.id
    status = message.text
    code = user_data[chat_id]["code"]
    track_cache[code] = {"Track": code, "Status": status}
    if sheet:
        try:
            sheet.append_row([code, status])
        except Exception as e:
            bot.send_message(chat_id, f"❌ Ошибка записи в таблицу: {e}")
    bot.send_message(chat_id, f"✅ Трек-код {code} добавлен/обновлен")
    send_main_menu(chat_id)

# ================== RUN ==================
if __name__ == "__main__":
    load_cache()
    print("Бот запущен...")
    bot.infinity_polling()
