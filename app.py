import os
from flask import Flask, request
from bot import bot, TOKEN
from admin import init_admin

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("FLASK_SECRET", "supersecretkey")

# --- Инициализация админ-панели ---
init_admin(app)

WEBHOOK_ROUTE = '/' + TOKEN
WEBHOOK_URL = os.environ.get("WEBHOOK_URL") + WEBHOOK_ROUTE

# --- Установка Webhook при старте ---
@app.before_first_request
def setup_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    print(f"WEBHOOK SET: {WEBHOOK_URL}")

@app.route(WEBHOOK_ROUTE, methods=['POST'])
def webhook():
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
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
