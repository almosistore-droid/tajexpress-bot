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
BTN_ABOUT_US = "ℹ️ Маълумот дар бораи мо"

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
    text = "*Лутфан, навъи интиқолро интихоб кунед:*"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        types.InlineKeyboardButton("✈️ Интиқоли ҳавоӣ (АВИА)", callback_data="address_type_avia"),
        types.InlineKeyboardButton("🚚 Интиқоли заминӣ", callback_data="address_type_ground")
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
    
    delivery_type = "Интиқоли ҳавоӣ (АВИА)" if call.data == "address_type_avia" else "Интиқоли заминӣ"
    user_data[chat_id] = {"delivery_type": delivery_type}

    msg = bot.send_message(chat_id, 
                           f"🇨🇳 Лутфан, номи худро **ТАНҲО бо ҳарфҳои лотинӣ** ворид кунед (масалан, *Ahmad*):")
    
    bot.register_next_step_handler(msg, address_step_name)


# 🛠️ Функсияи интихоби навъи нархнома
def choose_price_list_type(chat_id):
    """Мепурсад, ки корбар нархномаи АВИА-ро мехоҳад ё Интиқоли заминӣ."""
    text = "📦 *Нархномаи кадом навъи интиқолро мехоҳед дидан?*"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        types.InlineKeyboardButton("✈️ Интиқоли ҳавоӣ (АВИА)", callback_data="price_list_avia"),
        types.InlineKeyboardButton("🚚 Интиқоли заминӣ", callback_data="price_list_ground")
    )
    
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")


# 🛠️ Обработчик барои фиристодани нархнома (АВИА/НАЗЕМНЫЙ)
@bot.callback_query_handler(func=lambda call: call.data.startswith('price_list_'))
def send_price_list(call):
    """Танҳо матни нархномаро мувофиқи интихоби корбар мефиристад (аксҳо нест карда шуданд)."""
    chat_id = call.message.chat.id
    delivery_type = "АВИА" if call.data == "price_list_avia" else "НАЗЕМНЫЙ"
    
    try:
        # Нест кардани тугмаҳои қаблӣ
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None) 
    except ApiTelegramException:
        pass

    # ==================== Матн барои АВИА ====================
    if delivery_type == "АВИА":
        caption_text = (
            "💰 *Нархномаи хизматрасониҳо - АВИА:*\n"
            "---"
            "• **Интиқоли ҳавоӣ:** Аз 3-7 рӯз\n"
            "• **Нарх:** Аз **$10** барои то 0.1 то 1 кг \n"
            "• **Тавсия:** Барои борҳои сабук ва зурурӣ."
        )

    # ==================== Матн барои НАЗЕМНЫЙ ====================
    else: # НАЗЕМНЫЙ
        caption_text = (
            "💰 *Нархномаи хизматрасониҳо - Интиқоли заминӣ:*\n"
            "---"
            "• Аз **200кг то 1000кг** — *$1.8$* барои 1 кг\n"
            "• Аз **0.1кг то 200кг** — *$2.5$* барои 1 кг\n"
            "Барои тафсилоти бештар бо мо тамос гиред."
        )

    # ==================== Танҳо фиристодани Матн ====================
    try:
        # 🟢 Ҳоло танҳо матн фиристода мешавад
        bot.send_message(chat_id, caption_text, parse_mode="Markdown")
    except Exception as e:
        print(f"❌ Хатогӣ ҳангоми фиристодани матн: {e}")
