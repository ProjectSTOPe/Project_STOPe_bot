import telebot, sqlite3, os
from telebot import types
from flask import Flask
from threading import Thread

TOKEN = '8840112637:AAFe2OMBNVdZ9bVCWrgVEsZeZc-9nsnhF4k'
bot = telebot.TeleBot(TOKEN)
app = Flask('')

@app.route('/')
def home(): return "Bot is alive"
def run_web(): app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

def init_db():
    conn = sqlite3.connect('stope_v2.db')
    c = conn.cursor()
    # Удаляем старую таблицу, чтобы гарантированно создать новую с нужными полями
    c.execute('DROP TABLE IF EXISTS players')
    c.execute('''CREATE TABLE players 
                 (uid INTEGER PRIMARY KEY, name TEXT, class TEXT, atk INTEGER, deff INTEGER, 
                  gold INTEGER, crystals INTEGER DEFAULT 10000)''')
    conn.commit(); conn.close()
init_db()

CLASSES = {
    "Berserker": {"atk": 45, "deff": 15}, "Vanguard": {"atk": 25, "deff": 35},
    "Assassin": {"atk": 55, "deff": 10}, "Night Ranger": {"atk": 40, "deff": 15}
}

@bot.message_handler(commands=['start'])
def start(m):
    conn = sqlite3.connect('stope_v2.db')
    c = conn.cursor()
    # Проверяем, есть ли такой юзер
    c.execute("SELECT class FROM players WHERE uid=?", (m.chat.id,))
    user = c.fetchone()
    
    if user:
        bot.send_message(m.chat.id, "⚔️ Ты уже зарегистрирован.")
    else:
        markup = types.InlineKeyboardMarkup()
        for cls in CLASSES.keys():
            markup.add(types.InlineKeyboardButton(cls, callback_data=f"setcls_{cls}"))
        c.execute("INSERT INTO players (uid, name, gold, crystals) VALUES (?, ?, 777000, 10000)", 
                  (m.chat.id, m.from_user.first_name))
        conn.commit()
        bot.send_message(m.chat.id, "🌑 Выберите класс:", reply_markup=markup)
    conn.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith("setcls_"))
def set_class(call):
    cls_name = call.data.split("_")[1]
    stats = CLASSES[cls_name]
    conn = sqlite3.connect('stope_v2.db')
    c = conn.cursor()
    c.execute("UPDATE players SET class=?, atk=?, deff=? WHERE uid=?", (cls_name, stats["atk"], stats["deff"], call.from_user.id))
    conn.commit(); conn.close()
    bot.edit_message_text(f"✅ Выбран: {cls_name}", call.message.chat.id, call.message.message_id)

if __name__ == '__main__':
    t = Thread(target=run_web)
    t.start()
    bot.polling(none_stop=True)
    
