import os
import json
import re
import threading
import time
from telebot import TeleBot, types
from telebot.apihelper import ApiTelegramException
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ================== Настройки ==================
UPDATE_INTERVAL = 5 * 60  # Обновление кэша каждые 5 минут

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ TELEGRAM_BOT_TOKEN не задан!")

GOOGLE_CREDS_PATH = os.getenv(
    "GOOGLE_CREDENTIALS_JSON",
    "/opt/render/secrets/credentials.json"
)

# Проверка, чтобы избежать ошибок при пустом значении
try:
    DELIVERY_GROUP_ID = int(os.getenv("DELIVERY_GROUP_ID", "0"))
except ValueError:
    DELIVERY_GROUP_ID = 0

ADMIN_LOGIN = os.getenv("ADMIN_LOGIN", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "password")

# ================== Телеграм бот ==================
bot = TeleBot(TOKEN, threaded=False)

# ================== Данные пользователей и кэш ==================
user_data = {}
track_cache = {}
user_cache = {} # Кэш пользователей для быстрого доступа

# ================== Подключение к Google Sheets ==================
if not os.path.isfile(GOOGLE_CREDS_PATH):
    raise RuntimeError(f"❌ Файл Google credentials не найден: {GOOGLE_CREDS_PATH}")

with open(GOOGLE_CREDS_PATH, "r") as f:
    creds_dict = json.load(f)

