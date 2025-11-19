import os
from flask import Flask, request
import telebot
from telebot import types
from telebot.apihelper import ApiTelegramException
from dotenv import load_dotenv

# --- Загрузка переменных окружения ---
load_dotenv()  # автоматически ищет .env в корне проекта

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_HOST = os.getenv("WEBHOOK_URL")
DELIVERY_GROUP_ID = int(os.getenv("DELIVERY_GROUP_ID", 0))
WEBHOOK_ROUTE = f"/{TOKEN}"
WEBHOOK_URL = WEBHOOK_HOST + WEBHOOK_ROUTE

app = Flask(__name__)
bot = telebot.TeleBot(TOKEN)

# --- Глобальные переменные для многошаговой логики ---
user_data = {}

# --- Кнопки меню ---
BUTTON_GET_ADDRESS = "🏠 🇨🇳 Гирифтани адрес ва код"
BUTTON_DELIVERY = "🚚 Доставка"
BUTTON_CALC = "📦 Нархнома"
BUTTON_TRACK = "🔍 Проверка трек-кода"
BUTTON_CONTACT = "📞 Контакты"
BUTTON_TAJIK_ADDR = "🇹🇯 Адрес Душанбе"
BUTTON_PROHIBITED = "Молхои манъшуда"

# --- Установка Webhook ---
def set_webhook():
    try:
        bot.remove_webhook()
        if bot.set_webhook(url=WEBHOOK_URL):
            print(f"WEBHOOK SET: {WEBHOOK_URL}")
            return True
        else:
            print("Не удалось установить Webhook")
            return False
    except Exception as e:
        print(f"Ошибка Webhook: {e}")
        return False

set_webhook()

