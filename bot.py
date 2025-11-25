import os
import json
from telebot import TeleBot, types
from telebot.apihelper import ApiTelegramException
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import threading
import time

UPDATE_INTERVAL = 5 * 60  # 5 минут

load_dotenv()

# ================== TELEGRAM BOT ==================
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN не задан!")

bot = TeleBot(TOKEN, threaded=False)

# ================== ADMINS & DATA ==================
ADMINS = [1324431208]
user_data = {}
try:
    DELIVERY_GROUP_ID = int(os.getenv("DELIVERY_GROUP_ID", "0"))
except ValueError:
    DELIVERY_GROUP_ID = 0

# ================== GOOGLE SHEETS ==================
GOOGLE_CREDS_PATH = "taj-express-478705-b4ad615749f9.json"
if not os.path.exists(GOOGLE_CREDS_PATH):
    raise RuntimeError(f"❌ Файл Google credentials не найден: {GOOGLE_CREDS_PATH}")

with open(GOOGLE_CREDS_PATH, "r") as f:
    creds_dict = json.load(f)

scope = ["https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gc = gspread.authorize(creds)

SHEET_NAME = "Tracks"
try:
    sheet = gc.open(SHEET_NAME).sheet1
except Exception as e:
    print("❌ Ошибка подключения к таблице:", e)
    sheet = None

# ================== MENU ==================
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
        "🚀 TAJEXPRESS – каргои боваринок ва бехатар барои овардани борхои Шумо!\n\n"
        "📦 Борҳои худро зуд ва бехатар фиристед\n"
        "⏱️ Дархостҳоро осон ва зуд иҷро намоед\n"
        "🇨🇳 Суроғаи қулай дар Чин барои харидҳои шумо\n\n"
        "Менюи зерро интихоб кунед:"
    )
    bot.send_message(chat_id, welcome_text)
    send_main_menu(chat_id)

# ================== КЭШ ==================
track_cache = {}  # {track_code: row_data}
user_cache = {}   # {chat_id: user_data}

def load_cache():
    global track_cache, user_cache
    if sheet:
        try:
            records = sheet.get_all_records()
            track_cache = {str(r["Track"]).upper(): r for r in records}
        except Exception as e:
            print(f"Ошибка загрузки треков в кэш: {e}")
    try:
        users_sheet = gc.open("Tracks").worksheet("Users")
        users_records = users_sheet.get_all_records()
        user_cache = {int(r["ChatID"]): r for r in users_records}
    except Exception as e:
        print(f"Ошибка загрузки пользователей в кэш: {e}")

load_cache()

def update_track_cache_periodically():
    global track_cache
    while True:
        try:
            if sheet:
                records = sheet.get_all_records()
                track_cache = {str(r["Track"]).upper(): r for r in records}
                print(f"[INFO] Кэш треков обновлен. Всего треков: {len(track_cache)}")
        except Exception as e:
            print(f"[ERROR] Не удалось обновить кэш треков: {e}")
        time.sleep(UPDATE_INTERVAL)

threading.Thread(target=update_track_cache_periodically, daemon=True).start()

# ================== MAIN HANDLER ==================
@bot.message_handler(func=lambda m: True)
def main_handler(message):
    chat_id = message.chat.id
    text = message.text

    if text == BTN_REGISTER:
        msg = bot.send_message(chat_id, "Введите ваше имя:")
        bot.register_next_step_handler(msg, register_step_name)

    elif text == BTN_DELIVERY:
        msg = bot.send_message(chat_id, "Номи худро ворид кунед:")
        bot.register_next_step_handler(msg, delivery_step_name)

    elif text == BTN_ADDRESS:
        msg = bot.send_message(chat_id, "Номи худро ворид кунед (Танҳо ҳарфҳои англисӣ):")
        bot.register_next_step_handler(msg, address_step_name)

    elif text == BTN_PRICE_LIST:
        bot.send_message(chat_id,
                         "📦 Нархнома:\n"
                         "• Аз 200кг то 1000кг — 1.8$\n"
                         "• Аз 0.1кг то 200кг — 3$")

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
    msg = bot.send_message(chat_id, "Введите ваш номер телефона:")
    bot.register_next_step_handler(msg, register_step_phone)

def register_step_phone(message):
    chat_id = message.chat.id
    user_data[chat_id]["phone"] = message.text
    threading.Thread(target=save_user, args=(chat_id,), daemon=True).start()
    bot.send_message(chat_id,
                     f"✅ Бақайдгирӣ анҷом ёфт!\nИмя: {user_data[chat_id]['name']}\nТел: {user_data[chat_id]['phone']}")
    send_main_menu(chat_id)

