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

# Номи канали шумо барои тафтиши обуна
CHANNEL_USERNAME = "@TAJEXPRESSCARGO" 

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
BTN_ABOUT_US = "ℹ️ Маълумот дар бораи мо"
BTN_LESSON = "🎓 ДАРС"

MAIN_MENU = [
    [BTN_DELIVERY, BTN_ADDRESS],
    [BTN_TRACK, BTN_DUSHANBE],
    [BTN_PRICE_LIST, BTN_BANNED],
    [BTN_CONTACTS, BTN_ABOUT_US],
    [BTN_LESSON]
]

# ================== Функсияҳои ёрирасон ==================

def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"❌ Хатогӣ дар тафтиши обуна: {e}")
        return False

def send_subscription_invite(chat_id):
    markup = types.InlineKeyboardMarkup()
    url = f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"
    markup.add(types.InlineKeyboardButton("📢 Обуна шудан ба канал", url=url))
    markup.add(types.InlineKeyboardButton("✅ Тафтиш кардан", callback_data="check_sub"))
    
    text = (
        f"🛑 *Барои истифодабарии бот шумо бояд аввал ба канали мо обуна шавед:*\n\n"
        f"{CHANNEL_USERNAME}\n\n"
        "Пас аз обуна шудан, тугмаи **'✅ Тафтиш кардан'**-ро пахш кунед."
    )
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

def send_main_menu(chat_id, text="Менюи асосӣ. Лутфан, интихоб кунед:"):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for row in MAIN_MENU:
        markup.add(*[types.KeyboardButton(button_text) for button_text in row])
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

# ================== START & HANDLERS ==================

@bot.message_handler(commands=["start", "help"])
def start_handler(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if is_subscribed(user_id):
        welcome_text = (
            "🚀 *TAJEXPRESS* – каргои боваринок ва бехатар барои овардани борхои Шумо!\n\n"
            "📦 Борҳои худро **зуд ва бехатар** фиристед\n"
            "⏱️ Дархостҳоро осон ва зуд иҷро намоед\n"
            "🇨🇳 *Суроғаи қулай дар Чин* барои харидҳои шумо\n\n"
            "Менюи зерро интихоб кунед:"
        )
        send_main_menu(chat_id, welcome_text)
    else:
        send_subscription_invite(chat_id)

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub_callback(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id

    if is_subscribed(user_id):
        bot.answer_callback_query(call.id, "✅ Ташаккур барои обуна!")
        bot.delete_message(chat_id, call.message.message_id)
        send_main_menu(chat_id, "🚀 Хуш омадед! Акнун шумо метавонед ботро истифода баред:")
    else:
        bot.answer_callback_query(call.id, "❌ Шумо ҳоло ҳам обуна нашудаед!", show_alert=True)

# 🛠️ Функсияи интихоби навъи интиқол
def choose_delivery_type(chat_id):
    text = "*Лутфан, навъи интиқолро интихоб кунед:*"
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✈️ Интиқоли ҳавоӣ (АВИА)", callback_data="address_type_avia"),
        types.InlineKeyboardButton("🚚 Интиқоли заминӣ", callback_data="address_type_ground")
    )
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('address_type_'))
def handle_address_type_callback(call):
    chat_id = call.message.chat.id
    try:
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
    except ApiTelegramException:
        pass 

    delivery_type = "Интиқоли ҳавоӣ (АВИА)" if call.data == "address_type_avia" else "Интиқоли заминӣ"
    user_data[chat_id] = {"delivery_type": delivery_type}
    msg = bot.send_message(chat_id, "🇨🇳 Лутфан, номи худро **ТАНҲО бо ҳарфҳои лотинӣ** ворид кунед:")
    bot.register_next_step_handler(msg, address_step_name)

# >>>>>>>>>>>>>>> FIX START (ЕДИНСТВЕННОЕ ИСПРАВЛЕНИЕ)
def address_step_name(message):
    chat_id = message.chat.id
    name = message.text.strip()

    if not re.match(r"^[A-Za-z\s]+$", name):
        msg = bot.send_message(
            chat_id,
            "❌ Лутфан, номи худро **ТАНҲО бо ҳарфҳои лотинӣ** ворид кунед:",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, address_step_name)
        return

    user_data[chat_id]["name"] = name
    msg = bot.send_message(chat_id, "📞 Лутфан, рақами телефонро ворид кунед (мисол: 985112233):")
    bot.register_next_step_handler(msg, address_step_phone)
