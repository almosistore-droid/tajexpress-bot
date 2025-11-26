#!/usr/bin/env python3
# coding: utf-8
import os
import json
import time
import threading
import re
from telebot import TeleBot, types
from telebot.apihelper import ApiTelegramException
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ------------- Конфигурация -------------
UPDATE_INTERVAL = 5 * 60  # интервал обновления кэша (сек)
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN не задан!")

# Путь до JSON с ключами сервисного аккаунта (через .env)
GOOGLE_CREDS_PATH = os.getenv("GOOGLE_CREDENTIALS_JSON", "/var/www/bot/taj-express-478705-b4ad615749f9.json")

try:
    DELIVERY_GROUP_ID = int(os.getenv("DELIVERY_GROUP_ID", "0"))
except ValueError:
    DELIVERY_GROUP_ID = 0

ADMINS = [1324431208]  # поменяй на свои id админов при необходимости

# ------------- Инициализация бота -------------
bot = TeleBot(TOKEN, threaded=True)

# ------------- Google Sheets: подключение -------------
def init_gsheets(creds_path):
    """Возвращает объект клиента gspread или None + текст ошибки"""
    try:
        with open(creds_path, "r") as f:
            creds_dict = json.load(f)
    except Exception as e:
        print(f"[ERROR] Не удалось открыть credentials JSON: {e}")
        return None, f"Cannot open credentials file: {e}"

    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        gc = gspread.authorize(creds)
        return gc, None
    except Exception as e:
        print(f"[ERROR] Ошибка авторизации gspread: {e}")
        return None, f"gspread auth error: {e}"

gc, err = init_gsheets(GOOGLE_CREDS_PATH)
if not gc:
    print(f"[WARN] Google Sheets не инициализирован: {err}")

# пробуем открыть лист Tracks
SHEET_NAME = "Tracks"
sheet = None
if gc:
    try:
        sheet = gc.open(SHEET_NAME).sheet1
        print(f"[INFO] Успешно открыт лист: {SHEET_NAME}")
    except Exception as e:
        print(f"[WARN] Не удалось открыть таблицу '{SHEET_NAME}': {e}")
        sheet = None

# ------------- Внутренние структуры -------------
track_cache = {}   # {normalized_track: row_dict}
user_cache = {}    # {chat_id: {"Name": .., "Phone": .., "row": int?}}
user_data = {}     # временные данные при step handlers

# ------------- Утилиты -------------
def normalize_track_key(s: str) -> str:
    """Нормализует трек-код: удаляет пробелы, дефисы, оставляет A-Z0-9"""
    if s is None:
        return ""
    s = str(s).upper()
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s

def normalize_col_name(k: str) -> str:
    """Нормализация заголовков колонок (опционально)"""
    if not isinstance(k, str):
        return k
    return k.strip()

# ------------- Загрузка кэша -------------
def load_cache_once():
    global track_cache, user_cache
    if not sheet:
        print("[WARN] sheet не доступен — кэш не загружен")
        return
    try:
        records = sheet.get_all_records()
        new_cache = {}
        for r in records:
            if "Track" in r and r["Track"]:
                key = normalize_track_key(r["Track"])
                new_cache[key] = r
        track_cache = new_cache
        print(f"[INFO] Загружено треков в кэш: {len(track_cache)}")
    except Exception as e:
        print(f"[ERROR] load_cache_once: {e}")

    # users sheet (опционально)
    try:
        users_sheet = gc.open(SHEET_NAME).worksheet("Users")
        users = users_sheet.get_all_records()
        uc = {}
        for idx, row in enumerate(users, start=2):  # предполагаем заголовок на первой строке
            try:
                chatid = int(row.get("ChatID"))
                uc[chatid] = {"Name": row.get("Name"), "Phone": row.get("Phone"), "row": idx}
            except Exception:
                continue
        user_cache = uc
        print(f"[INFO] Загружено пользователей в кэш: {len(user_cache)}")
    except Exception:
        # users лист может отсутствовать — это норм
        pass

def update_cache_periodically():
    while True:
        try:
            load_cache_once()
        except Exception as e:
            print(f"[ERROR] update_cache_periodically: {e}")
        time.sleep(UPDATE_INTERVAL)

# запускаем один раз и стартуем фоновый поток
load_cache_once()
threading.Thread(target=update_cache_periodically, daemon=True).start()

