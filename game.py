import telebot, sqlite3, os
from telebot import types
from flask import Flask
from threading import Thread

# Твой актуальный токен
TOKEN = '8840112637:AAHKDM7xiUQlw9c4o_z79dTeIqs4jJtWLVc'
bot = telebot.TeleBot(TOKEN)
app = Flask('')

# --- Веб-сервер для Render ---
@app.route('/')
def home(): return "Bot is alive"
def run_web(): app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# --- База данных ---
def init_db():
    conn = sqlite3.connect('stope_v2.db')
    c = conn.cursor()
    # Создаем таблицу, если она не существует
    c.execute('''CREATE TABLE IF NOT EXISTS players 
                 (uid INTEGER PRIMARY KEY, name TEXT, class TEXT, atk INTEGER, deff INTEGER, 
                  gold INTEGER, crystals INTEGER DEFAULT 10000)''')
    conn.commit(); conn.close()
init_db()

CLASSES = {
    "Berserker": {"atk": 45, "deff": 15}, "Vanguard": {"atk": 25, "deff": 35},
    "Assassin": {"atk": 55, "deff": 10}, "Night Ranger": {"atk": 40, "deff": 15}
}

def get_db(): return sqlite3.connect('stope_v2.db', check_same_thread=False)

@bot.message_handler(commands=['start'])
def start(m):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT class FROM players WHERE uid=?", (m.chat.id,))
    user = c.fetchone()
    
    if user and user[0] is not None:
        bot.send_message(m.chat.id, f"⚔️ С возвращением, {m.from_user.first_name}!")
    else:
        markup = types.InlineKeyboardMarkup(row_width=2)
        for cls in CLASSES.keys():
            markup.add(types.InlineKeyboardButton(cls, callback_data=f"setcls_{cls}"))
        c.execute("INSERT OR REPLACE INTO players (uid, name, gold, crystals) VALUES (?, ?, 777000, 10000)", 
                  (m.chat.id, m.from_user.first_name))
        conn.commit()
        bot.send_message(m.chat.id, "🌑 Выберите свой стартовый класс:", reply_markup=markup)
    conn.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith("setcls_"))
def set_class(call):
    uid = call.from_user.id
    cls_name = call.data.split("_")[1]
    stats = CLASSES[cls_name]
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE players SET class=?, atk=?, deff=? WHERE uid=?", (cls_name, stats["atk"], stats["deff"], uid))
    conn.commit(); conn.close()
    bot.edit_message_text(f"✅ Вы выбрали класс: <b>{cls_name}</b>", call.message.chat.id, call.message.message_id, parse_mode="HTML")

# --- Запуск ---
if __name__ == '__main__':
    t = Thread(target=run_web)
    t.start()
    bot.polling(none_stop=True)
    
