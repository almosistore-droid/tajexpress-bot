import os
import telebot
from telebot import types
from dotenv import load_dotenv

# Загружаем .env (если он есть)
load_dotenv()

# Берём токен из переменных окружения
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if TOKEN is None:
    raise ValueError("Ошибка: TELEGRAM_BOT_TOKEN не найден! Укажите токен в .env или в Render Environment.")

bot = telebot.TeleBot(TOKEN)

# Пример кнопки
BUTTON_START = "Старт"

@bot.message_handler(commands=['start'])
def start_handler(message):
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton(BUTTON_START))
    bot.send_message(chat_id, "Привет! Выберите действие:", reply_markup=markup)