# >>>>>>>>>>>>>>> FIX END

def choose_price_list_type(chat_id):
    text = "📦 *Нархномаи кадом навъи интиқолро мехоҳед дидан?*"
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✈️ Интиқоли ҳавоӣ (АВИА)", callback_data="price_list_avia"),
        types.InlineKeyboardButton("🚚 Интиқоли заминӣ", callback_data="price_list_ground")
    )
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('price_list_'))
def send_price_list(call):
    chat_id = call.message.chat.id
    delivery_type = "АВИА" if call.data == "price_list_avia" else "НАЗЕМНЫЙ"
    try:
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None) 
    except ApiTelegramException: pass

    if delivery_type == "АВИА":
        caption_text = (
            "💰 *Нархномаи хизматрасониҳо - АВИА:*\n"
            "• **Интиқоли ҳавоӣ:** Аз 3-7 рӯз\n"
            "• Аз **0.1кг то 1кг** — *80 сомони*\n"
            "• Аз **1 кг то 50кг** — *75 сомони* барои 1 кг\n"
            "• Аз **50 кг то 200кг** — *65 сомони* барои 1 кг\n"  
            "• Аз **200 кг боло ** — *60 сомони* барои 1 кг\n"
            "• **Тавсия:** Барои борҳои сабук ва зурурӣ."
        )
    else:
        caption_text = (
            "💰 *Нархномаи хизматрасониҳо - Интиқоли заминӣ:*\n"
            "• Аз **0.1кг то 0.5кг** — *12 сомони*\n"
            "• Аз **0.5кг то 1кг** — *24 сомони*\n"
            "• Аз **20 кг то 200кг** — *20 сомони* барои 1 кг\n"
            "• Аз **200кг то 1000кг** — *19 сомони* барои 1 кг\n"
            "Барои тафсилоти бештар бо мо тамос гиред."
        )
    bot.send_message(chat_id, caption_text, parse_mode="Markdown")

# ================== ОСНОВНОЙ ОБРАБОТЧИК ==================

@bot.message_handler(func=lambda m: True)
def main_handler(message):
    chat_id = message.chat.id
    if not is_subscribed(message.from_user.id):
        send_subscription_invite(chat_id)
        return

    text = message.text

    if text == BTN_DELIVERY:
        msg = bot.send_message(chat_id, "🚚 Лутфан, номи пурраи худро ворид кунед:")
        bot.register_next_step_handler(msg, delivery_step_name)
    
    elif text == BTN_ADDRESS:
        choose_delivery_type(chat_id)
        
    elif text == BTN_PRICE_LIST:
        choose_price_list_type(chat_id)
        
    elif text == BTN_TRACK:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Канали ТРЕК-КОДЫ", url="https://t.me/TAJEXPRESSTRACCOD"))
        bot.send_message(chat_id, "🔍 Барои тафтиши код ба канал ворид шавед.", reply_markup=markup)
        
    elif text == BTN_DUSHANBE:
        bot.send_message(chat_id, "🏢 *Адрес Душанбе:* 103 мкр, бинои 34. ⏰ 9:00 - 18:00", parse_mode="Markdown")
        
    elif text == BTN_BANNED:
        bot.send_message(chat_id,

                              "⚠️ *Рӯйхати маҳсулотҳои манъшуда барои интиқол:*\n"
                              "🔥 1. **Маводҳои тарканда** (аз қабили пиротехника)\n"
                              "🔋 2. **Батареяҳо, аккумуляторҳо, магнитҳо ва повербанкҳо** (дар шакли алоҳида)\n"
                              "🥗 3. **Хӯрокворӣ, тухмӣ ва шинонандаҳо**\n"
                              "🔫 4. **Ҳарбу зарфҳо, кастет ва кордҳо** (ғайриқонунӣ)\n"
                              "⛽ 5. **Маводи сӯзишворӣ, равған ва косметикаи моеъ**\n"
                              "💎 6. **Нуқра, тилло ва маҳсулоти қиматбаҳо**\n"
                              "💧 7. **Моеъҳо, аэрозолҳо ва кимиёвӣ** (дар ҳаҷми калон)\n"
                              "🔞 8. **Ҳама намуд маҳсулотҳои 18+** (маводҳои порнографӣ, бозичаҳои ҷинсӣ ва ғайра)\n\n"
                              "_Лутфан, пеш аз фиристодан, ин рӯйхатро бодиққат хонед._", parse_mode="Markdown")
        
    elif text == BTN_LESSON:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📽 Тамошои дарсҳо", url="https://t.me/Tajexpresslesson"))
        bot.send_message(chat_id, "🎓 *Омӯзиши ройгон бо TAJEXPRESS*\n\nДар канали мо дарсҳои ройгон мавҷуданд:", reply_markup=markup, parse_mode="Markdown")
        
    elif text == BTN_CONTACTS:
        show_contacts(chat_id)
        
    elif text == BTN_ABOUT_US:
        show_about_us(chat_id)
    
    else:
        send_main_menu(chat_id)