# --- Flask маршрут для Webhook ---
@app.route(WEBHOOK_ROUTE, methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        try:
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return 'ok', 200
        except Exception as e:
            print(f"Ошибка обработки update: {e}")
            return 'error', 500
    else:
        return 'Not JSON', 403

# --- Функции меню ---
def send_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.row(types.KeyboardButton(BUTTON_GET_ADDRESS), types.KeyboardButton(BUTTON_DELIVERY))
    markup.row(types.KeyboardButton(BUTTON_CALC), types.KeyboardButton(BUTTON_TRACK))
    markup.row(types.KeyboardButton(BUTTON_TAJIK_ADDR), types.KeyboardButton(BUTTON_PROHIBITED))
    markup.row(types.KeyboardButton(BUTTON_CONTACT))
    bot.send_message(chat_id, "Добро пожаловать в TAJ-EXPRESS! 🚚\nВыберите пункт меню:", reply_markup=markup)

# --- Старт и помощь ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    send_main_menu(message.chat.id)

# --- Получение адреса и кода ---
@bot.message_handler(func=lambda m: m.text == BUTTON_GET_ADDRESS)
def get_address(message):
    chat_id = message.chat.id
    msg = bot.send_message(chat_id, "Введите ваше имя:")
    bot.register_next_step_handler(msg, get_name_step)

def get_name_step(message):
    chat_id = message.chat.id
    user_data[chat_id] = {"name": message.text}
    msg = bot.send_message(chat_id, "Введите ваш номер телефона:")
    bot.register_next_step_handler(msg, get_phone_step)

def get_phone_step(message):
    chat_id = message.chat.id
    user_data[chat_id]["phone"] = message.text
    name = user_data[chat_id]["name"]
    phone = user_data[chat_id]["phone"]
    final_address = f"Amin 17590820846 浙江省金华市义乌市 福田三小区80栋二单元305室 {name} {phone}"
    bot.send_message(chat_id, final_address)
    send_main_menu(chat_id)

# --- Доставка заявки ---
@bot.message_handler(func=lambda m: m.text == BUTTON_DELIVERY)
def delivery_start(message):
    chat_id = message.chat.id
    msg = bot.send_message(chat_id, "Введите ваше имя для заявки на доставку:")
    bot.register_next_step_handler(msg, delivery_name_step)

def delivery_name_step(message):
    chat_id = message.chat.id
    user_data[chat_id] = {"delivery_name": message.text}
    msg = bot.send_message(chat_id, "Введите ваш адрес для доставки:")
    bot.register_next_step_handler(msg, delivery_address_step)

def delivery_address_step(message):
    chat_id = message.chat.id
    user_data[chat_id]["delivery_address"] = message.text
    delivery_name = user_data[chat_id]["delivery_name"]
    delivery_address = user_data[chat_id]["delivery_address"]
    delivery_text = (
        f"📦 *НОВАЯ ЗАЯВКА НА ДОСТАВКУ*\n"
        f"👤 Имя: {delivery_name}\n"
        f"📍 Адрес: {delivery_address}\n"
        f"От пользователя: @{message.from_user.username or message.from_user.id}"
    )
    try:
        bot.send_message(DELIVERY_GROUP_ID, delivery_text, parse_mode="Markdown")
        bot.send_message(chat_id, "Ваша заявка на доставку отправлена! ✅")
    except ApiTelegramException as e:
        bot.send_message(chat_id, f"Ошибка отправки заявки: {e}")
    send_main_menu(chat_id)

# --- Расчет стоимости ---
@bot.message_handler(func=lambda m: m.text == BUTTON_CALC)
def calc_start(message):
    msg = bot.send_message(message.chat.id, "Введите вес груза в кг:")
    bot.register_next_step_handler(msg, calc_weight_step)

def calc_weight_step(message):
    try:
        weight = float(message.text.replace(',', '.').strip())
        if weight <= 0:
            raise ValueError
        msg = bot.send_message(message.chat.id, "Введите город отправления:")
        bot.register_next_step_handler(msg, calc_departure_step, weight)
    except ValueError:
        msg = bot.send_message(message.chat.id, "Неверный формат. Введите цифрами (например, 10.5).")
        bot.register_next_step_handler(msg, calc_weight_step)

def calc_departure_step(message, weight):
    departure = message.text.strip()
    msg = bot.send_message(message.chat.id, "Введите город назначения:")
    bot.register_next_step_handler(msg, calc_arrival_step, weight, departure)

def calc_arrival_step(message, weight, departure):
    arrival = message.text.strip()
    price = 500 + weight * 100
    response = (
        f"✅ Расчет готов!\n"
        f"Отправление: {departure}\n"
        f"Назначение: {arrival}\n"
        f"Вес: {weight} кг\n"
        f"Примерная стоимость: {price:.2f} руб.\n"
        f"Для точной стоимости свяжитесь с менеджером."
    )
    bot.send_message(message.chat.id, response)
    send_main_menu(message.chat.id)

# --- Отслеживание трек-кода ---
@bot.message_handler(func=lambda m: m.text == BUTTON_TRACK)
def track_start(message):
    msg = bot.send_message(message.chat.id, "Введите номер для отслеживания (например, TAJ12345):")
    bot.register_next_step_handler(msg, track_step)

def track_step(message):
    number = message.text.strip().upper()
    statuses = {
        "TAJ12345": "В пути, прибытие 25.11.2025.",
        "TAJ67890": "На складе в Москве, готовится к отправке.",
        "TAJ11223": "Доставлен и вручен получателю 15.11.2025."
    }
    status = statuses.get(number, "Груз не найден. Проверьте номер.")
    bot.send_message(message.chat.id, f"Статус груза {number}:\n{status}")
    send_main_menu(message.chat.id)

# --- Контакты ---
@bot.message_handler(func=lambda m: m.text == BUTTON_CONTACT)
def contact(message):
    info = "📞 Служба поддержки: +7 495 123 45 67\nEmail: support@tajexpress.com\nМенеджер: @TajExpressManager"
    bot.send_message(message.chat.id, info)
    send_main_menu(message.chat.id)

# --- Адрес Душанбе ---
@bot.message_handler(func=lambda m: m.text == BUTTON_TAJIK_ADDR)
def dushanbe_address(message):
    info = "🇹🇯 Адрес офиса: пр. Рудаки 123, Бизнес-центр 'Азия'\nТелефон: +992 900 12 34 56"
    bot.send_message(message.chat.id, info)
    send_main_menu(message.chat.id)

# --- Запрещенные товары ---
@bot.message_handler(func=lambda m: m.text == BUTTON_PROHIBITED)
def prohibited(message):
    info = "🚫 Запрещенные товары:\n1. Оружие\n2. Взрывчатые вещества\n3. Наркотики\n..."
    bot.send_message(message.chat.id, info)
    send_main_menu(message.chat.id)

# --- Обработчик всех остальных сообщений ---
@bot.message_handler(func=lambda m: True)
def fallback(message):
    bot.reply_to(message, "Используйте меню или команду /start.")

# --- Запуск Flask для локального теста ---
if __name__ == '__main__':
    print("Приложение запущено в локальном режиме.")
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
