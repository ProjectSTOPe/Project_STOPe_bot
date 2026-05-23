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

MY_WALLET = "UQBpJQIxJSCMMatGblXhEm1832gmW473Zm8oYh5fsUNsSi8M"

# --- WEB SERVER FOR RENDER ---
@app.route('/')
def home():
    return "Bot is alive"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# --- GAME LOGIC ---
def init_db():
    conn = sqlite3.connect('stope_v2.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS players 
                 (uid INTEGER PRIMARY KEY, name TEXT, class TEXT, lvl INTEGER, exp INTEGER, 
                  atk INTEGER, deff INTEGER, gold INTEGER, crystals INTEGER DEFAULT 10000, 
                  afk_start INTEGER DEFAULT 0, afk_hours INTEGER DEFAULT 0, 
                  afk_type TEXT DEFAULT 'hunt',
                  dungeon_exp_limit INTEGER DEFAULT 0,
                  dungeon_gold_limit INTEGER DEFAULT 0,
                  dungeon_crystals_limit INTEGER DEFAULT 0,
                  eq_weapon INTEGER DEFAULT 0, eq_helm INTEGER DEFAULT 0, eq_armor INTEGER DEFAULT 0, 
                  eq_boots INTEGER DEFAULT 0, eq_ring INTEGER DEFAULT 0, eq_amulet INTEGER DEFAULT 0, 
                  eq_shield INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, uid INTEGER, item_name TEXT, item_type TEXT, 
                  grade TEXT, enhance INTEGER, item_atk INTEGER DEFAULT 0, item_deff INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS payments (memo TEXT PRIMARY KEY)''')
    conn.commit(); conn.close()

init_db()

CLASSES = {
    "Berserker": {"atk": 45, "deff": 15}, "Vanguard": {"atk": 25, "deff": 35},
    "Assassin": {"atk": 55, "deff": 10}, "Night Ranger": {"atk": 40, "deff": 15},
    "Elementalist": {"atk": 50, "deff": 8}, "Deathbringer": {"atk": 42, "deff": 18},
    "Divine Caster": {"atk": 20, "deff": 25}, "Destroyer": {"atk": 35, "deff": 22}
}
GRADES = {"Серый": "⬜", "Зеленый": "🟢", "Синий": "🔵", "Фиолетовый": "🟣", "Золотой": "🟡", "Красный": "🔴"}
GRADE_MULTIPLIERS = {"Серый": 1, "Зеленый": 3, "Синий": 7, "Фиолетовый": 15, "Золотой": 35, "Красный": 80}
LOOT_POOL = [
    {"name": "Стальной клинок", "type": "weapon"}, {"name": "Стальной шлем", "type": "helm"},
    {"name": "Чешуйчатый доспех", "type": "armor"}, {"name": "Кожаные сапоги охотника", "type": "boots"},
    {"name": "Оловянное кольцо", "type": "ring"}, {"name": "Серебряный амулет", "type": "amulet"},
    {"name": "Деревянный щит", "type": "shield"}, {"name": "Медное кольцо", "type": "ring"}
]

def get_db(): return sqlite3.connect('stope_v2.db', check_same_thread=False)

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🤖 Охота (АФК)", "🎒 Инвентарь", "🥊 Арена PvP", "👤 Статы", "🛒 Maгaзин / Донат", "💎 Гача")
    return markup

def generate_item_stats(item_type, grade):
    mult = GRADE_MULTIPLIERS.get(grade, 1)
    if item_type in ["weapon", "ring", "amulet"]:
        return random.randint(3, 6) * mult, random.randint(0, 1) * mult
    return random.randint(0, 1) * mult, random.randint(4, 8) * mult

def get_total_stats(uid, c):
    c.execute("SELECT atk, deff, eq_weapon, eq_helm, eq_armor, eq_boots, eq_ring, eq_amulet, eq_shield FROM players WHERE uid=?", (uid,))
    p = c.fetchone()
    if not p: return 0, 0
    base_atk, base_deff = p[0], p[1]
    bonus_atk, bonus_deff = 0, 0
    for item_id in p[2:]:
        if item_id:
            c.execute("SELECT item_atk, item_deff FROM inventory WHERE id=?", (item_id,))
            inv = c.fetchone()
            if inv: bonus_atk += inv[0]; bonus_deff += inv[1]
    return (base_atk + bonus_atk), (base_deff + bonus_deff)

@bot.message_handler(commands=['start'])
def start(m):
    conn = get_db(); c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO players (uid, name, class, lvl, exp, atk, deff, gold, crystals) VALUES (?, ?, NULL, 1, 0, 10, 10, 777000, 10000)", (m.chat.id, m.from_user.first_name))
    conn.commit()
    bot.send_message(m.chat.id, "Добро пожаловать в Project STOPe!", reply_markup=main_menu())
    conn.close()

# --- ВСТАВЬ ОСТАЛЬНЫЕ ФУНКЦИИ (profile_stats, shop_menu, gacha, hunt, pvp, inventory) НИЖЕ ---

if __name__ == '__main__':
    t = Thread(target=run_web)
    t.start()
    print("Бот и сервер запущены...")
    bot.infinity_polling(none_stop=True, interval=0, timeout=30)
    