# ------------- Клавиатура -------------
BTN_DELIVERY = "🚚 Доставка"
BTN_ADDRESS = "🇨🇳 Гирифтани адрес"
BTN_DUSHANBE = "🇹🇯 Адрес Душанбе"
BTN_PRICE_LIST = "📦 Нархнома"
BTN_TRACK = "🔍 Проверка трек-кода"
BTN_BANNED = "🚫 Молхои манъшуда"
BTN_CONTACTS = "📞 Контакты"
BTN_REGISTER = "📝 Регистрация"

MAIN_MENU = [
    [BTN_REGISTER],
    [BTN_DELIVERY, BTN_ADDRESS],
    [BTN_TRACK, BTN_DUSHANBE],
    [BTN_PRICE_LIST, BTN_BANNED],
    [BTN_CONTACTS]
]

def send_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for row in MAIN_MENU:
        markup.add(*[types.KeyboardButton(text) for text in row])
    bot.send_message(chat_id, "Меню:", reply_markup=markup)

# ------------- Хендлеры команд -------------
@bot.message_handler(commands=["start", "help"])
def start_handler(message):
    chat_id = message.chat.id
    welcome_text = (
        "🚀 TAJEXPRESS – каргои боваринок ва бехатар барои овардани борхои Шумо!\n\n"
        "📦 Борҳои худро зуд ва бехатар фиристед\n"
        "⏱️ Дархостҳоро осон ва зуд иҷро намоед\n"
        "🇨🇳 Суроғаи қулай дар Чин барои харидҳои шумо\n\n"
        "Менюи зерро интихоб кунед:"
    )
    bot.send_message(chat_id, welcome_text)
    send_main_menu(chat_id)

# ---------- Админ: добавить трек (через /addtrack) ----------
@bot.message_handler(commands=["addtrack"])
def cmd_addtrack(message):
    if message.from_user.id not in ADMINS:
        bot.send_message(message.chat.id, "❌ Доступ запрещен.")
        return
    msg = bot.send_message(message.chat.id, "Введите трек-код (например: 464868220821910):")
    bot.register_next_step_handler(msg, admin_addtrack_step_get_code)

def admin_addtrack_step_get_code(message):
    chat_id = message.chat.id
    code = message.text.strip()
    if not code:
        bot.send_message(chat_id, "Код пустой — отмена.")
        return
    # сохраняем временно
    user_data[chat_id] = {"new_track_code": code}
    msg = bot.send_message(chat_id, f"Введите статус для трек-кода {code}:")
    bot.register_next_step_handler(msg, admin_addtrack_step_get_status)

def admin_addtrack_step_get_status(message):
    chat_id = message.chat.id
    if chat_id not in user_data or "new_track_code" not in user_data[chat_id]:
        bot.send_message(chat_id, "Ошибка состояния — начните /addtrack заново.")
        return
    code = user_data[chat_id]["new_track_code"]
    status = message.text.strip()
    # сохраняем в Google Sheets
    if not sheet:
        bot.send_message(chat_id, "⚠ Таблица не подключена. Проверьте настройки.")
        return
    try:
        normalized = normalize_track_key(code)
        # пробуем найти существующий трек
        try:
            cell = sheet.find(code)
        except Exception:
            cell = None
        if cell:
            sheet.update_cell(cell.row, cell.col + 1, status)  # если структура не та — можно заменить
            bot.send_message(chat_id, f"✅ Трек {code} обновлён (обновлён статус).")
        else:
            # добавляем новую строку (Track, Status)
            sheet.append_row([code, status])
            bot.send_message(chat_id, f"✅ Трек {code} добавлен.")
        # Обновляем кэш сразу
        load_cache_once()
    except Exception as e:
        bot.send_message(chat_id, f"⚠ Ошибка при работе с таблицей: {e}")
    finally:
        user_data.pop(chat_id, None)

# ------------- Регистрация -------------
@bot.message_handler(func=lambda m: m.text == BTN_REGISTER)
def handle_register_start(message):
    chat_id = message.chat.id
    msg = bot.send_message(chat_id, "Номи худро ворид кунед:")
    bot.register_next_step_handler(msg, register_step_name)

def register_step_name(message):
    chat_id = message.chat.id
    user_data[chat_id] = {"name": message.text}
    msg = bot.send_message(chat_id, "Рақами телефони худро ворид кунед:")
    bot.register_next_step_handler(msg, register_step_phone)

