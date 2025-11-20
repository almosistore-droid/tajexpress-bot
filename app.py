# app.py
import os
from flask import Flask, request
from dotenv import load_dotenv

# загружаем .env (для локальной разработки)
load_dotenv()

# Берём токен и URL из окружения (Render / локально через .env)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_BASE = os.getenv("WEBHOOK_URL")  # например: https://tajexpress-cargo-bot.onrender.com
FLASK_SECRET = os.getenv("FLASK_SECRET", "change-me")

if not TOKEN:
    raise RuntimeError("Ошибка: TELEGRAM_BOT_TOKEN не задан. Установите переменную окружения в Render (или .env для локали).")

if not WEBHOOK_BASE:
    raise RuntimeError("Ошибка: WEBHOOK_URL не задан. Установите переменную окружения в Render.")

WEBHOOK_ROUTE = f"/{TOKEN}"
WEBHOOK_URL = WEBHOOK_BASE.rstrip("/") + WEBHOOK_ROUTE

# Импорт бота (bot должен использовать тот же TOKEN)
# Импорт выполняем после проверки переменных, чтобы избежать ошибок при старте
from bot import bot  # assumes bot.py defines `bot` (TeleBot instance)

app = Flask(__name__)
app.config["SECRET_KEY"] = FLASK_SECRET

from telebot.types import Update

@app.route(WEBHOOK_ROUTE, methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_string = request.get_data().decode("utf-8")
        update = Update.de_json(json_string)
        bot.process_new_updates([update])
        return "ok", 200
    return "Not JSON", 403
@app.route("/")
def index():
    return "TAJ-EXPRESS bot (webhook) is running ✅", 200

# IMPORTANT:
# Render runs via gunicorn which imports app module. Gunicorn will not execute __main__,
# so we must set webhook when the process starts. We'll attempt to set it here safely.
try:
    # set webhook once when module imported
    bot.remove_webhook()
    ok = bot.set_webhook(url=WEBHOOK_URL)
    print("Webhook set ->", ok, WEBHOOK_URL)
except Exception as e:
    print("Warning: failed to set webhook during import:", e)

# Note: do not put blocking code here.