# ================== ЛОГИКАИ ҚАДАМҲО (STEPS) ==================

def delivery_step_name(message):
    user_data[message.chat.id] = {"name": message.text.strip()}
    msg = bot.send_message(message.chat.id, "📍 Адреси худро ворид кунед:")
    bot.register_next_step_handler(msg, delivery_step_address)

def delivery_step_address(message):
    user_data[message.chat.id]["address"] = message.text.strip()
    msg = bot.send_message(message.chat.id, "📞 Рақами телефон (9 рақам):")
    bot.register_next_step_handler(msg, delivery_step_phone)

def delivery_step_phone(message):
    chat_id = message.chat.id
    phone = message.text.strip()
    if len(re.sub(r'\D', '', phone)) >= 9:
        user_data[chat_id]["phone"] = phone
        bot.send_message(chat_id, "✅ Фармоиш қабул шуд!")
        if DELIVERY_GROUP_ID:
            bot.send_message(DELIVERY_GROUP_ID, f"📦 Нав: {user_data[chat_id]['name']}\n📞 {phone}")
        send_main_menu(chat_id)
    else:
        msg = bot.send_message(chat_id, "❌ Хато! Рақамро дуруст нависед:")
        bot.register_next_step_handler(msg, delivery_step_phone)

# Ин қисм барои тугмаи "Гирифтани адрес" муҳим аст
def address_step_phone(message):
    chat_id = message.chat.id
    phone = message.text.strip()
    phone_pattern = re.compile(r"^(?:\+992|8|\+7)?\s*(\d{9})$") 
    match = phone_pattern.match(phone.replace(" ", ""))

    if not match:
        msg = bot.send_message(chat_id, "❌ Хатогӣ! 9 рақам ворид кунед:")
        bot.register_next_step_handler(msg, address_step_phone)
        return
        
    user_data[chat_id]["phone"] = f"+992{match.group(1)}"
    data = user_data[chat_id]
    dtype = data.get('delivery_type', 'Заминӣ')

    # Маълумоти складҳо
    if "АВИА" in dtype:
        c_name = f"SAM {data['name']}"
        c_phone = "17813714041"
        c_prov = "北京市"
        c_city = "通州区"
        c_addr = f"葛布店南里5号楼151 ({data['name']} {data['phone']})"
    else:
        c_name = f"{data['name']}"
        c_phone = "17590820846"
        c_prov = "浙江省"
        c_city = "金华市 / 义乌市"
        c_addr = f"福田三小区80栋二单元305室 ({data['name']} {data['phone']})"
    
    # Сатри Smart Paste барои Pinduoduo
    smart_paste = f"{c_name}，{c_phone}，{c_prov} {c_city} {c_addr}"

    res = (
        f"🇨🇳 **Адреси Шумо барои Pinduoduo / Taobao / 1688:**\n"
        f"✈️ **Навъи интиқол:** {dtype}\n\n"
        f"👤 **收货人 (Имя):**\n`{c_name}`\n\n"
        f"📞 **手机号码 (Телефон):**\n`{c_phone}`\n\n"
        f"📍 **所在地区 (Регион):**\n`{c_prov} {c_city}`\n\n"
        f"🏠 **详细地址 (Адрес):**\n`{c_addr}`\n\n"
        f"`{smart_paste}`"
    )
    
    bot.send_message(chat_id, res, parse_mode="Markdown")
    send_main_menu(chat_id)
