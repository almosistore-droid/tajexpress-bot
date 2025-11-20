# bot.py
import os
import telebot
from telebot import types
from telebot.apihelper import ApiTelegramException
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not defined.")

bot = telebot.TeleBot(TOKEN, threaded=False)

try:
    DELIVERY_GROUP_ID = int(os.getenv("DELIVERY_GROUP_ID", 0))
except ValueError:
    DELIVERY_GROUP_ID = 0

print("Bot initialized. DELIVERY_GROUP_ID =", DELIVERY_GROUP_ID)

# Глобальные данные пользователей
user_data = {}

# --- Кнопки меню ---
BUTTON_GET_ADDRESS = "🏠 🇨🇳 Гирифтани адрес ва код"
BUTTON_DELIVERY = "🚚 Доставка"
BUTTON_CALC = "📦 Нархнома"
BUTTON_TRACK = "🔍 Проверка трек-кода"
BUTTON_CONTACT = "📞 Контакты"
BUTTON_TAJIK_ADDR = "🇹🇯 Адрес Душанбе"
BUTTON_PROHIBITED = "Молхои манъшуда"

def send_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.row(types.KeyboardButton(BUTTON_GET_ADDRESS), types.KeyboardButton(BUTTON_DELIVERY))
    markup.row(types.KeyboardButton(BUTTON_CALC), types.KeyboardButton(BUTTON_TRACK))
    markup.row(types.KeyboardButton(BUTTON_TAJIK_ADDR), types.KeyboardButton(BUTTON_PROHIBITED))
    markup.row(types.KeyboardButton(BUTTON_CONTACT))
    bot.send_message(chat_id, "Выберите пункт меню:", reply_markup=markup)

# --- Гирифтани адрес ва код ---
@bot.message_handler(func=lambda m: m.text == BUTTON_GET_ADDRESS)
def get_address(message):
    chat_id = message.chat.id
    msg = bot.send_message(chat_id, "Введите ваше имя:")
    bot.register_next_step_handler(msg, get_name_step)

def get_name_step(message):
    chat_id = message.chat.id
    user_data[chat_id] = {"name": message.text}
    msg = bot.send_message(chat_id, "Введите ваш номер телефона:")
    bot.register_next_step_handler(msg, get_phone_step)

def get_phone_step(message):
    chat_id = message.chat.id
    user_data[chat_id]["phone"] = message.text
    name = user_data[chat_id]["name"]
    phone = user_data[chat_id]["phone"]
    final_address = f"Amin 17590820846 浙江省金华市义乌市 福田三小区80栋二单元305室 {name} {phone}"
    bot.send_message(chat_id, final_address)
    send_main_menu(chat_id)

# --- Доставка заявки (имя, адрес, телефон) ---
@bot.message_handler(func=lambda m: m.text == BUTTON_DELIVERY)
def delivery_start(message):
    chat_id = message.chat.id
    msg = bot.send_message(chat_id, "Введите ваше имя:")
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
    user_data[chat_id]["delivery_phone"] = message.text
    data = user_data[chat_id]
    delivery_text = (
        f"📦 *НОВАЯ ЗАЯВКА НА ДОСТАВКУ*\n"
        f"Имя: {data['delivery_name']}\n"
        f"Адрес: {data['delivery_address']}\n"
        f"Телефон: {data['delivery_phone']}"
    )
    try:
        bot.send_message(DELIVERY_GROUP_ID, delivery_text, parse_mode="Markdown")
        bot.send_message(chat_id, "Заявка отправлена ✅")
    except ApiTelegramException as e:
        bot.send_message(chat_id, f"Ошибка отправки заявки: {e}")
    send_main_menu(chat_id)

# --- Нархнома (список услуг) ---
@bot.message_handler(func=lambda m: m.text == BUTTON_CALC)
def show_price_list(message):
    chat_id = message.chat.id
    price_list = (
        "📦 *Нархнома TAJ-EXPRESS*\n"
        "1. Малый пакет (до 5 кг) — 500 руб.\n"
        "2. Средний пакет (до 10 кг) — 1000 руб.\n"
        "3. Большой пакет (до 20 кг) — 2000 руб.\n"
        "Для точной стоимости свяжитесь с менеджером."
    )
    bot.send_message(chat_id, price_list, parse_mode="Markdown")
    send_main_menu(chat_id)

# --- Проверка трек-кода (пример с API-заглушкой) ---
@bot.message_handler(func=lambda m: m.text == BUTTON_TRACK)
def track_start(message):
    msg = bot.send_message(message.chat.id, "Введите номер для отслеживания (например, TAJ12345):")
    bot.register_next_step_handler(msg, track_step)

def track_step(message):
    number = message.text.strip().upper()
    # TODO: подключить реальный API трекинга
    # Пример: https://api.example.com/track?number=...
    # Пока просто заглушка:
    example_statuses = {
        "TAJ12345": "В пути, прибытие 25.11.2025.",
        "TAJ67890": "На складе в Москве, готовится к отправке.",
    }
    status = example_statuses.get(number, "Груз не найден. Проверьте номер.")
    bot.send_message(message.chat.id, f"Статус груза {number}:\n{status}")
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

# --- Фолбэк для всех остальных сообщений ---
@bot.message_handler(f_
