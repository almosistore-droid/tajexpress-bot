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
user_cache = {}

# ================== Подключение к Google Sheets ==================
if not os.path.isfile(GOOGLE_CREDS_PATH):
    # Агар файл ёфт нашавад, кодро қатъ мекунад
    raise RuntimeError(f"❌ Файл Google credentials не найден: {GOOGLE_CREDS_PATH}")

try:
    with open(GOOGLE_CREDS_PATH, "r") as f:
        creds_dict = json.load(f)
except Exception as e:
    raise RuntimeError(f"❌ Ошибка чтения файла credentials.json: {e}")


scope = ["https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gc = gspread.authorize(creds)

# --- САНҶИШИ ИМКОНИЯТИ ПАЙВАСТШАВӢ ---
TRACKS_SHEET = None
USERS_SHEET = None
TRACKS_SHEET_NAME = "Tracks" 
USERS_SHEET_NAME = "Users"

try:
    # Предполагаем, что sheet1 это лист с треками
    TRACKS_SHEET = gc.open(TRACKS_SHEET_NAME).sheet1 
    try:
        USERS_SHEET = gc.open(TRACKS_SHEET_NAME).worksheet(USERS_SHEET_NAME)
    except gspread.WorksheetNotFound:
        USERS_SHEET = None
except Exception as e:
    print(f"❌ Ошибка подключения к таблице Google Sheets: {e}. Проверьте дастрасӣ!")
# ---------------------------------------------------

# ================== Меню ==================
BTN_DELIVERY = "🚚 Доставка"
BTN_ADDRESS = "🇨🇳 Гирифтани адрес ва код"
BTN_DUSHANBE = "🇹🇯 Адрес Душанбе"
BTN_PRICE_LIST = "📦 Нархнома"
BTN_TRACK = "🔍 Проверка трек-кода"
BTN_BANNED = "🚫 Молхои манъшуда"
BTN_CONTACTS = "📞 Контакты"
BTN_REGISTER = "📝 Регистрация"
# ТУГМАИ НАВ:
BTN_ABOUT_US = "ℹ️ Информация о нас"

MAIN_MENU = [
    [BTN_REGISTER],
    [BTN_DELIVERY, BTN_ADDRESS],
    [BTN_TRACK, BTN_DUSHANBE],
    [BTN_PRICE_LIST, BTN_BANNED],
    # ТУГМАИ НАВ ИЛОВА ШУД
    [BTN_CONTACTS, BTN_ABOUT_US] 
]
# ... (Коди send_main_menu бетағйир мемонад)

def send_main_menu(chat_id, text=""): # <--- Матн барои менюи асосӣ нест карда шуд
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for row in MAIN_MENU:
        # Истифодаи button_text барои пешгирии муноқишаи номҳо
        markup.add(*[types.KeyboardButton(button_text) for button_text in row])
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
# ... (дар дохили def main_handler(message):)

    elif text == BTN_CONTACTS:
        show_contacts(chat_id)

    # ОБРАБОТЧИК ТУГМАИ НАВ
    elif text == BTN_ABOUT_US:
        show_about_us(chat_id)
        
    else:
    if text == BTN_REGISTER:
        msg = bot.send_message(chat_id, "📝 **Барои бақайдгирӣ** лутфан, номи худро ворид кунед:")
        bot.register_next_step_handler(msg, register_step_name)

    elif text == BTN_DELIVERY:
        msg = bot.send_message(chat_id, "🚚 Лутфан, номи пурраи гирандаро ворид кунед:")
        bot.register_next_step_handler(msg, delivery_step_name)

    elif text == BTN_ADDRESS:
        msg = bot.send_message(chat_id, "🇨🇳 **Барои гирифтани адреси Чин ва коди мизоҷ**.\nНом худро **ТАНҲО бо ҳарфҳои лотинӣ** ворид кунед (масалан, *Ahmad*):")
        bot.register_next_step_handler(msg, address_step_name)

    elif text == BTN_PRICE_LIST:
        bot.send_message(chat_id,
                          "💰 *Нархномаи хизматрасониҳо:*\n"
                          "• Аз **200кг то 1000кг** — *$1.8$* барои 1 кг\n"
                          "• Аз **0.1кг то 200кг** — *$3.0$* барои 1 кг\n"
                          "Барои тафсилоти бештар бо оператор тамос гиред.",
                          parse_mode="Markdown")

    elif text == BTN_TRACK:
        # ЛОГИКАИ НАВ: ФИРИСТОДАНИ ССЫЛКА БА ҶОИ ҶУСТУҶӮ
        track_link = "https://t.me/TAJEXPRESSTRACCOD" 
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("🔍 Барои тафтиши треккод ворид шавед", url=track_link))
        
        track_text = (
            "🔍 Барои тафтиши трек-коди худ, лутфан ба канали мо ворид шавед.\n\n"
            "Ба тугмаи зерин пахш кунед:"
        )

        bot.send_message(chat_id, track_text, reply_markup=markup, parse_mode="Markdown")
        
    elif text == BTN_DUSHANBE:
        bot.send_message(chat_id, 
                          "🏢 *Адреси мо дар Душанбе:*\n"
                          "🇹🇯 **ш. Душанбе, 103 мкр, бинои 34**\n"
                          "☎️ **Тел:** `+992 985 171 732` (Барои тамос бо мо) \n"
                          "⏰ **Вақти корӣ:** 9:00 - 18:00 (Душанбе)",
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
        # Паёми хатогӣ бо менюи нав
        bot.send_message(chat_id, "Ин фармон шинохта нашуд. Лутфан, тугмаи менюро истифода баред.")
        send_main_menu(chat_id)


# ================== Регистрация ==================
def get_users_sheet():
    global USERS_SHEET
    if USERS_SHEET is None:
        try:
            book = gc.open(TRACKS_SHEET_NAME)
            try:
                USERS_SHEET = book.worksheet(USERS_SHEET_NAME)
            except gspread.WorksheetNotFound:
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
    msg = bot.send_message(chat_id, "📞 Рақами телефони худро (дар формати +992 XXX XX XX XX) ворид кунед:")
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
            user_cache[chat_id] = {"Name": user_data[chat_id]["name"], "Phone": user_data[chat_id]["phone"]}
    except Exception as e:
        print(f"❌ Ошибка сохранения пользователя в Sheets: {e}")

# ================== Доставка ==================
def delivery_step_name(message):
    chat_id = message.chat.id
    user_data[chat_id] = {"name": message.text.strip()}
    msg = bot.send_message(chat_id, "📍 Лутфан, адреси пурраи худро ворид кунед:")
    bot.register_next_step_handler(msg, delivery_step_address)

def delivery_step_address(message):
    chat_id = message.chat.id
    user_data[chat_id]["address"] = message.text.strip()
    msg = bot.send_message(chat_id, "📞 Лутфан, рақами телефонро ворид кунед:")
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
    if not re.match(r"^[A-Za-z\s]+$", name):
        msg = bot.send_message(chat_id, "❌ **Хатогӣ!** Танҳо ҳарфҳои лотинӣ истифода баред. Лутфан, дубора ворид кунед:")
        bot.register_next_step_handler(msg, address_step_name)
        return
        
    user_data[chat_id] = {"name": name}
    msg = bot.send_message(chat_id, "📞 Лутфан, рақами телефони худро ворид кунед:")
    bot.register_next_step_handler(msg, address_step_phone)

def address_step_phone(message):
    chat_id = message.chat.id
    phone = message.text.strip()
    user_data[chat_id]["phone"] = phone
    data = user_data[chat_id]
    
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

# ================== Трек-код (Нормализатсия барои кэш) ==================
def normalize_track(code: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(code).upper())

# ================== Кэш треков ==================
# Ин номҳо бояд 100% бо сарлавҳаҳои сатри аввали Sheets мувофиқат кунанд!
# Барои ин версия, ин бахш фаъол аст, аммо функсияи track_step нест.
TRACK_KEY_NAME = 'Track' 

def load_cache():
    global track_cache
    if not TRACKS_SHEET:
        print("[ERROR] Лист для треков не доступен. Проверьте подключение и имя листа.")
        return
        
    try:
        # gspread.get_all_records() использует первую строку как заголовки.
        records = TRACKS_SHEET.get_all_records()
        new_track_cache = {}
        
        for r in records:
            if TRACK_KEY_NAME in r and r[TRACK_KEY_NAME]:
                key = normalize_track(r[TRACK_KEY_NAME])
                new_track_cache[key] = r
            
        global track_cache
        track_cache = new_track_cache
        
        # ... (Код для user_cache, остаётся без изменений) ...
        users_sheet = get_users_sheet()
        if users_sheet:
            users_records = users_sheet.get_all_records()
            new_user_cache = {}
            for u in users_records:
                 if "ChatID" in u and u["ChatID"]:
                    try:
                        chat_id = int(u["ChatID"])
                        new_user_cache[chat_id] = {"Name": u.get("Name", ""), "Phone": u.get("Phone", "")}
                    except ValueError:
                        continue
            global user_cache
            user_cache = new_user_cache
        
        print(f"[INFO] Кэш обновлён. Треков: {len(track_cache)}, Пользователей: {len(user_cache)}")
        
    except Exception as e:
        print(f"[ERROR] Ошибка загрузки данных из Google Sheets: {e}")

def update_track_cache_periodically():
    while True:
        try:
            load_cache()
        except Exception as e:
            print(f"[ERROR] Ошибка обновления кэша: {e}")
        time.sleep(UPDATE_INTERVAL)

threading.Thread(target=update_track_cache_periodically, daemon=True).start()

# ================== Контакты ==================
def show_contacts(chat_id):
    text = "📞 *Барои тамос бо TAJEXPRESS, яке аз рақамҳои зеринро интихоб кунед:*\n\n"
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    markup.add(types.InlineKeyboardButton("📱 Менеҷер: +992 985 171 732", url="https://t.me/zubaidullo_tjk"))
    markup.add(types.InlineKeyboardButton("📱 Менеҷер: +992 933 055 707", url="https://t.me/zubaidullo_tjk"))
    markup.add(types.InlineKeyboardButton("📱 Менеҷер: +992 007 282 626", url="https://t.me/Fayoz_7707"))
    
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

# ================== Запуск бота ==================
if __name__ == "__main__":
    print("Бот запущен...")
    # Барои бор кардани кэш дар аввал, пеш аз оғози polling
    load_cache() 
    bot.infinity_polling()