def show_contacts(chat_id):
    text = "📞 *Барои тамос:* "
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("📱 Менеҷер: +992 933 055 707", url="https://t.me/zubaidullo_tjk"))
    markup.add(types.InlineKeyboardButton("📱 Менеҷер: +992 007 282 626", url="https://t.me/Fayoz_7707"))
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

def show_about_us(chat_id):
    text = "🌐 *Шабакаҳои иҷтимоии мо:*"
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("📢 Telegram", url="https://t.me/TAJEXPRESSCARGO"))
    markup.add(types.InlineKeyboardButton("📸 Instagram", url="https://www.instagram.com/taj_express01"))
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")
# ================== Запуск бота ==================
if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling()
import os
import re
from telebot import TeleBot, types
from telebot.apihelper import ApiTelegramException
from dotenv import load_dotenv

# ================== Танзимот ==================
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ TELEGRAM_BOT_TOKEN на задан!")

try:
    DELIVERY_GROUP_ID = int(os.getenv("DELIVERY_GROUP_ID", "0"))
except ValueError:
    DELIVERY_GROUP_ID = 0

# Номи канали шумо барои тафтиши обуна
CHANNEL_USERNAME = "@TAJEXPRESSCARGO" 

# ================== Телеграм бот ==================
bot = TeleBot(TOKEN, threaded=False)

# ================== Данные пользователей ==================
user_data = {}

# ================== Меню ==================
BTN_DELIVERY = "🚚 Доставка"
BTN_ADDRESS = "🇨🇳 Гирифтани адрес ва код"
BTN_DUSHANBE = "🇹🇯 Адрес Душанбе"
BTN_PRICE_LIST = "📦 Нархнома"
BTN_TRACK = "🔍 Проверка трек-кода"
BTN_BANNED = "🚫 Молхои манъшуда"
BTN_CONTACTS = "📞 Контакты"
BTN_ABOUT_US = "ℹ️ Маълумот дар бораи мо"
BTN_LESSON = "🎓 ДАРС"

MAIN_MENU = [
    [BTN_DELIVERY, BTN_ADDRESS],
    [BTN_TRACK, BTN_DUSHANBE],
    [BTN_PRICE_LIST, BTN_BANNED],
    [BTN_CONTACTS, BTN_ABOUT_US],
    [BTN_LESSON]
]

# ================== Функсияҳои ёрирасон ==================

def is_subscribed(user_id):
    """Тафтиш мекунад, ки оё корбар ба канал обуна ҳаст ё не."""
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"❌ Хатогӣ дар тафтиши обуна: {e}")
        return False

def send_subscription_invite(chat_id):
    """Паёми даъват ба обунаро мефиристад."""
    markup = types.InlineKeyboardMarkup()
    url = f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"
    markup.add(types.InlineKeyboardButton("📢 Обуна шудан ба канал", url=url))
    markup.add(types.InlineKeyboardButton("✅ Тафтиш кардан", callback_data="check_sub"))
    
    text = (
        f"🛑 *Барои истифодабарии бот шумо бояд аввал ба канали мо обуна шавед:*\n\n"
        f"{CHANNEL_USERNAME}\n\n"
        "Пас аз обуна шудан, тугмаи **'✅ Тафтиш кардан'**-ро пахш кунед."
    )
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

def send_main_menu(chat_id, text="Менюи асосӣ. Лутфан, интихоб кунед:"):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for row in MAIN_MENU:
        markup.add(*[types.KeyboardButton(button_text) for button_text in row])
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

# ================== START & HANDLERS ==================

