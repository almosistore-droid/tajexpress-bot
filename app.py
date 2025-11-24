import os
from flask import Flask, request
import telebot
from bot import bot, TOKEN

WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # https://tajexpress-bot.onrender.com
if not TOKEN or not WEBHOOK_URL:
    raise RuntimeError("TELEGRAM_BOT_TOKEN или WEBHOOK_URL не определены!")

WEBHOOK_ROUTE = f"/{TOKEN}"
FULL_WEBHOOK_URL = WEBHOOK_URL.rstrip("/") + WEBHOOK_ROUTE

app = Flask(__name__)

# ===== Webhook endpoint =====
@app.route(WEBHOOK_ROUTE, methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        data = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(data)
        bot.process_new_updates([update])
        return "ok", 200
    return "Not JSON", 403

# ===== Root =====
@app.route("/", methods=["GET"])
def index():
    return "TAJ-EXPRESS bot running ✅", 200

# ===== Установка webhook (для локального запуска) =====
if __name__ == "__main__":
    try:
        bot.remove_webhook()
        bot.set_webhook(url=FULL_WEBHOOK_URL)
        print("Webhook установлен:", FULL_WEBHOOK_URL)
    except Exception as e:
        print("Ошибка установки webhook:", e)