# ================== Основной обработчик ==================
@bot.message_handler(func=lambda m: True)
def main_handler(message):
    chat_id = message.chat.id
    text = message.text

    if text == BTN_DELIVERY:
        msg = bot.send_message(chat_id, "🚚 Лутфан, номи пурраи худро ворид кунед:")
        bot.register_next_step_handler(msg, delivery_step_name)

    elif text == BTN_ADDRESS:
        choose_delivery_type(chat_id)

    elif text == BTN_PRICE_LIST:
        choose_price_list_type(chat_id) 

    elif text == BTN_TRACK: 
        track_link = "https://t.me/TAJEXPRESSTRACCOD" 
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        markup.add(types.InlineKeyboardButton("📢 Ба канали TAJ-EXPRESS ТРЕК-КОДЫ ворид шавед", url=track_link))
        
        track_text = (
            "🔍 Барои тафтиши трек-коди худ, лутфан ба канали мо ворид шавед.\n\n"
            "*Ҳамаи трек-кодҳои воридшуда ва тафтишшуда дар ин канал нашр мешаванд.*"
        )
        bot.send_message(chat_id, track_text, reply_markup=markup, parse_mode="Markdown")
        
    elif text == BTN_DUSHANBE:
        bot.send_message(chat_id, 
                              "🏢 *Адреси мо дар Душанбе:*\n"
                              "🇹🇯 **ш. Душанбе, 103 мкр, бинои 34**\n"
                              "⏰ **Вақти корӣ:** 9:00 - 18:00 (Душанбе)",
                              parse_mode="Markdown")

    elif text == BTN_BANNED:
        # 🟢 Блоки ислоҳшуда
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
    phone = message.text.strip()
    
    # 🟢 Тасдиқкунии (Validation) формати +992 ё 9 рақам
    # (9 рақамро талаб мекунад ва ба +992 иваз мекунад)
    phone_pattern = re.compile(r"^(?:\+992|8|\+7)?\s*(\d{9})$") 
    match = phone_pattern.match(phone.replace(" ", ""))

    if not match:
        msg = bot.send_message(chat_id, 
                               "❌ **Хатогӣ!** Лутфан, рақамро бо формати **9 рақам** ворид кунед (мисол: `985171732`).")
        bot.register_next_step_handler(msg, delivery_step_phone)
        return

    # Рақами асосии 9-гонаро ҷудо мекунем:
    main_phone = match.group(1)
    
    user_data[chat_id]["phone"] = f"+992{main_phone}" # 👈 Формати ниҳоиро +992 месозем
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
        bot.send_message(chat_id, "✅ **✅ Фармоиши Шумо қабул шуд! 🚀 Мо борро то муддати 2 рӯз бурда мерасонем. Одатан, мо борро пеш аз муҳлат бурда мерасонем!", parse_mode="Markdown")
    except ApiTelegramException as e:
        error_msg = f"❌ Ошибка отправки заявки в группу (ID: {DELIVERY_GROUP_ID}). Проверьте настройки: {e}"
        print(error_msg)
        bot.send_message(chat_id, f"❌ Ошибка отправки заявки. Пожалуйста, попробуйте позже или свяжитесь с нами напрямую.")
    send_main_menu(chat_id)


# ================== Адрес (Бо тағйироти НИҲОӢ) ==================
def address_step_name(message):
    chat_id = message.chat.id
    name = message.text.strip()
    
    if chat_id not in user_data or 'delivery_type' not in user_data[chat_id]:
        bot.send_message(chat_id, "❌ **Хатогӣ!** Лутфан, аз менюи асосӣ дубора оғоз кунед ва навъи интиқолро интихоб кунед.")
        send_main_menu(chat_id)
        return
        
    if not re.match(r"^[A-Za-z\s]+$", name):
        msg = bot.send_message(chat_id, "❌ **Хатогӣ!** Танҳо ҳарфҳои лотинӣ истифода баред. Лутфан, дубора ворид кунед:")
        bot.register_next_step_handler(msg, address_step_name)
        return
        
    user_data[chat_id]["name"] = name 
    
    msg = bot.send_message(chat_id, "📞 Лутфан, рақами телефони худро ворид кунед:")
    bot.register_next_step_handler(msg, address_step_phone)