@bot.message_handler(commands=["start", "help"])
def start_handler(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if is_subscribed(user_id):
        welcome_text = (
            "🚀 *TAJEXPRESS* – каргои боваринок ва бехатар барои овардани борхои Шумо!\n\n"
            "📦 Борҳои худро **зуд ва бехатар** фиристед\n"
            "🇨🇳 *Суроғаи қулай дар Чин* барои харидҳои шумо\n\n"
            "Менюи зерро интихоб кунед:"
        )
        send_main_menu(chat_id, welcome_text)
    else:
        send_subscription_invite(chat_id)

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub_callback(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id

    if is_subscribed(user_id):
        bot.answer_callback_query(call.id, "✅ Ташаккур барои обуна!")
        bot.delete_message(chat_id, call.message.message_id)
        send_main_menu(chat_id, "🚀 Хуш омадед! Акнун шумо метавонед ботро истифода баред:")
    else:
        bot.answer_callback_query(call.id, "❌ Шумо ҳоло ҳам обуна нашудаед!", show_alert=True)

# 🛠️ Функсияи интихоби навъи интиқол
def choose_delivery_type(chat_id):
    text = "*Лутфан, навъи интиқолро интихоб кунед:*"
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✈️ Интиқоли ҳавоӣ (АВИА)", callback_data="address_type_avia"),
        types.InlineKeyboardButton("🚚 Интиқоли заминӣ", callback_data="address_type_ground")
    )
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('address_type_'))
def handle_address_type_callback(call):
    chat_id = call.message.chat.id
    try:
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
    except ApiTelegramException: pass 

    delivery_type = "Интиқоли ҳавоӣ (АВИА)" if call.data == "address_type_avia" else "Интиқоли заминӣ"
    user_data[chat_id] = {"delivery_type": delivery_type}
    msg = bot.send_message(chat_id, f"🇨🇳 Лутфан, номи худро **ТАНҲО бо ҳарфҳои лотинӣ** ворид кунед:")
    bot.register_next_step_handler(msg, address_step_name)

def choose_price_list_type(chat_id):
    text = "📦 *Нархномаи кадом навъи интиқолро мехоҳед дидан?*"
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✈️ АВИА", callback_data="price_list_avia"),
        types.InlineKeyboardButton("🚚 Заминӣ", callback_data="price_list_ground")
    )
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('price_list_'))
def send_price_list(call):
    chat_id = call.message.chat.id
    delivery_type = "АВИА" if call.data == "price_list_avia" else "ЗАМИНӢ"
    try:
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None) 
    except ApiTelegramException: pass

    if delivery_type == "АВИА":
        caption_text = (
            "💰 *Нархнома - АВИА:*\n"
            "• Аз 0.1кг то 1кг — *80 сомони*\n"
            "• Аз 1кг то 50кг — *75 сомони* барои 1 кг\n"
            "• Аз 200кг боло — *60 сомони* барои 1 кг"
        )
    else:
        caption_text = (
            "💰 *Нархнома - ЗАМИНӢ:*\n"
            "• Аз 0.1кг то 0.5кг — *12 сомони*\n"
            "• Аз 0.5кг то 1кг — *24 сомони*\n"
            "• Аз 20кг то 200кг — *20 сомони* барои 1 кг"
        )
    bot.send_message(chat_id, caption_text, parse_mode="Markdown")

# ================== Основной обработчик ==================

