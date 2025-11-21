import os
import telebot
from telebot import types
from telebot.apihelper import ApiTelegramException
from dotenv import load_dotenv
import json

# -----------------------------
# Настройки
# -----------------------------
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN не определен!")
bot = telebot.TeleBot(TOKEN, threaded=False)

try:
    DELIVERY_GROUP_ID = int(os.getenv("DELIVERY_GROUP_ID", "0"))
except ValueError:
    DELIVERY_GROUP_ID = 0

TRACK_FILE = "track_codes.json"


def load_track_codes():
    try:
        with open(TRACK_FILE, "r") as f:
            return json.load(f)
    except:
        return {}


def save_track_codes(codes):
    with open(TRACK_FILE, "w") as f:
        json.dump(codes, f, indent=4)


# -----------------------------
# Администраторы (user_id)
# -----------------------------
ADMINS = [1324431208]

# -----------------------------
# Хранилище для пользователей
# -----------------------------
user_data = {}

# -----------------------------
# Кнопки меню
# -----------------------------
BTN_DELIVERY = "🚚 Доставка"
BTN_ADDRESS = "🇨🇳 Гирифтани адрес"
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

# -----------------------------
# Главное меню
# -----------------------------
def send_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for row in MAIN_MENU:
        markup.add(*[types.KeyboardButton(text) for text in row])

    welcome_text = (
        "🚀 TAJEXPRESS – каргои боваринок ва бехатар барои овардани борхои Шумо!\n\n"
        "📦 Борҳои худро зуд ва бехатар фиристед\n"
        "⏱ Дархостҳоро осон ва зуд иҷро намоед\n"
        "🇨🇳 Суроғаи қулай дар Чин барои харидҳои шумо\n\n"
        "Менюи зерро интихоб кунед:"
    )

    bot.send_message(chat_id, welcome_text, reply_markup=markup)


# -----------------------------
# Команда /start
# -----------------------------
@bot.message_handler(commands=["start", "help"])
def start_handler(message):
    send_main_menu(message.chat.id)


# -----------------------------
# Основной обработчик кнопок
# -----------------------------
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
        msg = bot.send_message(chat_id, "Трек-коди худро ворид кунед:")
        bot.register_next_step_handler(msg, track_step)

    elif text == BTN_DUSHANBE:
        bot.send_message(chat_id, "🇹🇯 Адрес: Душанбе, к. Хисор 34\nТелефон: +992 985171732")

    elif text == BTN_BANNED:
        bot.send_message(chat_id,
            "🚫 Молҳои манъшуда:\n"
            "1. Взрывоопасные вещества\n"
            "2. Батарейки, аккумуляторы, магниты, повербанки\n"
            "3. Продукты питания, семена\n"
            "4. Оружие, ножи, кастеты\n"
            "5. Химические вещества, аэрозоли\n"
            "6. Золото, серебро\n"
            "7. Жидкости любых видов"
        )

    elif text == BTN_CONTACTS:
        bot.send_message(chat_id,
            "📞 Тамос:\n"
            "8:00–17:30\n\n"
            "📱 +992 985 171 732\n"
            "📱 +992 026 460 110\n"
            "📱 +992 007 282 626\n\n"
            "КАРГОИ БОВАРИНОК 🚚✅\n"
            "Мӯҳлати доставка: 15–25 рӯз.\n"
            "Канал: https://t.me/TAJEXPRESSCARGO"
        )

    else:
        send_main_menu(chat_id)


# -----------------------------
# Доставка
# -----------------------------
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

    delivery_text = (
        f"📦 *НОВАЯ ЗАЯВКА*\n"
        f"👤 Имя: {data['name']}\n"
        f"📍 Адрес: {data['address']}\n"
        f"📞 Телефон: {data['phone']}"
    )

    try:
        bot.send_message(DELIVERY_GROUP_ID, delivery_text, parse_mode="Markdown")
        bot.send_message(chat_id, "Дархост қабул шуд ✅")
    except ApiTelegramException as e:
        bot.send_message(chat_id, f"Хатогӣ: {e}")

    send_main_menu(chat_id)


# -----------------------------
# Гирифтани адрес ва код
# -----------------------------
def address_step_name(message):
    chat_id = message.chat.id

    if not message.text.isascii():
        msg = bot.send_message(chat_id, "❌ Танҳо ҳарфҳои англисӣ нависед.")
        bot.register_next_step_handler(msg, address_step_name)
        return

    user_data[chat_id] = {"name": message.text}

    msg = bot.send_message(chat_id, "Рақами телефони худро ворид кунед:")
    bot.register_next_step_handler(msg, address_step_phone)


def address_step_phone(message):
    chat_id = message.chat.id
    user_data[chat_id]["phone"] = message.text
    data = user_data[chat_id]

    name = data['name']
    phone = data['phone']

    full_address = (
        f"{name} 17590820846 浙江省金华市义乌市 福田三小区80栋二单元305室楼下 "
        f"#58# {name} {phone}"
    )

    bot.send_message(chat_id, full_address)
    send_main_menu(chat_id)


# -----------------------------
# Проверка трек-кодов
# -----------------------------
def track_step(message):
    chat_id = message.chat.id
    code = message.text.strip().upper()

    track_codes = load_track_codes()
    status = track_codes.get(code, "❌ Трек-код ёфт нашуд.")

    bot.send_message(chat_id, f"📦 {code}\nСтатус: {status}")
    send_main_menu(chat_id)


# -----------------------------
# Админ: добавление трек-кодов
# -----------------------------
@bot.message_handler(commands=["add_track"])
def add_track(message):
    if message.from_user.id not in ADMINS:
        bot.send_message(message.chat.id, "❌ Дастрасӣ манъ аст.")
        return

    msg = bot.send_message(message.chat.id, "Трек-кодро нависед:")
    bot.register_next_step_handler(msg, add_track_step)


def add_track_step(message):
    track_code = message.text.strip().upper()
    msg = bot.send_message(message.chat.id, f"Статус барои {track_code}-ро нависед:")
    bot.register_next_step_handler(msg, lambda m: save_track_status(track_code, m))


def save_track_status(track_code, message):
    track_codes = load_track_codes()
    status = message.text.strip()

    track_codes[track_code] = status
    save_track_codes(track_codes)

    bot.send_message(message.chat.id, f"✅ Трек-код {track_code} нав карда шуд.")

    try:
        bot.send_message(
            DELIVERY_GROUP_ID,
            f"🆕 Трек-код: {track_code}\nСтатус: {status}"
        )
    except:
        pass


# -----------------------------
# Запуск бота
# -----------------------------
if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling()
