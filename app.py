import os
from flask import Flask, request
from dotenv import load_dotenv
from bot import bot  # импорт TeleBot объекта
from telebot.types import Update

# Загрузка переменных окружения
load_dotenv()

WEBHOOK_BASE = os.getenv("WEBHOOK_URL")
if not WEBHOOK_BASE:
    raise RuntimeError("WEBHOOK_URL is not defined!")

WEBHOOK_ROUTE = f"/{bot.token}"
WEBHOOK_URL = WEBHOOK_BASE.rstrip("/") + WEBHOOK_ROUTE

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET", "change-me")

# --- Маршрут webhook ---
@app.route(WEBHOOK_ROUTE, methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_string = request.get_data().decode("utf-8")
        update = Update.de_json(json_string)
        bot.process_new_updates([update])
        return "ok", 200
    return "Not JSON", 403

# --- Главная страница ---
@app.route("/")
def index():
    return "TAJ-EXPRESS bot (webhook) is running ✅", 200

# --- Установка webhook при старте ---
try:
    bot.remove_webhook()
    ok = bot.set_webhook(url=WEBHOOK_URL)
    print("Webhook set ->", ok, WEBHOOK_URL)
except Exception as e:
    print("Warning: failed to set webhook during import:", e)

# --- Локальный запуск для теста ---
if __name__ == "__main__":
    print("Приложение запущено локально.")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
