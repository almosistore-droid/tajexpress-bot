# bot.py
import os
import telebot
from telebot import types
from telebot.apihelper import ApiTelegramException
from dotenv import load_dotenv

# Для локальной разработки .env
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    # если переменная отсутствует — бросаем исключение, но app.py уже защитит от этого
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not defined.")

# threaded=False — важно для webhook обработки внутри bot.process_new_updates
bot = telebot.TeleBot(TOKEN, threaded=False)

# DELIVERY_GROUP_ID может быть пустым в dev, используем 0 по умолчанию
try:
    DELIVERY_GROUP_ID = int(os.getenv("DELIVERY_GROUP_ID", "0"))
except ValueError:
    DELIVERY_GROUP_ID = 0

# Пример логирования
print("Bot initialized. DELIVERY_GROUP_ID =", DELIVERY_GROUP_ID)

# --- Кнопки меню ---
BUTTON_GET_ADDRESS = "🏠 🇨🇳 Гирифтани адрес ва код"
BUTTON_DELIVERY = "🚚 Доставка"
BUTTON_CALC = "📦 Нархнома"
BUTTON_TRACK = "🔍 Проверка трек-кода"
BUTTON_CONTACT = "📞 Контакты"
BUTTON_TAJIK_ADDR = "🇹🇯 Адрес Душанбе"
BUTTON_PROHIBITED = "Молхои манъшуда"

user_data = {}

def send_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.row(types.KeyboardButton(BUTTON_GET_ADDRESS), types.KeyboardButton(BUTTON_DELIVERY))
    markup.row(types.KeyboardButton(BUTTON_CALC), types.KeyboardButton(BUTTON_TRACK))
    markup.row(types.KeyboardButton(BUTTON_TAJIK_ADDR), types.KeyboardButton(BUTTON_PROHIBITED))
    markup.row(types.KeyboardButton(BUTTON_CONTACT))
    bot.send_message(chat_id, "Добро пожаловать в TAJ-EXPRESS! 🚚\nВыберите пункт меню:", reply_markup=markup)

@bot.message_handler(commands=['start','help'])
def cmd_start(message):
    send_main_menu(message.chat.id)

# остальные обработчики (как у тебя)...
# например:
@bot.message_handler(func=lambda m: m.text == BUTTON_GET_ADDRESS)
def get_address(message):
    msg = bot.send_message(message.chat.id, "Введите ваше имя:")
    bot.register_next_step_handler(msg, get_name_step)

def get_name_step(message):
    chat_id = message.chat.id
    user_data[chat_id] = {"name": message.text}
    msg = bot.send_message(chat_id, "Введите ваш телефон:")
    bot.register_next_step_handler(msg, get_phone_step)

def get_phone_step(message):
    chat_id = message.chat.id
    name = user_data[chat_id]["name"]
    phone = message.text
    final = f"Amin ... {name} {phone}"
    bot.send_message(chat_id, final)
    send_main_menu(chat_id)

# fallback
@bot.message_handler(func=lambda m: True)
def fallback(message):
    bot.reply_to(message, "Пожалуйста, используйте кнопки меню или /start.")
