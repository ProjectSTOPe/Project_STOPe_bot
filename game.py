import telebot, sqlite3
from telebot import types
from flask import Flask
from threading import Thread
import os

TOKEN = '8840112637:AAHKDM7xiUQlw9c4o_z79dTeIqs4jJtWLVc'
bot = telebot.TeleBot(TOKEN)
app = Flask('')

@app.route('/')
def home(): return "Bot is alive"
def run_web(): app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# Настройки классов
CLASSES = {
    "Ассасин": {"atk": 55, "deff": 10, "passive": "Крит. удар +8%"},
    "Авангард": {"atk": 25, "deff": 35, "passive": "Снижение урона -10%"},
    "Маг": {"atk": 50, "deff": 8, "passive": "+10% к урону, -5% защиты"}
}

def init_db():
    conn = sqlite3.connect('stope_v2.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS players 
                 (uid INTEGER PRIMARY KEY, name TEXT, class TEXT, level INTEGER DEFAULT 1, exp INTEGER DEFAULT 0,
                  atk INTEGER, deff INTEGER)''')
    conn.commit(); conn.close()
init_db()

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("⚔️ PvP", "🌿 PvE", "👤 Герой", "🎒 Инвентарь", "🏰 Призыв", "📝 Квесты", "💨 Навыки")
    return markup

@bot.message_handler(commands=['start'])
def start(m):
    conn = sqlite3.connect('stope_v2.db')
    c = conn.cursor()
    c.execute("SELECT class FROM players WHERE uid=?", (m.chat.id,))
    user = c.fetchone()
    
    if user and user[0]:
        bot.send_message(m.chat.id, "⚔️ С возвращением в S-Rank Online!", reply_markup=main_menu())
    else:
        markup = types.InlineKeyboardMarkup(row_width=1)
        for cls in CLASSES.keys():
            markup.add(types.InlineKeyboardButton(cls, callback_data=f"setcls_{cls}"))
        c.execute("INSERT OR IGNORE INTO players (uid, name) VALUES (?, ?)", (m.chat.id, m.from_user.first_name))
        conn.commit()
        bot.send_message(m.chat.id, "🌑 Выберите свой путь:", reply_markup=markup)
    conn.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith("setcls_"))
def set_class(call):
    cls_name = call.data.split("_")[1]
    stats = CLASSES[cls_name]
    conn = sqlite3.connect('stope_v2.db')
    c = conn.cursor()
    c.execute("UPDATE players SET class=?, atk=?, deff=? WHERE uid=?", (cls_name, stats["atk"], stats["deff"], call.from_user.id))
    conn.commit(); conn.close()
    bot.edit_message_text(f"✅ Выбран класс: {cls_name}\nПассивка: {stats['passive']}", call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "Добро пожаловать в меню:", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "👤 Герой")
def hero_stats(m):
    conn = sqlite3.connect('stope_v2.db')
    c = conn.cursor()
    c.execute("SELECT name, class, level, atk, deff FROM players WHERE uid=?", (m.chat.id,))
    p = c.fetchone()
    if p:
        text = f"👤 <b>{p[0]}</b>\n🛡️ {p[1]} · Уровень {p[2]}\n\n⚔️ Атака: {p[3]}\n🛡️ Защита: {p[4]}"
        bot.send_message(m.chat.id, text, parse_mode="HTML")
    conn.close()

if __name__ == '__main__':
    Thread(target=run_web).start()
    bot.polling(none_stop=True)
    
