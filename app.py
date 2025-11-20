# app.py
import os
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_BASE = os.getenv("WEBHOOK_URL")
FLASK_SECRET = os.getenv("FLASK_SECRET", "supersecretkey")

if not TOKEN or not WEBHOOK_BASE:
    raise RuntimeError("TELEGRAM_BOT_TOKEN или WEBHOOK_URL не заданы!")

WEBHOOK_ROUTE = f"/{TOKEN}"
WEBHOOK_URL = WEBHOOK_BASE.rstrip("/") + WEBHOOK_ROUTE

from bot import bot

app = Flask(__name__)
app.config["SECRET_KEY"] = FLASK_SECRET

@app.route(WEBHOOK_ROUTE, methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_string = request.get_data().decode("utf-8")
        from telebot.types import Update
        update = Update.de_json(json_string)
        bot.process_new_updates([update])
        return "ok", 200
    return "Not JSON", 403

@app.route("/")
def index():
    return "TAJ-EXPRESS bot (webhook) is running ✅", 200

# Установка webhook при старте
try:
    bot.remove_webhook()
    ok = bot.set_webhook(url=WEBHOOK_URL)
    print("Webhook set ->", ok, WEBHOOK_URL)
except Exception as e:
    print("Warning: failed to set webhook during import:", e)