def save_user(chat_id):
    try:
        users_sheet = gc.open("Tracks").worksheet("Users")
    except gspread.WorksheetNotFound:
        users_sheet = gc.open("Tracks").add_worksheet(title="Users", rows="1000", cols="3")
        users_sheet.append_row(["ChatID", "Name", "Phone"])

    if chat_id in user_cache:
        row = user_cache[chat_id].get("row", None)
        if row:
            users_sheet.update(f"B{row}", user_data[chat_id]["name"])
            users_sheet.update(f"C{row}", user_data[chat_id]["phone"])
    else:
        users_sheet.append_row([chat_id, user_data[chat_id]["name"], user_data[chat_id]["phone"]])
    user_cache[chat_id] = {"Name": user_data[chat_id]["name"], "Phone": user_data[chat_id]["phone"]}

# ================== Доставка ==================
def delivery_step_name(message):
    chat_id = message.chat.id
    user_data[chat_id] = {"name": message.text}
    msg = bot.send_message(chat_id, "Суроғаро ворид кунед:")
    bot.register_next_step_handler(msg, delivery_step_address)

def delivery_step_address(message):
    chat_id = message.chat.id
    user_data[chat_id]["address"] = message.text
    msg = bot.send_message(chat_id, "Рақами телефони худро ворид кунед:")
    bot.register_next_step_handler(msg, delivery_step_phone)

def delivery_step_phone(message):
    chat_id = message.chat.id
    user_data[chat_id]["phone"] = message.text
    data = user_data[chat_id]
    delivery_text = f"📦 *НОВАЯ ЗАЯВКА НА ДОСТАВКУ*\nИмя: {data['name']}\nАдрес: {data['address']}\nТелефон: {data['phone']}"
    try:
        bot.send_message(DELIVERY_GROUP_ID, delivery_text, parse_mode="Markdown")
        bot.send_message(chat_id, "Дархост қабул шуд ✅")
    except ApiTelegramException as e:
        bot.send_message(chat_id, f"Хатогии ирсол: {e}")
    send_main_menu(chat_id)

# ================== Адрес ==================
def address_step_name(message):
    chat_id = message.chat.id
    if not message.text.isascii():
        msg = bot.send_message(chat_id, "❌ Танҳо бо ҳарфҳои англисӣ нависед!")
        bot.register_next_step_handler(msg, address_step_name)
        return
    user_data[chat_id] = {"name": message.text}
    msg = bot.send_message(chat_id, "Рақами телефони худро ворид кунед:")
    bot.register_next_step_handler(msg, address_step_phone)

def address_step_phone(message):
    chat_id = message.chat.id
    user_data[chat_id]["phone"] = message.text
    data = user_data[chat_id]
    full_address = f"{data['name']} 17590820846 浙江省 金华市 义乌市 福田三小区80栋二单元305室 {data['name']} {data['phone']}"
    bot.send_message(chat_id, full_address)
    send_main_menu(chat_id)

# ================== Трек-код ==================
def track_step(message):
    chat_id = message.chat.id
    code = message.text.strip().upper()
    info_text = "❌ Трек-код не найден"
    row = track_cache.get(code)
    if row:
        info_text = (
            f"🔢 Трек-код: {row.get('Track', '-')}\n"
            f"📦 Статус: {row.get('Status', '-')}\n"
            f"📅 Дата: {row.get('Date', '-')}\n"
            f"👤 Имя клиента: {row.get('Name', '-')}\n"
            f"📞 Номер: {row.get('ClientCode', '-')}\n"
            f"⚖ Вес: {row.get('Weight(kg)', '-')}\n"
            f"💰 Цена/кг: {row.get('Price/kg', '-')}\n"
            f"💵 Всего: {row.get('Total', '-')}"
        )
    bot.send_message(chat_id, info_text)
    send_main_menu(chat_id)

# ================== Контакты ==================
def show_contacts(chat_id):
    text = "📞 *Ракамхо мо*\n\n"
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("📱 +992 985 171 732", url="https://t.me/zubaidullo_tjk"))
    markup.add(types.InlineKeyboardButton("📱 +992 933 055 707", url="https://t.me/zubaidullo_tjk"))
    markup.add(types.InlineKeyboardButton("📱 +992 007 282 626", url="https://t.me/Fayoz_7707"))
    markup.add(types.InlineKeyboardButton("📢 Канал Telegram", url="https://t.me/TAJEXPRESSCARGO"))
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

# ===================== ЗАПУСК =====================
if __name__ == "__main__":
    print("Бот запущен в режиме polling...")
    bot.infinity_polling()
