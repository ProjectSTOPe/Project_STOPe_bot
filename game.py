import os
import telebot
from flask import Flask
from threading import Thread

# Твой токен
TOKEN = '8840112637:AAHKDM7xiUQlw9c4o_z79dTeIqs4jJtWLVc'
bot = telebot.TeleBot(TOKEN)
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive"

# Простейший обработчик
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Связь работает!")

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

if __name__ == '__main__':
    t = Thread(target=run_web)
    t.start()
    print("Бот запущен, жду команды /start...")
    bot.infinity_polling()
    
