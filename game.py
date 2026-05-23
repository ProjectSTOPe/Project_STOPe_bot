import os
import telebot
import sqlite3
import random
import time
import requests
from telebot import types
from flask import Flask
from threading import Thread

TOKEN = '8840112637:AAHKDM7xiUQlw9c4o_z79dTeIqs4jJtWLVc'
bot = telebot.TeleBot(TOKEN)
app = Flask('')

# --- ТУТ БУДУТ ТВОИ ФУНКЦИИ (init_db, CLASSES, и т.д.) ---
# Оставь всё, что было у тебя раньше (init_db, CLASSES, GRADES, LOOT_POOL, хэндлеры...)

@app.route('/')
def home():
    return "Bot is alive"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

if __name__ == '__main__':
    # Запускаем веб-сервер в фоне
    t = Thread(target=run_web)
    t.start()

    # Запускаем бота
    print("Бот запускается...")
bot.infinity_polling(none_stop=True, interval=0, timeout=20)
