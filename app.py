import os
from flask import Flask, request
from bot import bot  # предполагаем, что у тебя есть bot.py с объектом TeleBot

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("FLASK_SECRET", "supersecretkey")

# --- Проверка токена ---
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("Ошибка: TELEGRAM_BOT_TOKEN не определён! Установи переменную окружения на Render.")

# --- Инициализация админ-панели ---
try:
    from admin import init_admin
    init_admin(app)
except ModuleNotFoundError:
    print("Admin panel не подключена (нет модуля admin)")

# --- Webhook URL ---
WEBHOOK_URL_BASE = os.environ.get("WEBHOOK_URL")
if not WEBHOOK_URL_BASE:
    raise ValueError("Ошибка: WEBHOOK_URL не определён! Установи переменную окружения на Render.")

WEBHOOK_ROUTE = '/' + TOKEN
WEBHOOK_URL = WEBHOOK_URL_BASE + WEBHOOK_ROUTE

# --- Установка Webhook при старте ---
@app.before_serving
def setup_webhook():
    """Удаление старого и установка нового Webhook"""
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    print(f"WEBHOOK установлен: {WEBHOOK_URL}")

@app.route(WEBHOOK_ROUTE, methods=['POST'])
def webhook():
    """Приём обновлений от Telegram"""
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = bot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'ok', 200
    else:
        return 'Invalid request', 403

@app.route("/")
def index():
    return "Telegram bot is running ✅", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
