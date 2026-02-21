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

CHANNEL_USERNAME = "@TAJEXPRESSCARGO"


# ================== Телеграм бот ==================

bot = TeleBot(TOKEN, threaded=True)


# ================== Данные пользователей ==================

user_data = {}


# ================== RESET STATE ==================

def reset_user_state(chat_id):

    if chat_id in user_data:
        del user_data[chat_id]

    try:
        bot.clear_step_handler_by_chat_id(chat_id)
    except:
        pass


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


# ================== Helpers ==================

def is_subscribed(user_id):

    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status

        return status in ['member', 'administrator', 'creator']

    except Exception as e:

        print(e)

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

    bot.send_message(chat_id,
                     "Ба канал обуна шавед",
                     reply_markup=markup,
                     parse_mode="Markdown")



def send_main_menu(chat_id,
                   text="Менюи асосӣ. Лутфан интихоб кунед:"):

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    for row in MAIN_MENU:
        markup.add(*row)

    bot.send_message(chat_id,
                     text,
                     reply_markup=markup)


# ================== START ==================

@bot.message_handler(commands=["start", "help"])
def start_handler(message):

    if is_subscribed(message.from_user.id):

        send_main_menu(message.chat.id)

    else:

        send_subscription_invite(message.chat.id)



# ================== CALLBACK ==================

@bot.callback_query_handler(func=lambda call:
call.data == "check_sub")
def check_sub(call):

    if is_subscribed(call.from_user.id):

        bot.answer_callback_query(call.id,
                                  "✅ Обуна тасдиқ шуд")

        bot.delete_message(call.message.chat.id,
                           call.message.message_id)

        send_main_menu(call.message.chat.id)

    else:

        bot.answer_callback_query(call.id,
                                  "❌ Обуна нашудаед",
                                  show_alert=True)



# ================== ADDRESS TYPE ==================

def choose_delivery_type(chat_id):

    markup = types.InlineKeyboardMarkup()

    markup.add(

        types.InlineKeyboardButton(
            "✈️ Интиқоли ҳавоӣ",
            callback_data="address_type_avia"),

        types.InlineKeyboardButton(
            "🚚 Интиқоли заминӣ",
            callback_data="address_type_ground")
    )

    bot.send_message(chat_id,
                     "Навъи интиқолро интихоб кунед:",
                     reply_markup=markup)



@bot.callback_query_handler(func=lambda call:
call.data.startswith("address_type_"))
def address_type_handler(call):

    chat_id = call.message.chat.id

    reset_user_state(chat_id)

    try:
        bot.edit_message_reply_markup(chat_id,
                                      call.message.message_id,
                                      reply_markup=None)
    except:
        pass


    delivery_type = "АВИА" if "avia" in call.data else "Заминӣ"

    user_data[chat_id] = {
        "delivery_type": delivery_type
    }

    msg = bot.send_message(chat_id,
                           "Номро бо лотин ворид кунед:")

    bot.register_next_step_handler(msg,
                                   address_step_name)



# ================== ADDRESS STEPS ==================

def address_step_name(message):

    chat_id = message.chat.id

    name = message.text.strip()

    if not re.match(r"^[A-Za-z\s]+$", name):

        msg = bot.send_message(chat_id,
                               "Фақат бо лотин:")

        bot.register_next_step_handler(msg,
                                       address_step_name)

        return


    if chat_id not in user_data:

        user_data[chat_id] = {}


    user_data[chat_id]["name"] = name


    msg = bot.send_message(chat_id,
                           "Телефон:")

    bot.register_next_step_handler(msg,
                                   address_step_phone)



def address_step_phone(message):

    chat_id = message.chat.id

    phone = re.sub(r'\D', '',
                   message.text)[-9:]


    if len(phone) < 9:

        msg = bot.send_message(chat_id,
                               "Хато:")

        bot.register_next_step_handler(msg,
                                       address_step_phone)

        return


    user_data[chat_id]["phone"] = phone


    data = user_data[chat_id]

    dtype = data.get("delivery_type")


    if "АВИА" in dtype:

        c_name = f"SAM {data['name']}"

        c_phone = "17813714041"

        c_addr = f"北京 {data['name']} {phone}"

    else:

        c_name = data['name']

        c_phone = "17590820846"

        c_addr = f"义乌 {data['name']} {phone}"


    bot.send_message(chat_id,
                     f"{c_name}\n{c_phone}\n{c_addr}")

    send_main_menu(chat_id)



# ================== DELIVERY ==================

def delivery_step_name(message):

    chat_id = message.chat.id

    user_data[chat_id] = {
        "name": message.text
    }

    msg = bot.send_message(chat_id,
                           "Адрес:")

    bot.register_next_step_handler(msg,
                                   delivery_step_address)



def delivery_step_address(message):

    chat_id = message.chat.id

    user_data[chat_id]["address"] = message.text

    msg = bot.send_message(chat_id,
                           "Телефон:")

    bot.register_next_step_handler(msg,
                                   delivery_step_phone)



def delivery_step_phone(message):

    chat_id = message.chat.id

    phone = message.text

    user_data[chat_id]["phone"] = phone

    bot.send_message(chat_id,
                     "✅ Кабул шуд")

    send_main_menu(chat_id)



# ================== MAIN HANDLER ==================

@bot.message_handler(func=lambda message: True)
def main_handler(message):

    chat_id = message.chat.id


    if not is_subscribed(message.from_user.id):

        send_subscription_invite(chat_id)

        return


    text = message.text


    if text in [

        BTN_DELIVERY,
        BTN_ADDRESS,
        BTN_PRICE_LIST,
        BTN_TRACK,
        BTN_DUSHANBE,
        BTN_BANNED,
        BTN_CONTACTS,
        BTN_ABOUT_US,
        BTN_LESSON

    ]:

        reset_user_state(chat_id)



    if text == BTN_DELIVERY:

        msg = bot.send_message(chat_id,
                               "Ном:")

        bot.register_next_step_handler(msg,
                                       delivery_step_name)


    elif text == BTN_ADDRESS:

        choose_delivery_type(chat_id)


    elif text == BTN_CONTACTS:

        bot.send_message(chat_id,
                         "Контакты")


    else:

        send_main_menu(chat_id)



# ================== RUN ==================

print("БОТ ЗАПУЩЕН")

bot.infinity_polling()
