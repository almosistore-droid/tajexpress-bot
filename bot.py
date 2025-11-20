import os
from flask import Flask, request
import telebot
from telebot import types
from telebot.apihelper import ApiTelegramException
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
WEBHOOK_HOST = os.getenv("WEBHOOK_URL")
DELIVERY_GROUP_ID = int(os.getenv("DELIVERY_GROUP_ID"))
WEBHOOK_ROUTE = f"/{TOKEN}"
WEBHOOK_URL = WEBHOOK_HOST + WEBHOOK_ROUTE

app = Flask(__name__)
bot = telebot.TeleBot(TOKEN)
