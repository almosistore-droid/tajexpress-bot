import os
import telebot
from telebot import types

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

# --- Кнопки меню ---
BUTTON_GET_ADDRESS = "🏠 🇨🇳 Гирифтани адрес ва код"
BUTTON_DELIVERY = "🚚 Доставка"
BUTTON_CALC = "📦 Нархнома"
BUTTON_TRACK = "🔍 Проверка трек-кода"
BUTTON_CONTACT = "📞 Контакты"
BUTTON_TAJIK_ADDR = "🇹🇯 Адрес Душанбе"
BUTTON_PROHIBITED = "Молхои манъшуда"

# --- Глобальные переменные ---
user_data = {}
DELIVERY_GROUP_ID = int(os.environ.get("DELIVERY_GROUP_ID", "-5077729823"))

# --- Обработчик /start ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.row(types.KeyboardButton(BUTTON_GET_ADDRESS), types.KeyboardButton(BUTTON_DELIVERY))
    markup.row(types.KeyboardButton(BUTTON_CALC), types.KeyboardButton(BUTTON_TRACK))
    markup.row(types.KeyboardButton(BUTTON_TAJIK_ADDR), types.KeyboardButton(BUTTON_PROHIBITED))
    markup.row(types.KeyboardButton(BUTTON_CONTACT))
    bot.send_message(chat_id, "Добро пожаловать в TAJ-EXPRESS! 🚚\nВыберите пункт меню:", reply_markup=markup)

# --- Пример обработчика получения адреса ---
@bot.message_handler(func=lambda message: message.text == BUTTON_GET_ADDRESS)
def get_full_address(message):
    chat_id = message.chat.id
    msg = bot.send_message(chat_id, "Введите ваше имя:")
    bot.register_next_step_handler(msg, get_name_for_address)

def get_name_for_address(message):
    chat_id = message.chat.id
    user_data[chat_id] = {"name": message.text}
    msg = bot.send_message(chat_id, "Введите ваш номер телефона:")
    bot.register_next_step_handler(msg, get_phone_for_address)

def get_phone_for_address(message):
    chat_id = message.chat.id
    user_data[chat_id]["phone"] = message.text
    name = user_data[chat_id]["name"]
    phone = user_data[chat_id]["phone"]
    final_address = f"Amin 17590820846 浙江省金华市义乌市 福田三小区80栋二单元305室 {name} {phone}"
    bot.send_message(chat_id, final_address)
    send_welcome(message)

# --- Добавляем остальные обработчики как в твоем коде ---
# Delivery, Calc, Track, Contacts, Dushanbe, Prohibited
