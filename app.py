import os
from flask import Flask, request
from dotenv import load_dotenv
import telebot
from bot import bot  # объект bot из bot.py

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
FLASK_SECRET = os.getenv("FLASK_SECRET", "change-me")

if not TOKEN or not WEBHOOK_URL:
    raise RuntimeError("❌ TELEGRAM_BOT_TOKEN или WEBHOOK_URL не определены!")

WEBHOOK_ROUTE = f"/{TOKEN}"
FULL_WEBHOOK_URL = WEBHOOK_URL.rstrip("/") + WEBHOOK_ROUTE

app = Flask(__name__)
app.config["SECRET_KEY"] = FLASK_SECRET

# ===== Webhook endpoint =====
@app.route(WEBHOOK_ROUTE, methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_string = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "ok", 200
    return "Not JSON", 403

@app.route("/", methods=["GET"])
def index():
    return "TAJ-EXPRESS bot running ✅", 200

if __name__ == "__main__":
    try:
        bot.remove_webhook()
        ok = bot.set_webhook(url=FULL_WEBHOOK_URL)
        print("Webhook установлен ->", ok, FULL_WEBHOOK_URL)
    except Exception as e:
        print("❌ Ошибка при установке webhook:", e)
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
