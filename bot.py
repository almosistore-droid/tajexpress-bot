import os
import telebot
from telebot import types
from telebot.apihelper import ApiTelegramException
from dotenv import load_dotenv
import re  # Для проверки имени на латиницу

# Загружаем переменные окружения из .env
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN не определен!")

bot = telebot.TeleBot(TOKEN, threaded=False)

try:
    DELIVERY_GROUP_ID = int(os.getenv("DELIVERY_GROUP_ID", "0"))
except ValueError:
    DELIVERY_GROUP_ID = 0

# --- Хранилища данных ---
user_data = {}
track_codes = {
    "TAJ12345": "В пути, прибытие 25.11.2025",
    "TAJ54321": "Доставлено, 19.11.2025"
}

# --- Администраторы ---
ADMINS = [123456789]  # Вставьте сюда id админа

# --- Кнопки меню ---
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

# --- Главное меню ---
def send_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for row in MAIN_MENU:
        markup.add(*[types.KeyboardButton(text) for text in row])
    bot.send_message(chat_id, "Выберите пункт меню:", reply_markup=markup)

# --- Команда /start ---
@bot.message_handler(commands=["start", "help"])
def start_handler(message):
    send_main_menu(message.chat.id)

# --- Основной обработчик кнопок ---
@bot.message_handler(func=lambda m: True)
def main_handler(message):
    chat_id = message.chat.id
    text = message.text

    if text == BTN_DELIVERY:
        msg = bot.send_message(chat_id, "Введите ваше имя для заявки:")
        bot.register_next_step_handler(msg, delivery_step_name)

    elif text == BTN_ADDRESS:
        msg = bot.send_message(chat_id, "Номи худро ворид кунед (бо ҳарфҳои англисӣ):")
        bot.register_next_step_handler(msg, address_step_name)  # Проверка английских букв внутри функции

    elif text == BTN_PRICE_LIST:
        bot.send_message(chat_id, "📦 Список тарифов:\n1. Малый груз — 2000 руб.\n2. Средний груз — 4000 руб.\n3. Большой груз — 6000 руб.")

    elif text == BTN_TRACK:
        msg = bot.send_message(chat_id, "Введите номер для отслеживания (например, TAJ12345):")
        bot.register_next_step_handler(msg, track_step)

    elif text == BTN_DUSHANBE:
        bot.send_message(chat_id, "🇹🇯 Адрес офиса: Душанбе, к Хисор 34\nТелефон: +992 985171732")

    elif text == BTN_BANNED:
        bot.send_message(chat_id,
            "🚫 **Запрещенные товары:**\n"
            "1. Взрывоопасные вещества\n"
            "2. Аккумуляторы, батареи, магниты, повербанки\n"
            "3. Продукты питания, семена, саженцы\n"
            "4. Оружие (в том числе игрушечное), кастеты, ножи\n"
            "5. Горюче-смазочные материалы, косметика\n"
            "6. Серебро, золото и аналогичные изделия\n"
            "7. Жидкости, аэрозоли, химические вещества"
        )

    elif text == BTN_CONTACTS:
        bot.send_message(chat_id, "📞 Служба поддержки: +992 985171732\nМенеджер: @TAJEXPRESSMANAGER")

    else:
        send_main_menu(chat_id)

# ==========================
# --- Доставка ---
# ==========================
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

# ==========================
# --- Гирифтани адрес ва код ---
# ==========================
def address_step_name(message):
    chat_id = message.chat.id
    name = message.text.strip()
    # Проверка на английские буквы и пробел
    if not re.fullmatch(r"[A-Za-z ]+", name):
        msg = bot.send_message(chat_id, "Номи худро ворид кунед (бо ҳарфҳои англисӣ)и:")
        bot.register_next_step_handler(msg, address_step_name)
        return
    user_data[chat_id] = {"name": name}
    msg = bot.send_message(chat_id, "Рақами телефони худро ворид кунед:")
    bot.register_next_step_handler(msg, address_step_phone)

def address_step_phone(message):
    chat_id = message.chat.id
    user_data[chat_id]["phone"] = message.text
    data = user_data[chat_id]
    full_address = (
        f"Amin 17590820846 浙江省金华市义乌市 福田三小区80栋二单元305室 "
        f"楼下密码 #58# {data['name']} {data['phone']}"
    )
    bot.send_message(chat_id, full_address)
    send_main_menu(chat_id)

# ==========================
# --- Проверка трек-кода ---
# ==========================
def track_step(message):
    chat_id = message.chat.id
    code = message.text.strip().upper()
    status = track_codes.get(code, "Трек-код не найден")
    bot.send_message(chat_id, f"Статус груза {code}:\n{status}")
    send_main_menu(chat_id)

# ==========================
# --- Админ: добавление трек-кодов ---
# ==========================
@bot.message_handler(commands=["add_track"])
def add_track(message):
    if message.from_user.id not in ADMINS:
        bot.send_message(message.chat.id, "❌ Доступ запрещен.")
        return
    msg = bot.send_message(message.chat.id, "Введите трек-код:")
    bot.register_next_step_handler(msg, add_track_step)

def add_track_step(message):
    track_code = message.text.strip().upper()
    msg = bot.send_message(message.chat.id, f"Введите статус для {track_code}:")
    bot.register_next_step_handler(msg, lambda m: save_track_status(track_code, m))

def save_track_status(track_code, message):
    track_codes[track_code] = message.text.strip()
    bot.send_message(message.chat.id, f"✅ Трек-код {track_code} добавлен/обновлен.")

# ==========================
# --- Запуск бота ---
# ==========================
if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling()
