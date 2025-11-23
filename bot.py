import os
import json
import telebot
from telebot import types
from telebot.apihelper import ApiTelegramException
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials

load_dotenv()

# ================== TELEGRAM BOT ==================
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN не определен!")

bot = telebot.TeleBot(TOKEN, threaded=False)

try:
    DELIVERY_GROUP_ID = int(os.getenv("DELIVERY_GROUP_ID", "0"))
except ValueError:
    DELIVERY_GROUP_ID = 0

# Хранилища данных
user_data = {}

# Админы
ADMINS = [1324431208]  # вставьте сюда id админа

# ================== GOOGLE SHEETS ==================
GOOGLE_CREDS_PATH = "taj-express-478705-b4ad615749f9.json"  # Используем файл ключа
if not os.path.exists(GOOGLE_CREDS_PATH):
    raise RuntimeError(f"❌ Файл Google credentials не найден: {GOOGLE_CREDS_PATH}")

try:
    with open(GOOGLE_CREDS_PATH, "r") as f:
        creds_dict = json.load(f)
except Exception as e:
    raise RuntimeError(f"❌ Ошибка загрузки Google JSON: {e}")

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
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

MAIN_MENU = [
    [BTN_DELIVERY, BTN_ADDRESS],
    [BTN_TRACK, BTN_DUSHANBE],
    [BTN_PRICE_LIST, BTN_BANNED],
    [BTN_CONTACTS]
]

def send_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for row in MAIN_MENU:
        markup.add(*[types.KeyboardButton(text) for text in row])
    bot.send_message(chat_id, "Выберите пункт меню:", reply_markup=markup)

# ================== START ==================
@bot.message_handler(commands=["start", "help"])
def start_handler(message):
    send_main_menu(message.chat.id)

# ================== MAIN HANDLER ==================
@bot.message_handler(func=lambda m: True)
def main_handler(message):
    chat_id = message.chat.id
    text = message.text

    if text == BTN_DELIVERY:
        msg = bot.send_message(chat_id, "Номи худро ворид кунед:")
        bot.register_next_step_handler(msg, delivery_step_name)

    elif text == BTN_ADDRESS:
        msg = bot.send_message(chat_id, "Номи худро ворид кунед (Танҳо ҳарфҳои англисӣ):")
        bot.register_next_step_handler(msg, address_step_name)

    elif text == BTN_PRICE_LIST:
        bot.send_message(chat_id,
            "📦 Нархнома:\n"
            "• Аз 200кг то 1000кг — 1.8$\n"
            "• Аз 0.1кг то 200кг — 3$"
        )

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
            "💧 7. Моеъҳо, аэрозолҳо ва моддаҳои кимиёвӣ\n"
        )

    elif text == BTN_CONTACTS:
        show_contacts(chat_id)

    else:
        send_main_menu(chat_id)

# ================== Доставка ==================
def delivery_step_name(message):
    chat_id = message.chat.id
    user_data[chat_id] = {"name": message.text}
    msg = bot.send_message(chat_id, "Суроғаро ворид кунед:")
    bot.register_next_step_handler(msg, delivery_step_address)

def delivery_step_address(message):
    chat_id = message.chat.id
    user_data[chat_id]["address"] = message.text
    msg = bot.send_message(chat_id, "Рақами телефон:")
    bot.register_next_step_handler(msg, delivery_step_phone)

def delivery_step_phone(message):
    chat_id = message.chat.id
    user_data[chat_id]["phone"] = message.text
    data = user_data[chat_id]
    delivery_text = (
        f"📦 *НОВАЯ ЗАЯВКА НА ДОСТАВКУ*\n"
        f"Имя: {data['name']}\n"
        f"Адрес: {data['address']}\n"
        f"Телефон: {data['phone']}"
    )
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
        msg = bot.send_message(chat_id, "❌ Танҳо ҳарфҳои англисӣ нависед!")
        bot.register_next_step_handler(msg, address_step_name)
        return
    user_data[chat_id] = {"name": message.text}
    msg = bot.send_message(chat_id, "Рақами телефони худро ворид кунед:")
    bot.register_next_step_handler(msg, address_step_phone)

def address_step_phone(message):
    chat_id = message.chat.id
    user_data[chat_id]["phone"] = message.text
    data = user_data[chat_id]
    full_address = (
        f"{data['name']} 17590820846 浙江省 金华市 义乌市 福田三小区80栋二单元305室{data['name']}{data['phone']}"
    )
    bot.send_message(chat_id, full_address)
    send_main_menu(chat_id)

