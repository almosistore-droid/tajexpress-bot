import os
import re
from telebot import TeleBot, types
from telebot.apihelper import ApiTelegramException
from dotenv import load_dotenv

# ================== Настройки ==================
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

# ================== Меню ==================
BTN_DELIVERY = "🚚 Доставка"
BTN_ADDRESS = "🇨🇳 Гирифтани адрес ва код"
BTN_DUSHANBE = "🇹🇯 Адрес Душанбе"
BTN_PRICE_LIST = "📦 Нархнома"
BTN_TRACK = "🔍 Проверка трек-кода"
BTN_BANNED = "🚫 Молхои манъшуда"
BTN_CONTACTS = "📞 Контакты"
BTN_ABOUT_US = "ℹ️ Информация о нас"

MAIN_MENU = [
    [BTN_DELIVERY, BTN_ADDRESS],
    [BTN_TRACK, BTN_DUSHANBE],
    [BTN_PRICE_LIST, BTN_BANNED],
    [BTN_CONTACTS, BTN_ABOUT_US]
]

def send_main_menu(chat_id, text="Менюи асосӣ. Лутфан, интихоб кунед:"):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for row in MAIN_MENU:
        markup.add(*[types.KeyboardButton(button_text) for button_text in row])
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

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
    send_main_menu(chat_id, welcome_text)

# 🛠️ Функсияи интихоби навъи интиқол барои гирифтани адрес
def choose_delivery_type(chat_id):
    text = "✈️ *Лутфан, навъи интиқолеро, ки мехоҳед истифода баред, интихоб кунед:*"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        types.InlineKeyboardButton("✈️ АВИА", callback_data="address_type_avia"),
        types.InlineKeyboardButton("🚢 НАЗЕМНЫЙ", callback_data="address_type_ground")
    )
    
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

# 🛠️ Обработчик барои интихоби АВИА/НАЗЕМНЫЙ (гирифтани адрес)
@bot.callback_query_handler(func=lambda call: call.data.startswith('address_type_'))
def handle_address_type_callback(call):
    chat_id = call.message.chat.id
    
    try:
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
    except ApiTelegramException:
        pass 
    
    delivery_type = "АВИА" if call.data == "address_type_avia" else "НАЗЕМНЫЙ"
    user_data[chat_id] = {"delivery_type": delivery_type}

    msg = bot.send_message(chat_id, 
                           f"✅ Шумо **{delivery_type}**-ро интихоб кардед.\n\n"
                           f"🇨🇳 Лутфан, номи худро **ТАНҲО бо ҳарфҳои лотинӣ** ворид кунед (масалан, *Ahmad*):")
    
    bot.register_next_step_handler(msg, address_step_name)


# 🛠️ Функсияи интихоби навъи нархнома
def choose_price_list_type(chat_id):
    """Мепурсад, ки корбар нархномаи АВИА-ро мехоҳад ё НАЗЕМНЫЙ."""
    text = "📦 *Нархномаи кадом навъи интиқолро мехоҳед дидан?*"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        types.InlineKeyboardButton("✈️ АВИА", callback_data="price_list_avia"),
        types.InlineKeyboardButton("🚢 Интиқоли заминӣ", callback_data="price_list_ground")
    )
    
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")


# 🛠️ Обработчик барои фиристодани нархнома (АВИА/НАЗЕМНЫЙ)
@bot.callback_query_handler(func=lambda call: call.data.startswith('price_list_'))
def send_price_list(call):
    """Матн ва аксҳои нархномаро мувофиқи интихоби корбар мефиристад."""
    chat_id = call.message.chat.id
    delivery_type = "АВИА" if call.data == "price_list_avia" else "НАЗЕМНЫЙ"
    
    try:
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None) # Нест кардани тугмаҳо
    except ApiTelegramException:
        pass

    # ==================== ID ва Матн барои АВИА ====================
    if delivery_type == "АВИА":
        # ⚠️ ID-и аксҳои АВИА-ро ин ҷо гузоред!
        PHOTO_ID_1 = "ID_AXSI_AVIA_1_RO_INJO_GUZORED" # Агар акси дуюм набошад, ID-ро такрор кунед
        PHOTO_ID_2 = "ID_AXSI_AVIA_2_RO_INJO_GUZORED"
        
        caption_text = (
            "💰 *Нархномаи хизматрасониҳо - АВИА:*\n"
            "---"
            "• **Интиқоли ҳавоӣ:** Аз 3-7 рӯз\n"
            "• **Нарх:** Аз **$10** барои 1 кг (Вобаста ба вазн)\n"
            "• **Тавсия:** Барои борҳои сабук ва зурурӣ."
        )

    # ==================== ID ва Матн барои НАЗЕМНЫЙ ====================
    else: # НАЗЕМНЫЙ
        # ⚠️ ID-и аксҳои НАЗЕМНЫЙ-ро ин ҷо гузоред!
        PHOTO_ID_1 = "ID_AXSI_GROUND_1_RO_INJO_GUZORED"
        PHOTO_ID_2 = "ID_AXSI_GROUND_2_RO_INJO_GUZORED" 
        
        # 🟢 МАТНИ ИСЛОҲШУДАИ НАЗЕМНЫЙ
        caption_text = (
            "💰 *Нархномаи хизматрасониҳо - Интиқоли заминӣ:*\n"
            "---"
            "• Аз **200кг то 1000кг** — *$1.8$* барои 1 кг\n"
            "• Аз **0.1кг то 200кг** — *$3.0$* барои 1 кг\n"
            "Барои тафсилоти бештар бо оператор тамос гиред."
        )

    # ==================== Фиристодани Media Group ====================
    media = [
        # Акси 1 бо caption (матн)
        types.InputMediaPhoto(PHOTO_ID_1, caption=caption_text, parse_mode="Markdown"),
        # Акси 2 бидуни caption
        types.InputMediaPhoto(PHOTO_ID_2)
    ]

    try:
        bot.send_media_group(chat_id, media)
    except Exception as e:
        # Агар фиристодан хатогӣ диҳад, танҳо матнро мефиристем
        print(f"Хатогӣ ҳангоми фиристодани гурӯҳи аксҳо: {e}")
        bot.send_message(chat_id, f"❌ Хатогӣ ҳангоми фиристодани аксҳо.\n\n{caption_text}", parse_mode="Markdown")


# ================== Основной обработчик ==================
@bot.message_handler(func=lambda m: True)
def main_handler(message):
    chat_id = message.chat.id
    text = message.text

    if text == BTN_DELIVERY:
        msg = bot.send_message(chat_id, "🚚 Лутфан, номи пурраи гирандаро ворид кунед:")
        bot.register_next_step_handler(msg, delivery_step_name)

    elif text == BTN_ADDRESS:
        choose_delivery_type(chat_id)

    elif text == BTN_PRICE_LIST:
        # 🟢 Ҳоло ин тугма ба функсияи интихоби нархнома мегузарад
        choose_price_list_type(chat_id) 

    elif text == BTN_TRACK: 
        track_link = "https://t.me/TAJEXPRESSCARGO" 
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        markup.add(types.InlineKeyboardButton("📢 Ба канали TAJEXPRESSCARGO ворид шавед", url=track_link))
        
        track_text = (
            "🔍 Барои тафтиши трек-коди худ, лутфан ба канали мо ворид шавед.\n\n"
            "*Ҳамаи трек-кодҳои воридшуда ва тафтишшуда дар ин канал нашр мешаванд.*"
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
                              "⚠️ *Р
