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
# ================== CITY DATA ==================

CITY_LIST = {

    "city_dushanbe": "DUSHANBE",
    "city_bokhtar": "BOKHTAR",
    "city_jabbor": "JABBOR RASULOV"

}
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
            "• **Муҳлати интиқол:** Аз 3-7 рӯз\n"
            "• Аз **0.1кг то 1кг** — *8 $*\n"
            "• Аз **1 кг то 50кг** — *8 $* барои 1 кг\n"
            "• Аз **50 кг то 200кг** — *7 $* барои 1 кг\n"  
            "• Аз **200 кг боло ** — *6.5 $* барои 1 кг\n"
            "• **Тавсия:** Барои борҳои сабук ва зурурӣ."
        )
    else:
        caption_text = (
            "💰 *Нархномаи хизматрасониҳо - Интиқоли заминӣ:*\n"
            "• **Муҳлати интиқол:** Аз 15-25 рӯз\n"
            "• Аз **0.1кг то 0.5кг** — * 1,25 $ *\n"
            "• Аз **0.5кг то 1кг** — *2.5 $ *\n"
            "• Аз **50 кг то 200кг** — *2.3 $* барои 1 кг\n"
            "• Аз **200кг боло ** — *1.9 $* барои 1 кг\n"
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

        markup = types.InlineKeyboardMarkup(row_width=1)

        markup.add(
            types.InlineKeyboardButton("🏢 Dushanbe", callback_data="city_dushanbe"),
            types.InlineKeyboardButton("🏢 Bokhtar", callback_data="city_bokhtar"),
            types.InlineKeyboardButton("🏢 Jabbor Rasulov", callback_data="city_jabbor")
    )

    bot.send_message(
        chat_id,
        "📍 Шаҳрро интихоб кунед:",
        reply_markup=markup
    )

    bot.send_message(
        chat_id,
        "📍 Шаҳрро интихоб кунед:",
        reply_markup=markup
    )
        
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

@bot.callback_query_handler(func=lambda call: call.data.startswith("city_"))
def city_callback(call):

    chat_id = call.message.chat.id

    city = CITY_LIST.get(call.data)

    user_data[chat_id] = {

        "city": city

    }

    msg = bot.send_message(
        chat_id,
        "👤 Номро бо ҳарфҳои лотинӣ ворид кунед:"
    )

    bot.register_next_step_handler(
        msg,
        city_name_step
    )
def city_name_step(message):

    chat_id = message.chat.id

    name = message.text.strip()

    user_data[chat_id]["name"] = name

    msg = bot.send_message(
        chat_id,
        "📞 Телефон (9 рақам):"
    )

    bot.register_next_step_handler(
        msg,
        city_phone_step
    )
def city_phone_step(message):

    chat_id = message.chat.id

    phone = re.sub(r'\D', '', message.text)[-9:]

    data = user_data[chat_id]

    city = data["city"]

    name = data["name"]

    c_name = f"{city} {name}"

    c_phone = "17590820846"

    c_addr = f"福田三小区80栋二单元305室 {city} {name} {phone}"

    full = f"""
🇨🇳 Адреси шумо:

👤 收货人: {c_name}

📞 手机: {c_phone}

📍 地址:

浙江省 义乌市

{c_addr}
"""

    bot.send_message(chat_id, full)

    send_main_menu(chat_id)
# ================== Запуск бота ==================
if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling()
