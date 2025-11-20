import os
import telebot
from telebot import types
from telebot.apihelper import ApiTelegramException
from dotenv import load_dotenv

# Загрузка переменных окружения из .env для локальной разработки
load_dotenv()

# Токен бота
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not defined!")

# Инициализация бота
bot = telebot.TeleBot(TOKEN, threaded=False)

# ID группы для заявок на доставку
try:
    DELIVERY_GROUP_ID = int(os.getenv("DELIVERY_GROUP_ID", "0"))
except ValueError:
    DELIVERY_GROUP_ID = 0

print("Bot initialized. DELIVERY_GROUP_ID =", DELIVERY_GROUP_ID)

# Глобальные данные для многошаговой логики
user_data = {}

# Кнопки меню
BUTTON_GET_ADDRESS = "🏠 🇨🇳 Гирифтани адрес ва код"
BUTTON_DELIVERY = "🚚 Доставка"
BUTTON_CALC = "📦 Нархнома"
BUTTON_TRACK = "🔍 Проверка трек-кода"
BUTTON_CONTACT = "📞 Контакты"
BUTTON_TAJIK_ADDR = "🇹🇯 Адрес Душанбе"
BUTTON_PROHIBITED = "Молхои манъшуда"

# Функция для показа главного меню
def send_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.row(types.KeyboardButton(BUTTON_GET_ADDRESS), types.KeyboardButton(BUTTON_DELIVERY))
    markup.row(types.KeyboardButton(BUTTON_CALC), types.KeyboardButton(BUTTON_TRACK))
    markup.row(types.KeyboardButton(BUTTON_TAJIK_ADDR), types.KeyboardButton(BUTTON_PROHIBITED))
    markup.row(types.KeyboardButton(BUTTON_CONTACT))
    bot.send_message(chat_id, "Добро пожаловать в TAJ-EXPRESS! 🚚\nВыберите пункт меню:", reply_markup=markup)

# Старт и помощь
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    send_main_menu(message.chat.id)

# --- Дальше идут все функции для кнопок: GET_ADDRESS, DELIVERY, CALC, TRACK, CONTACT, и др. ---
# Здесь можно вставить все обработчики из твоего предыдущего кода (get_address, delivery_start, calc_start и т.д.)
