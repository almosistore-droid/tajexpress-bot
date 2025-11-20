# bot.py
import os
import telebot
from telebot import types
from telebot.apihelper import ApiTelegramException
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not defined.")

bot = telebot.TeleBot(TOKEN, threaded=False)

DELIVERY_GROUP_ID = int(os.getenv("DELIVERY_GROUP_ID", 0))
ADMINS = [123456789]  # сюда вставьте свои Telegram ID для админов

# --- Глобальные переменные ---
user_data = {}
track_codes = {}  # ключ: номер трек-кода, значение: статус

print("Bot initialized. DELIVERY_GROUP_ID =", DELIVERY_GROUP_ID)
