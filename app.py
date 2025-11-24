# app.py
import os
from flask import Flask, request
from dotenv import load_dotenv
import telebot
from telebot import types
from bot import bot, TOKEN  # импортируем bot и TOKEN из bot.py

load_dotenv()

WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # https://tajexpress-bot.onrender.com
FLASK_SECRET = os.getenv("FLASK_SECRET", "secret-key")

if not TOKEN or not WEBHOOK_URL:
    raise RuntimeError("TELEGRAM_BOT_TOKEN или WEBHOOK_URL не определены!")

WEBHOOK_ROUTE = f"/{TOKEN}"
FULL_WEBHOOK_URL = WEBHOOK_URL.rstrip("/") + WEBHOOK_ROUTE

app = Flask(__name__)
app.config["SECRET_KEY"] = FLASK_SECRET

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

# ===== Webhook setup =====
if __name__ == "__main__":
    try:
        bot.remove_webhook()
        bot.set_webhook(url=FULL_WEBHOOK_URL)
        print("Webhook установлен:", FULL_WEBHOOK_URL)
    except Exception as e:
        print("Ошибка при установке webhook:", e)

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
