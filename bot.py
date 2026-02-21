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

bot = TeleBot(TOKEN, threaded=False)

CHANNEL_USERNAME = "@TAJEXPRESSCARGO"

try:
    DELIVERY_GROUP_ID = int(os.getenv("DELIVERY_GROUP_ID", "0"))
except ValueError:
    DELIVERY_GROUP_ID = 0


# ================== DATA ==================

user_data = {}

CITY_LIST = {

    "city_dushanbe": "DUSHANBE",
    "city_bokhtar": "BOKHTAR",
    "city_jabbor": "JABBOR RASULOV"

}


# ================== BUTTONS ==================

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


# ================== HELPERS ==================

def is_subscribed(user_id):

    try:

        status = bot.get_chat_member(
            CHANNEL_USERNAME,
            user_id
        ).status

        return status in ['member','administrator','creator']

    except:

        return False



def send_subscription_invite(chat_id):

    markup = types.InlineKeyboardMarkup()

    markup.add(

        types.InlineKeyboardButton(
            "📢 Обуна шудан",
            url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}"
        )
    )

    markup.add(

        types.InlineKeyboardButton(
            "✅ Тафтиш кардан",
            callback_data="check_sub"
        )
    )

    bot.send_message(chat_id,"Ба канал обуна шавед",reply_markup=markup)



def send_main_menu(chat_id,text="Меню:"):

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    for row in MAIN_MENU:

        markup.add(*row)

    bot.send_message(chat_id,text,reply_markup=markup)


# ================== START ==================

@bot.message_handler(commands=["start","help"])
def start_handler(message):

    if is_subscribed(message.from_user.id):

        send_main_menu(message.chat.id)

    else:

        send_subscription_invite(message.chat.id)



@bot.callback_query_handler(func=lambda call:call.data=="check_sub")
def check_sub(call):

    if is_subscribed(call.from_user.id):

        bot.delete_message(call.message.chat.id,
                           call.message.message_id)

        send_main_menu(call.message.chat.id)


# ================== ADDRESS ==================

@bot.message_handler(func=lambda m:m.text==BTN_ADDRESS)
def address_start(message):

    markup=types.InlineKeyboardMarkup()

    markup.add(

        types.InlineKeyboardButton(
            "✈️ Интиқоли ҳавоӣ (АВИА)",
            callback_data="type_avia"),

        types.InlineKeyboardButton(
            "🚚 Интиқоли заминӣ",
            callback_data="type_ground")
    )

    bot.send_message(message.chat.id,
                     "Навъи интиқолро интихоб кунед:",
                     reply_markup=markup)



@bot.callback_query_handler(func=lambda call:
call.data.startswith("type_"))
def type_handler(call):

    chat_id=call.message.chat.id

    delivery_type="AVIA" if call.data=="type_avia" else "GROUND"

    user_data[chat_id]={"delivery_type":delivery_type}

    markup=types.InlineKeyboardMarkup()

    markup.add(

        types.InlineKeyboardButton("🏢 Dushanbe",
                                   callback_data="city_dushanbe"),

        types.InlineKeyboardButton("🏢 Bokhtar",
                                   callback_data="city_bokhtar"),

        types.InlineKeyboardButton("🏢 Jabbor Rasulov",
                                   callback_data="city_jabbor")
    )

    bot.send_message(chat_id,
                     "Шаҳрро интихоб кунед:",
                     reply_markup=markup)



@bot.callback_query_handler(func=lambda call:
call.data.startswith("city_"))
def city_handler(call):

    chat_id=call.message.chat.id

    city=CITY_LIST.get(call.data)

    user_data[chat_id]["city"]=city

    msg=bot.send_message(chat_id,
                         "Номро бо лотин ворид кунед:")

    bot.register_next_step_handler(msg,get_name)



def get_name(message):

    chat_id=message.chat.id

    user_data[chat_id]["name"]=message.text

    msg=bot.send_message(chat_id,"Телефон:")

    bot.register_next_step_handler(msg,get_phone)



def get_phone(message):

    chat_id=message.chat.id

    phone=re.sub(r'\D','',message.text)[-9:]

    data=user_data[chat_id]

    city=data["city"]

    name=data["name"]

    dtype=data["delivery_type"]

    c_name=f"{city} {name}"

    if dtype=="AVIA":

        c_phone="17813714041"

        province="北京市"

        city_cn="通州区"

        address=f"葛布店南里5号楼151 {city} {name} {phone}"

    else:

        c_phone="17590820846"

        province="浙江省"

        city_cn="义乌市"

        address=f"福田三小区80栋二单元305室 {city} {name} {phone}"


    text=f"""
🇨🇳 Адрес:

👤 收货人: {c_name}

📞 手机: {c_phone}

📍 地址:

{province} {city_cn}

{address}
"""

    bot.send_message(chat_id,text)

    send_main_menu(chat_id)


# ================== OTHER BUTTONS ==================

@bot.message_handler(func=lambda m:m.text==BTN_CONTACTS)
def contacts(message):

    markup=types.InlineKeyboardMarkup()

    markup.add(

        types.InlineKeyboardButton(
            "📱 +992933055707",
            url="https://t.me/zubaidullo_tjk"),

        types.InlineKeyboardButton(
            "📱 +992007282626",
            url="https://t.me/Fayoz_7707")
    )

    bot.send_message(message.chat.id,
                     "Контакты:",
                     reply_markup=markup)



# ================== RUN ==================

print("Бот запущен")

bot.infinity_polling()