def register_step_phone(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        bot.send_message(chat_id, "Ошибка состояния. Попробуйте снова.")
        return
    user_data[chat_id]["phone"] = message.text
    # Сохраняем асинхронно
    threading.Thread(target=save_user_to_sheet, args=(chat_id,), daemon=True).start()
    bot.send_message(chat_id, f"✅ Регистрация завершена!\nИмя: {user_data[chat_id]['name']}\nТел: {user_data[chat_id]['phone']}")
    send_main_menu(chat_id)

def save_user_to_sheet(chat_id):
    try:
        users_sheet = gc.open(SHEET_NAME).worksheet("Users")
    except Exception:
        users_sheet = None

    try:
        if users_sheet is None:
            users_sheet = gc.open(SHEET_NAME).add_worksheet(title="Users", rows="1000", cols="3")
            users_sheet.append_row(["ChatID", "Name", "Phone"])

        # если уже есть — обновляем
        if chat_id in user_cache:
            row = user_cache[chat_id].get("row")
            if row:
                users_sheet.update(f"B{row}", user_data[chat_id]["name"])
                users_sheet.update(f"C{row}", user_data[chat_id]["phone"])
        else:
            users_sheet.append_row([chat_id, user_data[chat_id]["name"], user_data[chat_id]["phone"]])
        # обновим локальный кэш
        user_cache[chat_id] = {"Name": user_data[chat_id]["name"], "Phone": user_data[chat_id]["phone"]}
    except Exception as e:
        print(f"[ERROR] save_user_to_sheet: {e}")

# ------------- Доставка -------------
@bot.message_handler(func=lambda m: m.text == BTN_DELIVERY)
def handle_delivery_start(message):
    chat_id = message.chat.id
    msg = bot.send_message(chat_id, "Номи худро ворид кунед:")
    bot.register_next_step_handler(msg, delivery_step_name)

def delivery_step_name(message):
    chat_id = message.chat.id
    user_data[chat_id] = {"name": message.text}
    msg = bot.send_message(chat_id, "Суроғаро ворид кунед:")
    bot.register_next_step_handler(msg, delivery_step_address)

def delivery_step_address(message):
    chat_id = message.chat.id
    user_data[chat_id]["address"] = message.text
    msg = bot.send_message(chat_id, "Рақами телефони худро ворид кунед:")
    bot.register_next_step_handler(msg, delivery_step_phone)

def delivery_step_phone(message):
    chat_id = message.chat.id
    user_data[chat_id]["phone"] = message.text
    data = user_data[chat_id]
    delivery_text = f"📦 *НОВАЯ ЗАЯВКА НА ДОСТАВКУ*\nИмя: {data['name']}\nАдрес: {data['address']}\nТелефон: {data['phone']}"
    try:
        if DELIVERY_GROUP_ID:
            bot.send_message(DELIVERY_GROUP_ID, delivery_text, parse_mode="Markdown")
        bot.send_message(chat_id, "Заявка принята ✅")
    except ApiTelegramException as e:
        bot.send_message(chat_id, f"Ошибка отправки: {e}")
    finally:
        user_data.pop(chat_id, None)
        send_main_menu(chat_id)

# ------------- Адрес (Китай) -------------
@bot.message_handler(func=lambda m: m.text == BTN_ADDRESS)
def handle_address_start(message):
    chat_id = message.chat.id
    msg = bot.send_message(chat_id, "Номи худро ворид кунед (Танҳо ҳарфҳои англисӣ):")
    bot.register_next_step_handler(msg, address_step_name)

def address_step_name(message):
    chat_id = message.chat.id
    if not message.text.isascii():
        msg = bot.send_message(chat_id, "❌ Танҳо бо ҳарфҳои англисӣ нависед!")
        bot.register_next_step_handler(msg, address_step_name)
        return
    user_data[chat_id] = {"name": message.text}
    msg = bot.send_message(chat_id, "Рақами телефони худро ворид кунед:")
    bot.register_next_step_handler(msg, address_step_phone)

def address_step_phone(message):
    chat_id = message.chat.id
    user_data[chat_id]["phone"] = message.text
    data = user_data[chat_id]
    full_address = f"{data['name']} 17590820846 浙江省 金华市 义乌市 福田三小区80栋二单元305室 {data['name']} {data['phone']}"
    bot.send_message(chat_id, full_address)
    user_data.pop(chat_id, None)
    send_main_menu(chat_id)

# ------------- Прайс / Другое -------------
@bot.message_handler(func=lambda m: m.text == BTN_PRICE_LIST)
def handle_price(message):
    bot.send_message(message.chat.id,
                     "📦 Нархнома:\n• Аз 200кг то 1000кг — 1.8$\n• Аз 0.1кг то 200кг — 3$")
    send_main_menu(message.chat.id)

@bot.message_handler(func=lambda m: m.text == BTN_DUSHANBE)
def handle_dushanbe(message):
    bot.send_message(message.chat.id, "🇹🇯 Душанбе, 103 мкр \nТел: +992 985171732")
    send_main_menu(message.chat.id)

@bot.message_handler(func=lambda m: m.text == BTN_BANNED)
def handle_banned(message):
    bot.send_message(message.chat.id,
                     bot.send_message(chat_id,
                         "⚠️ Маҳсулотҳои манъшуда:\n"
                         "🔥 1. Маводҳои тарканда\n"
                         "🔋 2. Батареяҳо, аккумуляторҳо, магнитҳо ва повербанкҳо\n"
                         "🥗 3. Хӯрокворӣ, тухмӣ ва шинонандаҳо\n"
                         "🔫 4. Ҳарбу зарфҳо (аз ҷумла бозичаҳо), кастет ва кордҳо\n"
                         "⛽ 5. Маводи сӯзишворӣ, равған ва косметика\n"
                         "💎 6. Нуқра, тилло ва маҳсулоти қиматбаҳо\n"
                         "💧 7. Моеъҳо, аэрозолҳо ва моддаҳои кимиёвӣ\n")
    send_main_menu(message.chat.id)

@bot.message_handler(func=lambda m: m.text == BTN_CONTACTS)
def handle_contacts(message):
    show_contacts(message.chat.id)
    send_main_menu(message.chat.id)

def show_contacts(chat_id):
    text = "📞 *Ракамхо мо*\n\n"
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("📱 +992 985 171 732", url="https://t.me/zubaidullo_tjk"))
    markup.add(types.InlineKeyboardButton("📱 +992 933 055 707", url="https://t.me/zubaidullo_tjk"))
    markup.add(types.InlineKeyboardButton("📱 +992 007 282 626", url="https://t.me/Fayoz_7707"))
    markup.add(types.InlineKeyboardButton("📢 Канал Telegram", url="https://t.me/TAJEXPRESSCARGO"))
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

# ------------- Проверка трек-кода -------------
@bot.message_handler(func=lambda m: m.text == BTN_TRACK)
def handle_track_start(message):
    chat_id = message.chat.id
    msg = bot.send_message(chat_id, "Треккоди худро равон кунед:")
    bot.register_next_step_handler(msg, track_step)

def track_step(message):
    chat_id = message.chat.id
    code = normalize_track(message.text)

    row = track_cache.get(code)
    if row:
        info_text = (
            f"🔢 Трек-код: {row.get('Track', '-')}\n"
            f"📦 Статус: {row.get('Status', '-')}\n"
            f"📅 Дата: {row.get('Date', '-')}\n"
            f"👤 Имя клиента: {row.get('Name', '-')}\n"
            f"📞 Код клиента: {row.get('ClientCode', '-')}\n"
            f"⚖ Вес: {row.get('Weight(kg)', '-')}\n"
            f"💰 Цена/кг: {row.get('Price/kg', '-')}\n"
            f"💵 Всего: {row.get('Total', '-')}"
        )
    else:
        info_text = "❌ Трек-код не найден. Проверьте номер и попробуйте ещё раз."

    bot.send_message(chat_id, info_text)
    send_main_menu(chat_id)

# ------------- Универсальный хендлер (последний) -------------
@bot.message_handler(func=lambda m: True)
def fallback_handler(message):
    # Отправляем главное меню при неизвестных сообщениях
    send_main_menu(message.chat.id)

# ------------- Запуск -------------
if __name__ == "__main__":
    print("Бот запущен (polling)...")
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except KeyboardInterrupt:
        print("Выход по Ctrl+C")
    except Exception as e:
        print(f"[FATAL] bot.infinity_polling: {e}")
