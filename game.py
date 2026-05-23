import telebot
import sqlite3
import random
import time
import requests
import os
from telebot import types
from flask import Flask
from threading import Thread

# Настройки
TOKEN = '8840112637:AAFe2OMBNVdZ9bVCWrgVEsZeZc-9nsnhF4k'
MY_WALLET = "UQBpJQIxJSCMMatGblXhEm1832gmW473Zm8oYh5fsUNsSi8M"
bot = telebot.TeleBot(TOKEN)
app = Flask('')

# --- Web Server для Render ---
@app.route('/')
def home(): return "Bot is alive"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# --- База данных ---
def init_db():
    conn = sqlite3.connect('stope_v2.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS players 
                 (uid INTEGER PRIMARY KEY, name TEXT, class TEXT, lvl INTEGER, exp INTEGER, 
                  atk INTEGER, deff INTEGER, gold INTEGER, crystals INTEGER DEFAULT 10000, 
                  afk_start INTEGER DEFAULT 0, afk_hours INTEGER DEFAULT 0, afk_type TEXT DEFAULT 'hunt',
                  dungeon_exp_limit INTEGER DEFAULT 0, dungeon_gold_limit INTEGER DEFAULT 0, 
                  dungeon_crystals_limit INTEGER DEFAULT 0,
                  eq_weapon INTEGER DEFAULT 0, eq_helm INTEGER DEFAULT 0, eq_armor INTEGER DEFAULT 0, 
                  eq_boots INTEGER DEFAULT 0, eq_ring INTEGER DEFAULT 0, eq_amulet INTEGER DEFAULT 0, eq_shield INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, uid INTEGER, item_name TEXT, item_type TEXT, 
                  grade TEXT, enhance INTEGER, item_atk INTEGER DEFAULT 0, item_deff INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS payments (memo TEXT PRIMARY KEY)''')
    conn.commit(); conn.close()

init_db()

# --- Вспомогательные данные ---
CLASSES = {"Berserker": {"atk": 45, "deff": 15}, "Vanguard": {"atk": 25, "deff": 35}, "Assassin": {"atk": 55, "deff": 10}, "Night Ranger": {"atk": 40, "deff": 15}, "Elementalist": {"atk": 50, "deff": 8}, "Deathbringer": {"atk": 42, "deff": 18}, "Divine Caster": {"atk": 20, "deff": 25}, "Destroyer": {"atk": 35, "deff": 22}}
GRADES = {"Серый": "⬜", "Зеленый": "🟢", "Синий": "🔵", "Фиолетовый": "🟣", "Золотой": "🟡", "Красный": "🔴"}
LOOT_POOL = [{"name": "Стальной клинок", "type": "weapon"}, {"name": "Стальной шлем", "type": "helm"}, {"name": "Чешуйчатый доспех", "type": "armor"}, {"name": "Кожаные сапоги охотника", "type": "boots"}, {"name": "Оловянное кольцо", "type": "ring"}, {"name": "Серебряный амулет", "type": "amulet"}, {"name": "Деревянный щит", "type": "shield"}]

def get_db(): return sqlite3.connect('stope_v2.db', check_same_thread=False)

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🤖 Охота (АФК)", "🎒 Инвентарь", "🥊 Арена PvP", "👤 Статы", "🛒 Maгaзин / Донат", "💎 Гача")
    return markup

# --- Обработчики ---
@bot.message_handler(commands=['start'])
def start(m):
    conn = get_db(); c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO players (uid, name, lvl, exp, atk, deff, gold, crystals) VALUES (?, ?, 1, 0, 10, 10, 777000, 10000)", (m.chat.id, m.from_user.first_name))
    conn.commit(); conn.close()
    bot.send_message(m.chat.id, "Добро пожаловать в Stope!", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "👤 Статы")
def profile(m):
    bot.send_message(m.chat.id, "Твой профиль активен.")

@bot.message_handler(func=lambda m: m.text == "🥊 Арена PvP")
def pvp(m):
    bot.send_message(m.chat.id, "Ты на арене!")

# --- Запуск ---
if __name__ == '__main__':
    # 1. Запуск веб-сервера для Render (как показано на 1000001174.jpg)
    t = Thread(target=run_web)
    t.start()
    
    # 2. Запуск бота
    while True:
        try:
            bot.polling(none_stop=True, interval=2, timeout=40)
        except Exception:
            time.sleep(5)
                                     