@bot.message_handler(func=lambda m: True)
def main_handler(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not is_subscribed(user_id):
        send_subscription_invite(chat_id)
        return

    text = message.text

    if text == BTN_DELIVERY:
        msg = bot.send_message(chat_id, "🚚 Лутфан, номи пурраи худро ворид кунед:")
        bot.register_next_step_handler(msg, delivery_step_name)
    
    elif text == BTN_ADDRESS:
        choose_delivery_type(chat_id)
        
    elif text == BTN_PRICE_LIST:
        choose_price_list_type(chat_id) 
        
    elif text == BTN_TRACK: 
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Канали ТРЕК-КОДЫ", url="https://t.me/TAJEXPRESSTRACCOD"))
        bot.send_message(chat_id, "🔍 Барои тафтиши трек-коди худ ба канал ворид шавед.", reply_markup=markup)
        
    elif text == BTN_DUSHANBE:
        bot.send_message(chat_id, "🏢 *Адрес Душанбе:* 103 мкр, бинои 34. ⏰ 9:00 - 18:00", parse_mode="Markdown")
        
    elif text == BTN_BANNED:
        bot.send_message(chat_id, "⚠️ *Молҳои манъшуда:* Тарканда, Батарея, Хӯрокворӣ, Силоҳ, Тилло, Маҳсулоти 18+.", parse_mode="Markdown")
        
    elif text == BTN_CONTACTS:
        show_contacts(chat_id)
        
    elif text == BTN_ABOUT_US:
        show_about_us(chat_id)
        
    elif text == BTN_LESSON:
        lesson_link = "https://t.me/Tajexpresslesson"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📽 Тамошои дарсҳо", url=lesson_link))
        text_less = (
            "🎓 *Омӯзиши ройгон бо TAJEXPRESS*\n\n"
            "Мо дар канали @Tajexpresslesson дарсҳои ройгонро барои шумо омода кардем. "
            "Барои дидани дарсҳо тугмаи зерро пахш кунед."
        )
        bot.send_message(chat_id, text_less, reply_markup=markup, parse_mode="Markdown")
    
    else:
        send_main_menu(chat_id, "Лутфан, тугмаро интихоб кунед.")

# ================== Логикаи қадамҳо (Steps) ==================

def delivery_step_name(message):
    chat_id = message.chat.id
    user_data[chat_id] = {"name": message.text.strip()}
    msg = bot.send_message(chat_id, "📍 Лутфан, адреси пурраи худро ворид кунед:")
    bot.register_next_step_handler(msg, delivery_step_address)

def delivery_step_address(message):
    chat_id = message.chat.id
    user_data[chat_id]["address"] = message.text.strip()
    msg = bot.send_message(chat_id, "📞 Рақами телефонро ворид кунед (мисол: 985112233):")
    bot.register_next_step_handler(msg, delivery_step_phone)

def delivery_step_phone(message):
    chat_id = message.chat.id
    phone = message.text.strip()
    user_data[chat_id]["phone"] = phone
    
    data = user_data[chat_id]
    delivery_text = f"📦 *Новая заявка*\n👤 {data['name']}\n📍 {data['address']}\n📞 {data['phone']}"
    
    try:
        if DELIVERY_GROUP_ID != 0:
            bot.send_message(DELIVERY_GROUP_ID, delivery_text, parse_mode="Markdown")
        bot.send_message(chat_id, "✅ Фармоиш қабул шуд!", parse_mode="Markdown")
    except:
        bot.send_message(chat_id, "❌ Хатогӣ дар фиристодан.")
    send_main_menu(chat_id)

# ҚАДАМҲОИ ГИРИФТАНИ АДРЕС (Ислоҳшуда)
def address_step_name(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        user_data[chat_id] = {}
    user_data[chat_id]["name"] = message.text.strip()
    msg = bot.send_message(chat_id, "📞 Акнун, рақами телефони худро ворид кунед (9 рақам):")
    bot.register_next_step_handler(msg, address_step_phone)

def address_step_phone(message):
    chat_id = message.chat.id
    phone = message.text.strip()
    
    # Регекс барои тафтиши 9 рақам
    if not re.match(r"^\d{9}$", phone.replace(" ", "").replace("+992", "")):
        msg = bot.send_message(chat_id, "❌ Хатогӣ! Лутфан 9 рақамро нависед:")
        bot.register_next_step_handler(msg, address_step_phone)
        return

    user_data[chat_id]["phone"] = phone
    data = user_data[chat_id]
    dtype = data.get('delivery_type', 'Заминӣ')

    if "АВИА" in dtype:
        c_name, c_phone, c_prov, c_city, c_addr = f"SAM {data['name']}", "17813714041", "北京市", "通州区", f"葛布店南里5号楼151 ({data['name']} {data['phone']})"
    else:
        c_name, c_phone, c_prov, c_city, c_addr = data['name'], "17590820846", "浙江省", "金华市 / 义乌市", f"福田三小区80栋二单元305室 ({data['name']} {data['phone']})"
    
    smart_paste = f"{c_name}，{c_phone}，{c_prov} {c_city} {c_addr}"

    res = (
        f"🇨🇳 **Адреси Шумо ({dtype}):**\n"
        f"👤 **收货人:** `{c_name}`\n"
        f"📞 **手机号码:** `{c_phone}`\n"
        f"📍 **所在地区:** `{c_prov} {c_city}`\n"
        f"🏠 **详细地址:** `{c_addr}`\n\n"
        f"💡 **Smart Paste:**\n`{smart_paste}`"
    )
    bot.send_message(chat_id, res, parse_mode="Markdown")
    send_main_menu(chat_id)

def show_contacts(chat_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📱 Менеҷер", url="https://t.me/zubaidullo_tjk"))
    bot.send_message(chat_id, "📞 Барои тамос бо менеҷер тугмаро пахш кунед:", reply_markup=markup)

def show_about_us(chat_id):
    bot.send_message(chat_id, "🌐 TAJEXPRESS - Каргои боэътимоди шумо.")

# ================== Запуск ==================
if __name__ == "__main__":
    print("Бот фаъол шуд...")
    bot.infinity_polling()