scope = ["https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gc = gspread.authorize(creds)

try:
    # Предполагаем, что sheet1 это лист с треками
    TRACKS_SHEET_NAME = "Tracks" 
    TRACKS_SHEET = gc.open(TRACKS_SHEET_NAME).sheet1 
    # Предполагаем, что лист для пользователей называется Users
    USERS_SHEET_NAME = "Users"
    # Попытка получить лист Users. Если его нет, он будет создан в save_user.
    try:
        USERS_SHEET = gc.open(TRACKS_SHEET_NAME).worksheet(USERS_SHEET_NAME)
    except gspread.WorksheetNotFound:
        USERS_SHEET = None

except Exception as e:
    print(f"❌ Ошибка подключения к таблице: {e}")
    TRACKS_SHEET = None
    USERS_SHEET = None


# ================== Меню ==================
BTN_DELIVERY = "🚚 Доставка"
BTN_ADDRESS = "🇨🇳 Гирифтани адрес ва код"
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

def send_main_menu(chat_id, text="Менюи асосӣ. Лутфан, интихоб кунед:"):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for row in MAIN_MENU:
        markup.add(*[types.KeyboardButton(text) for text in row])
    bot.send_message(chat_id, text, reply_markup=markup)

# ================== START ==================
@bot.message_handler(commands=["start", "help"])
def start_handler(message):
    chat_id = message.chat.id
    welcome_text = (
        "🚀 *TAJEXPRESS* – каргои боваринок ва бехатар барои овардани борхои Шумо!\n\n"
        "📦 Борҳои худро **зуд ва бехатар** фиристед\n"
        "⏱️ Дархостҳоро осон ва зуд иҷро намоед\n"
        "🇨🇳 *Суроғаи қулай дар Чин* барои харидҳои шумо\n\n"
        "Менюи зерро интихоб кунед:"
    )
    bot.send_message(chat_id, welcome_text, parse_mode="Markdown")
    send_main_menu(chat_id)

# ================== Основной обработчик ==================
@bot.message_handler(func=lambda m: True)
def main_handler(message):
    chat_id = message.chat.id
    text = message.text

    if text == BTN_REGISTER:
        msg = bot.send_message(chat_id, "📝 **Барои бақайдгирӣ** лутфан, номи худро (номи пурра) ворид кунед:")
        bot.register_next_step_handler(msg, register_step_name)

    elif text == BTN_DELIVERY:
        msg = bot.send_message(chat_id, "🚚 **Оғози тартиб додани дархости расонидан**.\nЛутфан, номи пурраи гирандаро ворид кунед:")
        bot.register_next_step_handler(msg, delivery_step_name)

    elif text == BTN_ADDRESS:
        msg = bot.send_message(chat_id, "🇨🇳 **Барои гирифтани адреси Чин ва коди мизоҷ**.\nНом ва насаби худро **ТАНҲО бо ҳарфҳои лотинӣ** ворид кунед (масалан, *Ahmad Saidov*):")
        bot.register_next_step_handler(msg, address_step_name)

    elif text == BTN_PRICE_LIST:
        bot.send_message(chat_id,
                         "💰 *Нархномаи хизматрасониҳо:*\n"
                         "• Аз **200кг то 1000кг** — *$1.8$* барои 1 кг\n"
                         "• Аз **0.1кг то 200кг** — *$3.0$* барои 1 кг\n"
                         "Барои тафсилоти бештар бо оператор тамос гиред.",
                         parse_mode="Markdown")

    elif text == BTN_TRACK:
        msg = bot.send_message(chat_id, "🔍 **Барои санҷиши ҳолати бор**.\nЛутфан, *трек-коди* худро ворид кунед:")
        bot.register_next_step_handler(msg, track_step)

    elif text == BTN_DUSHANBE:
        bot.send_message(chat_id, 
                         "🏢 *Адреси мо дар Душанбе:*\n"
                         "🇹🇯 **ш. Душанбе, 103 мкр, бинои 3**\n"
                         "☎️ **Тел:** `+992 985 171 732` (Барои тамос бо мо) \n"
                         "⏰ **Вақти корӣ:** 9:00 - 18:00 (Ду-Шанбе)",
                         parse_mode="Markdown")

    elif text == BTN_BANNED:
        bot.send_message(chat_id,
                         "⚠️ *Рӯйхати маҳсулотҳои манъшуда барои интиқол:*\n"
                         "---"
                         "🔥 1. **Маводҳои тарканда** (аз қабили пиротехника)\n"
                         "🔋 2. **Батареяҳо, аккумуляторҳо, магнитҳо ва повербанкҳо** (дар шакли алоҳида)\n"
                         "🥗 3. **Хӯрокворӣ, тухмӣ ва шинонандаҳо**\n"
                         "🔫 4. **Ҳарбу зарфҳо, кастет ва кордҳо** (ғайриқонунӣ)\n"
                         "⛽ 5. **Маводи сӯзишворӣ, равған ва косметикаи моеъ**\n"
                         "💎 6. **Нуқра, тилло ва маҳсулоти қиматбаҳо**\n"
                         "💧 7. **Моеъҳо, аэрозолҳо ва кимиёвӣ** (дар ҳаҷми калон)\n"
                         "🔞 8. **Ҳама намуд маҳсулотҳои 18+** (маводҳои порнографӣ, бозичаҳои ҷинсӣ ва ғайра)\n\n"
                         "_Лутфан, пеш аз фиристодан, ин рӯйхатро бодиққат хонед._",
                         parse_mode="Markdown")

    elif text == BTN_CONTACTS:
        show_contacts(chat_id)

    else:
        send_main_menu(chat_id, "Ин фармон шинохта нашуд. Лутфан, тугмаи менюро истифода баред.")

# ================== Регистрация ==================
def get_users_sheet():
    global USERS_SHEET
    if USERS_SHEET is None:
        try:
            # Открываем существующую книгу "Tracks"
            book = gc.open(TRACKS_SHEET_NAME)
            # Пытаемся найти лист "Users"
            try:
                USERS_SHEET = book.worksheet(USERS_SHEET_NAME)
            except gspread.WorksheetNotFound:
                # Если не найден, создаем
                USERS_SHEET = book.add_worksheet(title=USERS_SHEET_NAME, rows="1000", cols="3")
                USERS_SHEET.append_row(["ChatID", "Name", "Phone"])
            return USERS_SHEET
        except Exception as e:
            print(f"❌ Ошибка получения/создания листа Users: {e}")
            return None
    return USERS_SHEET

def register_step_name(message):
    chat_id = message.chat.id
    user_data[chat_id] = {"name": message.text.strip()}
    msg = bot.send_message(chat_id, "📞 Акнун, лутфан, рақами телефони худро (дар формати +992 XXX XX XX XX) ворид кунед:")
    bot.register_next_step_handler(msg, register_step_phone)

def register_step_phone(message):
    chat_id = message.chat.id
    phone = message.text.strip()
    user_data[chat_id]["phone"] = phone
    threading.Thread(target=save_user, args=(chat_id,), daemon=True).start()
    bot.send_message(chat_id,
                     f"✅ **Бақайдгирии шумо бо муваффақият анҷом ёфт!**\n"
                     f"👤 Ном: *{user_data[chat_id]['name']}*\n"
                     f"📞 Тел: *{phone}*\n\n"
                     "Шумо метавонед аз менюи асосӣ хизматрасонии лозимаро интихоб кунед.",
                     parse_mode="Markdown")
    send_main_menu(chat_id)

def save_user(chat_id):
    try:
        users_sheet = get_users_sheet()
        if users_sheet:
            users_sheet.append_row([chat_id, user_data[chat_id]["name"], user_data[chat_id]["phone"]])
            # Обновление кэша пользователей
            user_cache[chat_id] = {"Name": user_data[chat_id]["name"], "Phone": user_data[chat_id]["phone"]}
    except Exception as e:
        print(f"❌ Ошибка сохранения пользователя в Sheets: {e}")

# ================== Доставка ==================
def delivery_step_name(message):
    chat_id = message.chat.id
    user_data[chat_id] = {"name": message.text.strip()}
    msg = bot.send_message(chat_id, "📍 Лутфан, адреси пурраи расониданро (кӯча, хона, паҳлӯи чӣ) ворид кунед:")
    bot.register_next_step_handler(msg, delivery_step_address)

def delivery_step_address(message):
    chat_id = message.chat.id
    user_data[chat_id]["address"] = message.text.strip()
    msg = bot.send_message(chat_id, "📞 Лутфан, рақами телефони гирандаро ворид кунед:")
    bot.register_next_step_handler(msg, delivery_step_phone)

def delivery_step_phone(message):
    chat_id = message.chat.id
    user_data[chat_id]["phone"] = message.text.strip()
    data = user_data[chat_id]
    
    delivery_text = (
        "📦 *Новая заявка на доставку*\n"
        "---"
        f"👤 **Имя получателя:** {data['name']}\n"
        f"📍 **Адрес:** {data['address']}\n"
        f"📞 **Телефон:** {data['phone']}"
    )
    
    try:
        if DELIVERY_GROUP_ID != 0:
            bot.send_message(DELIVERY_GROUP_ID, delivery_text, parse_mode="Markdown")
        bot.send_message(chat_id, "✅ **Заявка на доставку принята!**\nВ ближайшее время с Вами свяжется наш менеджер.", parse_mode="Markdown")
    except ApiTelegramException as e:
        error_msg = f"❌ Ошибка отправки заявки в группу (ID: {DELIVERY_GROUP_ID}). Проверьте настройки: {e}"
        print(error_msg)
        bot.send_message(chat_id, f"❌ Ошибка отправки заявки. Пожалуйста, попробуйте позже или свяжитесь с нами напрямую.")
    send_main_menu(chat_id)

# ================== Адрес ==================
def address_step_name(message):
    chat_id = message.chat.id
    name = message.text.strip()
    # Проверка на латиницу и отсутствие спецсимволов
    if not re.match(r"^[A-Za-z\s]+$", name):
        msg = bot.send_message(chat_id, "❌ **Хатогӣ!** Танҳо ҳарфҳои лотинӣ ва фосилаҳоро истифода баред. Лутфан, дубора ворид кунед:")
        bot.register_next_step_handler(msg, address_step_name)
        return
        
    user_data[chat_id] = {"name": name}
    msg = bot.send_message(chat_id, "📞 Лутфан, рақами телефони худро (барои робитаи мо бо шумо дар ҳолати зарурӣ) ворид кунед:")
    bot.register_next_step_handler(msg, address_step_phone)

def address_step_phone(message):
    chat_id = message.chat.id
    phone = message.text.strip()
    user_data[chat_id]["phone"] = phone
    data = user_data[chat_id]
    
    # Формат адреса: [ВАШЕ ИМЯ ЛАТИНИЦЕЙ] [НОМЕР ТЕЛЕФОНА КАРГО] 浙江省 金华市 义乌市 福田三小区80栋二单元305室 [ВАШЕ ИМЯ ЛАТИНИЦЕЙ] [ВАШ ТЕЛЕФОН]
    full_address = (
        f"✅ **Адреси пурра барои харидҳо дар Чин:**\n"
        f"Номи мизоҷ: *{data['name']}*\n"
        f"Телефон: *{data['phone']}*\n"
        f"---"
        f"📝 **Барои истифода дар сайтҳои Чин:**\n"
        f"`{data['name']} 17590820846 浙江省 金华市 义乌市 福田三小区80栋二单元305室 {data['name']} {data['phone']}`"
    )
    
    bot.send_message(chat_id, full_address, parse_mode="Markdown")
    send_main_menu(chat_id)

# ================== Трек-код ==================
def normalize_track(code: str) -> str:
    # Удаляем пробелы и неалфавитно-цифровые символы, переводим в верхний регистр
    return re.sub(r"[^A-Z0-9]", "", str(code).upper())

def track_step(message):
    chat_id = message.chat.id
    code = normalize_track(message.text)
    
    # Поиск трек-кода в кэше
    row = track_cache.get(code)
    
    if row:
        # Убедитесь, что заголовки в вашем Google Sheet соответствуют этим ключам!
        # Пример: Track, Status, Date, Name, ClientCode, Weight(kg), Price/kg, Total
        info_text = (
            f"🔍 **Маълумот оид ба бор (Трек-код: {row.get('Track','-')}):**\n"
            f"---"
            f"👤 **Номи мизоҷ:** {row.get('Name','-')}\n"
            f"📞 **Коди мизоҷ (ID):** {row.get('ClientCode','-')}\n"
            f"📦 **Ҳолати бор:** *{row.get('Status','-')}*\n"
            f"📅 **Санаи воридшавӣ:** {row.get('Date','-')}\n"
            f"⚖ **Вазн (кг):** {row.get('Weight(kg)','-')}\n"
            f"💰 **Нарх/кг:** {row.get('Price/kg','-')}\n"
            f"💵 **Арзиши умумӣ:** {row.get('Total','-')}"
        )
    else:
        info_text = (
            "❌ **Трек-код ёфт нашуд.**\n\n"
            "Лутфан, тафтиш кунед, ки трек-код дуруст аст ё бо оператори мо тамос гиред, агар шумо боварӣ дошта бошед, ки бор фиристода шудааст."
        )
        
    bot.send_message(chat_id, info_text, parse_mode="Markdown")
    send_main_menu(chat_id)

# ================== Кэш треков (Коди навшуда) ==================
def load_cache():
    global track_cache
    if not TRACKS_SHEET:
        print("[ERROR] Лист для треков не доступен.")
        return

    try:
        # Истифодаи get_all_records() бо тахмини сарлавҳаи дуруст:
        records = TRACKS_SHEET.get_all_records()
        new_track_cache = {}
        
        # Калидҳо дар Sheet, ки шумо пешниҳод кардед, агар онҳо дуруст ҷудо шуда бошанд:
        # АГАР ИСТИФОДА ШАВАД: Track, Status, Date, Name, ClientCode, Weight(kg), Price/kg, Total
        # АГАР ЯКҶОЯ БОШАД (мушкили шумо): 
        # Мо бояд ба сутуни аслии трек-код муроҷиат кунем.
        
        # Эҳтимол дорад, ки gspread танҳо як калиди бузурги якҷояро мебинад.
        # Аз ин рӯ, тағйир додани сарлавҳаҳо дар Google Sheet (Қадами 1) ҳатмист.
        
        # Агар шумо сарлавҳаҳоро мувофиқи Қадами 1 тағйир дода бошед, ин код дуруст кор мекунад:
        TRACK_KEY = 'Track'

        for r in records:
            if TRACK_KEY in r and r[TRACK_KEY]:
                key = normalize_track(r[TRACK_KEY])
                new_track_cache[key] = r
            
        track_cache = new_track_cache
        
        # ... (Коди боқимондаи load_cache барои user_cache) ...

    except Exception as e:
        print(f"[ERROR] Ошибка загрузки данных из Google Sheets: {e}")
        

def update_track_cache_periodically():
    while True:
        try:
            load_cache()
            print(f"[INFO] Кэш обновлён. Треков: {len(track_cache)}, Пользователей: {len(user_cache)}")
        except Exception as e:
            print(f"[ERROR] Ошибка обновления кэша: {e}")
        time.sleep(UPDATE_INTERVAL)

threading.Thread(target=update_track_cache_periodically, daemon=True).start()

# ================== Контакты ==================
def show_contacts(chat_id):
    text = "📞 *Барои тамос бо TAJEXPRESS, яке аз рақамҳои зеринро интихоб кунед:*\n\n"
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    # 1. Номер Zubaidullo
    markup.add(types.InlineKeyboardButton("📱 Менеҷер: +992 985 171 732", url="https://t.me/zubaidullo_tjk"))
    markup.add(types.InlineKeyboardButton("📱 Менеҷер: +992 933 055 707", url="https://t.me/zubaidullo_tjk"))
    
    # 2. Номер Fayoz
    markup.add(types.InlineKeyboardButton("📱 Менеҷер: +992 007 282 626", url="https://t.me/Fayoz_7707"))
    
    # 3. Канал Telegram
    markup.add(types.InlineKeyboardButton("📢 Канали расмии Telegram", url="https://t.me/TAJEXPRESSCARGO"))
    
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

# ================== Запуск бота ==================
if __name__ == "__main__":
    print("Бот запущен...")
    load_cache() # Первоначальная загрузка
    bot.infinity_polling()
