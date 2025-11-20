# app.py
import os
from flask import Flask, request
from dotenv import load_dotenv
from bot import bot, user_data, track_codes, DELIVERY_GROUP_ID, ADMINS

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_BASE = os.getenv("WEBHOOK_URL")
FLASK_SECRET = os.getenv("FLASK_SECRET", "change-me")

if not TOKEN or not WEBHOOK_BASE:
    raise RuntimeError("TELEGRAM_BOT_TOKEN or WEBHOOK_URL not defined")

WEBHOOK_ROUTE = f"/{TOKEN}"
WEBHOOK_URL = WEBHOOK_BASE.rstrip("/") + WEBHOOK_ROUTE

app = Flask(__name__)
app.config["SECRET_KEY"] = FLASK_SECRET

# --- Webhook маршрут ---
@app.route(WEBHOOK_ROUTE, methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_string = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "ok", 200
    return "Not JSON", 403

@app.route("/")
def index():
    return "TAJ-EXPRESS bot running ✅", 200

# --- Установка Webhook ---
try:
    bot.remove_webhook()
    ok = bot.set_webhook(url=WEBHOOK_URL)
    print("Webhook set ->", ok, WEBHOOK_URL)
except Exception as e:
    print("Failed to set webhook:", e)

# --- Кнопки меню ---
BUTTON_GET_ADDRESS = "🏠 Гирифтани адрес ва код"
BUTTON_DELIVERY = "🚚 Доставка"
BUTTON_TRACK = "🔍 Проверка трек-кода"
BUTTON_TAJIK_ADDR = "🇹🇯 Адрес Душанбе"
BUTTON_PROHIBITED = "🚫 Молхои манъшуда"
BUTTON_CONTACT = "📞 Контакты"

def send_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.row(types.KeyboardButton(BUTTON_GET_ADDRESS), types.KeyboardButton(BUTTON_DELIVERY))
    markup.row(types.KeyboardButton(BUTTON_TRACK))
    markup.row(types.KeyboardButton(BUTTON_TAJIK_ADDR), types.KeyboardButton(BUTTON_PROHIBITED))
    markup.row(types.KeyboardButton(BUTTON_CONTACT))
    bot.send_message(chat_id, "Выберите пункт меню:", reply_markup=markup)

# --- Старт ---
@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    send_main_menu(message.chat.id)

# --- Гирифтани адрес ва код ---
@bot.message_handler(func=lambda m: m.text == BUTTON_GET_ADDRESS)
def get_address(message):
    chat_id = message.chat.id
    msg = bot.send_message(chat_id, "Введите ваше имя:")
    bot.register_next_step_handler(msg, get_name_step)

def get_name_step(message):
    chat_id = message.chat.id
    user_data[chat_id] = {"name": message.text}
    msg = bot.send_message(chat_id, "Введите номер телефона:")
    bot.register_next_step_handler(msg, get_phone_step)

def get_phone_step(message):
    chat_id = message.chat.id
    user_data[chat_id]["phone"] = message.text
    data = user_data[chat_id]
    final_address = f"Amin 17590820846 浙江省金华市义乌市 福田三小区80栋二单元305室 {data['name']} {data['phone']}"
    bot.send_message(chat_id, final_address)
    send_main_menu(chat_id)

# --- Доставка ---
@bot.message_handler(func=lambda m: m.text == BUTTON_DELIVERY)
def delivery_start(message):
    chat_id = message.chat.id
    msg = bot.send_message(chat_id, "Введите ваше имя для заявки:")
    bot.register_next_step_handler(msg, delivery_name_step)

def delivery_name_step(message):
    chat_id = message.chat.id
    user_data[chat_id] = {"delivery_name": message.text}
    msg = bot.send_message(chat_id, "Введите адрес доставки:")
    bot.register_next_step_handler(msg, delivery_address_step)

def delivery_address_step(message):
    chat_id = message.chat.id
    user_data[chat_id]["delivery_address"] = message.text
    msg = bot.send_message(chat_id, "Введите номер телефона:")
    bot.register_next_step_handler(msg, delivery_phone_step)

def delivery_phone_step(message):
    chat_id = message.chat.id
    user_data[chat_id]["phone"] = message.text
    data = user_data[chat_id]
    delivery_text = (
        f"📦 *НОВАЯ ЗАЯВКА НА ДОСТАВКУ*\n"
        f"Имя: {data['delivery_name']}\n"
        f"Адрес: {data['delivery_address']}\n"
        f"Телефон: {data['phone']}"
    )
    try:
        bot.send_message(DELIVERY_GROUP_ID, delivery_text, parse_mode="Markdown")
        bot.send_message(chat_id, "Заявка отправлена ✅")
    except ApiTelegramException as e:
        bot.send_message(chat_id, f"Ошибка отправки: {e}")
    send_main_menu(chat_id)

# --- Проверка трек-кода ---
@bot.message_handler(func=lambda m: m.text == BUTTON_TRACK)
def track_start(message):
    msg = bot.send_message(message.chat.id, "Введите номер трек-кода:")
    bot.register_next_step_handler(msg, track_step)

def track_step(message):
    number = message.text.strip().upper()
    status = track_codes.get(number)
    if status:
        bot.send_message(message.chat.id, f"Статус груза {number}:\n{status}")
    else:
        bot.send_message(message.chat.id, f"Трек-код {number} не найден.")
    send_main_menu(message.chat.id)

# --- Контакты ---
@bot.message_handler(func=lambda m: m.text == BUTTON_CONTACT)
def contact(message):
    info = "📞 Служба поддержки: +7 495 123 45 67\nEmail: support@tajexpress.com\nМенеджер: @TajExpressManager"
    bot.send_message(message.chat.id, info)
    send_main_menu(message.chat.id)

# --- Адрес Душанбе ---
@bot.message_handler(func=lambda m: m.text == BUTTON_TAJIK_ADDR)
def dushanbe_address(message):
    info = "🇹🇯 Адрес офиса: пр. Рудаки 123, Бизнес-центр 'Азия'\nТелефон: +992 900 12 34 56"
    bot.send_message(message.chat.id, info)
    send_main_menu(message.chat.id)

# --- Запрещенные товары ---
@bot.message_handler(func=lambda m: m.text == BUTTON_PROHIBITED)
def prohibited(message):
    info = "🚫 Запрещенные товары:\n1. Оружие\n2. Взрывчатые вещества\n3. Наркотики\n..."
    bot.send_message(message.chat.id, info)
    send_main_menu(message.chat.id)

# --- Админ команды ---
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
