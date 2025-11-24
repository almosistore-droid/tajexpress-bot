import os
from flask import Flask, request
from dotenv import load_dotenv
import telebot
from telebot import types
from bot import bot, TOKEN   # Импортируем только bot и TOKEN из bot.py

load_dotenv()

# === Настройка вебхука ===
WEBHOOK_HOST = "https://tajexpress-bot.onrender.com"
WEBHOOK_URL = f"{WEBHOOK_HOST}/{TOKEN}"

app = Flask(__name__)

# === Webhook endpoint ===
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

# === Главная страница ===
@app.route("/", methods=["GET"])
def index():
    return "TAJ-EXPRESS bot running ✅", 200


# === Запуск приложения и установка webhook ===
if __name__ == "__main__":
    try:
        bot.remove_webhook()
        bot.set_webhook(url=WEBHOOK_URL)
        print("Webhook установлен:", WEBHOOK_URL)
    except Exception as e:
        print("Ошибка установки вебхука:", e)

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