def address_step_phone(message):
    chat_id = message.chat.id
    phone = message.text.strip()
    
    if chat_id not in user_data or 'name' not in user_data[chat_id]:
        bot.send_message(chat_id, "❌ **Хатогӣ!** Лутфан, аз менюи асосӣ дубора оғоз кунед.")
        send_main_menu(chat_id)
        return

    # 🟢 Тасдиқкунии (Validation) формати +992 ё 9 рақам
    phone_pattern = re.compile(r"^(?:\+992|8|\+7)?\s*(\d{9})$") 
    match = phone_pattern.match(phone.replace(" ", ""))

    if not match:
        msg = bot.send_message(chat_id, 
                               "❌ **Хатогӣ!** Лутфан, рақамро бо формати **9 рақам** ворид кунед (мисол: `985171732`).")
        bot.register_next_step_handler(msg, address_step_phone)
        return
        
    # Рақами асосии 9-гонаро ҷудо мекунем:
    main_phone = match.group(1)

    user_data[chat_id]["phone"] = f"+992{main_phone}" # 👈 Формати ниҳоиро +992 месозем
    data = user_data[chat_id]
    
    delivery_type = data.get('delivery_type', 'Номаълум')
    
    
    # ====================================================================
    # ✈️ Логикаи АВИА ва НАЗЕМНЫЙ (Ҳарду бо формати мукаммал)
    # ====================================================================
    if delivery_type == "АВИА":
        # Маълумот барои АВИА (Суроғаи Sam)
        base_address_cn = "北京市通州区葛布店南里5号楼151"
        contact_phone_cn = "17813714041" 
        
    else: # 🚢 НАЗЕМНЫЙ (Ё Номаълум)
        # Маълумот барои НАЗЕМНЫЙ (Суроғаи пешина)
        base_address_cn = "浙江省 金华市 义乌市 福田三小区80栋二单元305室"
        contact_phone_cn = "17590820846"
        
    # 🛠️ ФОРМАТИ НИҲОИИ МУҚАРРАРШУДА: [Номи мизоҷ] [Телефони Чин] [Адреси Чин] [Номи мизоҷ] [Телефони корбар]
    china_address_format = (
        f"{data['name']} {contact_phone_cn} {base_address_cn} {data['name']} {data['phone']}"
    )
    # ====================================================================
    
    # 🟢 БЛОКИ full_address БО ФОСИЛАГУЗОРИИ ДУРУСТ (8 фосила)
    full_address = (
        f"🇨🇳 **Адреси Шумо дар Чин (TAJEXPRESS):**\n"
        f"---"
        f"✈️ **Навъи интиқол:** *{delivery_type}*\n"
        f"👤 **Номи шумо:** *{data['name']}*\n"
        f"📞 **Телефони шумо:** *{data['phone']}*\n\n"
        f"📝 **Барои истифода дар барномаҳои Чин (Якҷоя нависед):**\n"
        f"`{china_address_format}`"
    )
    
    bot.send_message(chat_id, full_address, parse_mode="Markdown")
    send_main_menu(chat_id)
# ================== Контакты ==================
def show_contacts(chat_id):
    text = "📞 *Барои тамос бо TAJEXPRESS, яке аз рақамҳои зеринро интихоб кунед:*\n\n"
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    markup.add(types.InlineKeyboardButton("📱 Менеҷер: +992 933 055 707", url="https://t.me/zubaidullo_tjk"))
    markup.add(types.InlineKeyboardButton("📱 Менеҷер: +992 007 282 626", url="https://t.me/Fayoz_7707"))
    
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

# ================== Маълумот дар бораи мо ==================
def show_about_us(chat_id):
    text = "ℹ️ *Мо дар шабакаҳои иҷтимоӣ:*\n\n"
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    markup.add(types.InlineKeyboardButton("📢 Канали Telegram", url="https://t.me/TAJEXPRESSCARGO"))
    markup.add(types.InlineKeyboardButton("📸 Саҳифаи Instagram", url="https://www.instagram.com/taj_express01?igsh=ZmcxdHE4eXI0aWc1")) 
    
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

# ================== Запуск бота ==================
if __name__ == "__main__":
    print("Бот запущен...")
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ Хатогии глобалӣ ҳангоми кор: {e}")