# ================== ТРЕК-КОДА ==================
def track_step(message):
    chat_id = message.chat.id
    code = message.text.strip().upper()
    status = "❌ Трек-код не найден"

    if sheet:
        try:
            # Загружаем все записи из Google Sheet
            records = sheet.get_all_records()
            # Ищем совпадение по коду
            for row in records:
                if str(row.get("TrackCode", "")).upper() == code:
                    status = row.get("Status", status)
                    break
        except Exception as e:
            status = f"❌ Ошибка чтения таблицы: {e}"
    else:
        status = "⚠ Таблица не подключена"

    bot.send_message(chat_id, f"Статус груза {code}:\n{status}")
    send_main_menu(chat_id)
print("Код из сообщения:", code)
print("Все записи:", records)
# ================== Загрузка всех трек-кодов в память ==================
# (для ускоренного поиска, если много данных)
track_codes_cache = {}

def load_track_codes_cache():
    global track_codes_cache
    if sheet:
        try:
            records = sheet.get_all_records()
            track_codes_cache = {str(row.get("TrackCode", "")).upper(): row.get("Status", "") for row in records}
            print(f"✅ Загружено {len(track_codes_cache)} трек-кодов")
        except Exception as e:
            print(f"❌ Ошибка загрузки трек-кодов: {e}")

def track_step_cached(message):
    chat_id = message.chat.id
    code = message.text.strip().upper()
    status = track_codes_cache.get(code, "❌ Трек-код не найден")
    bot.send_message(chat_id, f"Статус груза {code}:\n{status}")
    send_main_menu(chat_id)

# ================== ADMIN ТРЕК-КОДА ==================
@bot.message_handler(commands=["add_track"])
def add_track(message):
    if message.from_user.id not in ADMINS:
        bot.send_message(message.chat.id, "❌ Доступ запрещен.")
        return
    msg = bot.send_message(message.chat.id, "Введите трек-код:")
    bot.register_next_step_handler(msg, add_track_step)

def add_track_step(message):
    track_code = message.text.strip().upper()
    msg = bot.send_message(message.chat.id, f"Введите статус для трек-кода {track_code}:")
    bot.register_next_step_handler(msg, lambda m: save_track_status(track_code, m))

def save_track_status(track_code, message):
    status = message.text.strip()

    if not sheet:
        bot.send_message(message.chat.id, "⚠ Таблица не подключена, нельзя сохранить трек-код.")
        return

    try:
        # Ищем трек-код в таблице
        cell = sheet.find(track_code)
        if cell:
            # Обновляем статус во второй колонке
            sheet.update_cell(cell.row, 2, status)
            bot.send_message(message.chat.id, f"✅ Трек-код {track_code} обновлён.")
        else:
            # Добавляем новый трек-код в конец таблицы
            sheet.append_row([track_code, status])
            bot.send_message(message.chat.id, f"✅ Трек-код {track_code} добавлен.")

    except Exception as e:
        bot.send_message(message.chat.id, f"⚠ Ошибка работы с таблицей: {e}")
# ================== Загрузка кэша при старте ==================
if sheet:
    load_track_codes_cache()

# ================== Контакты ==================
def show_contacts(chat_id):
    text = "📞 *Ракамхо мо*\n\n"
    markup = types.InlineKeyboardMarkup(row_width=1)

    markup.add(types.InlineKeyboardButton("📱 +992 985 171 732", url="https://t.me/zubaidullo_tjk"))
    markup.add(types.InlineKeyboardButton("📱 +992 026 460 110", url="https://t.me/mprotj"))
    markup.add(types.InlineKeyboardButton("📱 +992 007 282 626", url="https://t.me/Fayoz_7707"))
    markup.add(types.InlineKeyboardButton("📢 Канал Telegram", url="https://t.me/TAJEXPRESSCARGO"))

    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

    info_text = (
        "📞 Тамос: 8:00–17:30\n"
        "КАРГОИ БОВАРИНОК 🚚✅\n"
        "Мӯҳлати доставка: 15–25 рӯз (мо одатан борро пеш аз муҳлат мебиёрем)"
    )
    bot.send_message(chat_id, info_text)

# ================== RUN BOT ==================
if __name__ == "__main__":
    print("Bot started...")
    bot.infinity_polling()
