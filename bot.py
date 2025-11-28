import os
import json
import re
import threading
import time
from telebot import TeleBot, types
from telebot.apihelper import ApiTelegramException
from dotenv import load_dotenv

# ================== Настройки ==================
# UPDATE_INTERVAL, GOOGLE_CREDS_PATH, ва ғайра хориҷ карда шуданд.

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ TELEGRAM_BOT_TOKEN не задан!")

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
# track_cache ва user_cache хориҷ карда шуданд, чунки Sheets нест.

# ================== Меню ==================
BTN_DELIVERY = "🚚 Доставка"
BTN_ADDRESS = "🇨🇳 Гирифтани адрес ва код"
BTN_DUSHANBE = "🇹🇯 Адрес Душанбе"
BTN_PRICE_LIST = "📦 Нархнома"
BTN_TRACK = "🔍 Проверка трек-кода"
BTN_BANNED = "🚫 Молхои манъшуда"
BTN_CONTACTS = "📞 Контакты"
BTN_REGISTER = "📝 Регистрация"
BTN_ABOUT_US = "ℹ️ Информация о нас"

MAIN_MENU = [
    [BTN_REGISTER],
    [BTN_DELIVERY, BTN_ADDRESS],
    [BTN_TRACK, BTN_DUSHANBE],
    [BTN_PRICE_LIST, BTN_BANNED],
    [BTN_CONTACTS, BTN_ABOUT_US]
]

def send_main_menu(chat_id, text=""):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for row in MAIN_MENU:
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

    if text == BTN_REGISTER:
        msg = bot.send_message(chat_id, "📝 **Барои бақайдгирӣ** лутфан, номи худро ворид кунед:")
        bot.register_next_step_handler(msg, register_step_name)

    elif text == BTN_DELIVERY:
        msg = bot.send_message(chat_id, "🚚 Лутфан, номи пурраи гирандаро ворид кунед:")
        bot.register_next_step_handler(msg, delivery_step_name)

    elif text == BTN_ADDRESS:
        msg = bot.send_message(chat_id, "🇨🇳 **Барои гирифтани адрес**.\nНом худро **ТАНҲО бо ҳарфҳои лотинӣ** ворид кунед (масалан, *Ahmad*):")
        bot.register_next_step_handler(msg, address_step_name)

    elif text == BTN_PRICE_LIST:
        bot.send_message(chat_id,
                          "💰 *Нархномаи хизматрасониҳо:*\n"
                          "• Аз **200кг то 1000кг** — *$1.8$* барои 1 кг\n"
                          "• Аз **0.1кг то 200кг** — *$3.0$* барои 1 кг\n"
                          "Барои тафсилоти бештар бо оператор тамос гиред.",
                          parse_mode="Markdown")

    elif text == BTN_TRACK:
        # Логикаи фиристодани ссылка
        track_link = "https://t.me/TAJEXPRETACCOD" 
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
    
    elif text == BTN_ABOUT_US:
        show_about_us(chat_id)

    else:
        bot.send_message(chat_id, "Ин фармон шинохта нашуд. Лутфан, тугмаи менюро истифода баред.")
        send_main_menu(chat_id)


# ================== Регистрация (Танҳо паём) ==================
# Функсияҳои Sheets (get_users_sheet ва save_user) хориҷ карда шуданд.
def register_step_name(message):
    chat_id = message.chat.id
    user_data[chat_id] = {"name": message.text.strip()}
    msg = bot.send_message(chat_id, "📞 Рақами телефони худро (дар формати +992 XXX XX XX XX) ворид кунед:")
    bot.register_next_step_handler(msg, register_step_phone)

def register_step_phone(message):
    chat_id = message.chat.id
    phone = message.text.strip()
    user_data[chat_id]["phone"] = phone
    
    # ❌ Коди save_user хориҷ карда шуд
    
    bot.send_message(chat_id,
                     f"✅ **Бақайдгирии шумо бо муваффақият анҷом ёфт!**\n"
                     f"👤 Ном: *{user_data[chat_id]['name']}*\n"
                     f"📞 Тел: *{phone}*\n\n"
                     "Шумо метавонед аз менюи асосӣ хизматрасонии лозимаро интихоб кунед.\n\n"
                     "⚠️ _Эзоҳ: Маълумоти бақайдгирӣ ҳоло танҳо дар чати шумо нигоҳ дошта мешавад. Лутфан, бо оператор тамос гиред._",
                     parse_mode="Markdown")
    send_main_menu(chat_id)

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
        # Заявка по-прежнему в группу отправляется
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
    
    # Эзоҳ: "17590820846" дар ин ҷо рақами тамос дар Чин аст
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

# ================== Контакты ==================
def show_contacts(chat_id):
    text = "📞 *Барои тамос бо TAJEXPRESS, яке аз рақамҳои зеринро интихоб кунед:*\n\n"
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    markup.add(types.InlineKeyboardButton("📱 Менеҷер: +992 985 171 732", url="https://t.me/zubaidullo_tjk"))
    markup.add(types.InlineKeyboardButton("📱 Менеҷер: +992 933 055 707", url="https://t.me/zubaidullo_tjk"))
    markup.add(types.InlineKeyboardButton("📱 Менеҷер: +992 007 282 626", url="https://t.me/Fayoz_7707"))
    
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

# ================== Маълумот дар бораи мо ==================
def show_about_us(chat_id):
    text = "ℹ️ *Мо дар шабакаҳои иҷтимоӣ:*\n\n"
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    markup.add(types.InlineKeyboardButton("📢 Канали Telegram", url="https://t.me/TAJEXPRESSCARGO"))
    # Истиноди Instagram-и худро иваз кунед
    markup.add(types.InlineKeyboardButton("📸 Саҳифаи Instagram", url="https://www.instagram.com/taj_express01?igsh=ZmcxdHE4eXI0aWc1")) 
    
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

# ================== Запуск бота ==================
if __name__ == "__main__":
    print("Бот запущен...")
    # Коди load_cache ва threading барои кэш хориҷ карда шуд.
    bot.infinity_polling()
