import os
import telebot
from telebot import types
from telebot.apihelper import ApiTelegramException
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not defined.")

bot = telebot.TeleBot(TOKEN, threaded=False)

try:
    DELIVERY_GROUP_ID = int(os.getenv("DELIVERY_GROUP_ID", "0"))
except ValueError:
    DELIVERY_GROUP_ID = 0

# Пользовательские данные временно храним в словаре
user_data = {}

# Трек-коды (для демонстрации)
# Можно позже вручную добавлять в админке
tracking_data = {
    "TAJ12345": "В пути, прибытие 25.11.2025",
    "TAJ54321": "Доставлено, 19.11.2025"
}

# Кнопки меню
BUTTON_DELIVERY = "🚚 Доставка"
BUTTON_ADDRESS = "🇨🇳 Гирифтани адрес ва код"
BUTTON_DUSHANBE = "🇹🇯 Адрес Душанбе"
BUTTON_PRICE_LIST = "📦 Нархнома"
BUTTON_TRACK = "🔍 Санчиши трек-код"
BUTTON_BANNED = "Молхои манъшуда"
BUTTON_CONTACTS = "📞 Контакты"

MAIN_MENU = [
    [BUTTON_DELIVERY],
    [BUTTON_ADDRESS, BUTTON_PRICE_LIST],
    [BUTTON_TRACK, BUTTON_DUSHANBE],
    [BUTTON_BANNED, BUTTON_CONTACTS]
]

def send_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for row in MAIN_MENU:
        markup.add(*[types.KeyboardButton(text) for text in row])
    bot.send_message(chat_id, "Выберите пункт меню:", reply_markup=markup)

# ===== Обработка кнопок =====

@bot.message_handler(func=lambda m: True)
def main_handler(message):
    chat_id = message.chat.id
    text = message.text

    if text == BUTTON_DELIVERY:
        msg = bot.send_message(chat_id, "Номи худро ворид созед:")
        bot.register_next_step_handler(msg, delivery_name_step)
    elif text == BUTTON_ADDRESS:
        bot.send_message(chat_id, "📍 Адрес склада: Душанбе, к Хисор 34")
    elif text == BUTTON_PRICE_LIST:
        bot.send_message(chat_id, "📦 Список тарифов:\n1. Малый груз — 2000 руб.\n2. Средний груз — 4000 руб.\n3. Большой груз — 6000 руб.")
    elif text == BUTTON_TRACK:
        msg = bot.send_message(chat_id, "Введите номер для отслеживания (например, TAJ12345):")
        bot.register_next_step_handler(msg, track_step)
    elif text == BUTTON_DUSHANBE:
        bot.send_message(chat_id, "🇹🇯 Адрес офиса: Душанбе, к Хисор 34\nТелефон: +992 985171732")
    elif text == BUTTON_BANNED:
        bot.send_message(chat_id, "🚫 Запрещенные товары:\n1. 1. Взрывоопасные вещества
2. Аккумуляторы, батареи, магниты, повербанки
3. Продукты питания, семена, саженцы
4. Оружие (в том числе игрушечное), кастеты, ножи
5. Горюче-смазочные материалы, косметика
6. Серебро, золото и аналогичные изделия
7. Д Игрушки с батарейками
8.Часы (включая Apple Watch), наушники и умные гаджеты" )
    elif text == BUTTON_CONTACTS:
        bot.send_message(chat_id, "📞 Служба поддержки: +992985171732\nEmail: \nМенеджер: https://t.me/TAJEXPRESSMANAGER")
    else:
        send_main_menu(chat_id)

# ===== Доставка =====

def delivery_name_step(message):
    chat_id = message.chat.id
    user_data[chat_id] = {"name": message.text}
    msg = bot.send_message(chat_id, "Суроғаи интиқолро ворид кунед:")
    bot.register_next_step_handler(msg, delivery_address_step)

def delivery_address_step(message):
    chat_id = message.chat.id
    user_data[chat_id]["address"] = message.text
    msg = bot.send_message(chat_id, "Рақами телефони худро ворид кунед:")
    bot.register_next_step_handler(msg, delivery_phone_step)

def delivery_phone_step(message):
    chat_id = message.chat.id
    user_data[chat_id]["phone"] = message.text

    data = user_data[chat_id]
    delivery_text = (
        f"📦 *НОВАЯ ЗАЯВКА НА ДОСТАВКУ*\n"
        f"Имя: {data['name']}\n"
        f"Адрес: {data['address']}\n"
        f"Телефон: {data['phone']}"
    )
    try:
        bot.send_message(DELIVERY_GROUP_ID, delivery_text, parse_mode="Markdown")
        bot.send_message(chat_id, "Заявка фиристода шуд. ✅")
    except ApiTelegramException as e:
        bot.send_message(chat_id, f"Ошибка отправки заявки: {e}")
    send_main_menu(chat_id)

# ===== Проверка трек-кода =====

def track_step(message):
    chat_id = message.chat.id
    code = message.text.strip().upper()
    status = tracking_data.get(code, "Трек-код не найден")
    bot.send_message(chat_id, f"Статус груза {code}:\n{status}")
    send_main_menu(chat_id)
