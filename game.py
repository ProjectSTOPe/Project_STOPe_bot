import telebot, sqlite3, os, random
from telebot import types
from flask import Flask
from threading import Thread

TOKEN = '8840112637:AAHKDM7xiUQlw9c4o_z79dTeIqs4jJtWLVc'
bot = telebot.TeleBot(TOKEN)
bot.remove_webhook()
app = Flask('')

# --- МОДУЛЬНАЯ ЧАСТЬ (сюда будем добавлять контент) ---

# Баланс классов
CLASSES = {
    "Ассасин": {"atk": 15, "dex": 20, "luck": 25, "hp": 100, "passive": "Крит. удар +8%"},
    "Авангард": {"atk": 10, "dex": 10, "luck": 10, "hp": 200, "passive": "Снижение урона -10%"},
    "Маг": {"atk": 25, "deff": 8, "luck": 15, "hp": 80, "passive": "+10% к урону, -5% защиты"}
}

# Новые подземелья добавляются одной строкой здесь
DUNGEONS = {
    "Катакомбы": {"lvl": 1, "exp": 50, "gold": 100},
    "Забытый склеп": {"lvl": 10, "exp": 250, "gold": 500},
    "Логово дракона": {"lvl": 50, "exp": 2000, "gold": 5000}
}

# --- ЯДРО ИГРЫ ---

@app.route('/')
def home(): return "Project STOPe is running"
def run_web(): app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

def init_db():
    conn = sqlite3.connect('stope_v2.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS players 
                 (uid INTEGER PRIMARY KEY, name TEXT, class TEXT, level INTEGER DEFAULT 1, exp INTEGER DEFAULT 0,
                  strength INTEGER DEFAULT 10, dexterity INTEGER DEFAULT 10, luck INTEGER DEFAULT 10, 
                  vitality INTEGER DEFAULT 10, points INTEGER DEFAULT 5, gold INTEGER DEFAULT 777000)''')
    conn.commit(); conn.close()
init_db()

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("⚔️ PvP", "🌿 Подземелья", "👤 Герой", "🎒 Инвентарь", "🏰 Призыв", "📝 Квесты", "💨 Навыки")
    return markup

@bot.message_handler(commands=['start'])
def start(m):
    conn = sqlite3.connect('stope_v2.db')
    c = conn.cursor()
    c.execute("SELECT class FROM players WHERE uid=?", (m.chat.id,))
    user = c.fetchone()
    if user and user[0]:
        bot.send_message(m.chat.id, "⚔️ С возвращением в Project STOPe!", reply_markup=main_menu())
    else:
        markup = types.InlineKeyboardMarkup(row_width=1)
        for cls in CLASSES.keys():
            markup.add(types.InlineKeyboardButton(cls, callback_data=f"setcls_{cls}"))
        c.execute("INSERT OR IGNORE INTO players (uid, name) VALUES (?, ?)", (m.chat.id, m.from_user.first_name))
        conn.commit()
        bot.send_message(m.chat.id, "🌑 Выберите путь в Project STOPe:", reply_markup=markup)
    conn.close()

# --- ВЫБОР ПОДЗЕМЕЛЬЯ ---
@bot.message_handler(func=lambda m: m.text == "🌿 Подземелья")
def list_dungeons(m):
    markup = types.InlineKeyboardMarkup()
    for d_name in DUNGEONS.keys():
        markup.add(types.InlineKeyboardButton(d_name, callback_data=f"dng_{d_name}"))
    bot.send_message(m.chat.id, "Выберите подземелье:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("dng_"))
def enter_dungeon(call):
    d_name = call.data.split("_")[1]
    d = DUNGEONS[d_name]
    conn = sqlite3.connect('stope_v2.db')
    c = conn.cursor()
    c.execute("UPDATE players SET exp = exp + ?, gold = gold + ? WHERE uid=?", (d['exp'], d['gold'], call.from_user.id))
    conn.commit(); conn.close()
    bot.edit_message_text(f"⚔️ Вы прошли <b>{d_name}</b>!\nПолучено: {d['exp']} XP и {d['gold']} золота.", 
                          call.message.chat.id, call.message.message_id, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "👤 Герой")
def hero_stats(m):
    conn = sqlite3.connect('stope_v2.db')
    c = conn.cursor()
    c.execute("SELECT name, class, level, strength, dexterity, luck, vitality, points, gold FROM players WHERE uid=?", (m.chat.id,))
    p = c.fetchone()
    if p:
        text = (f"👤 <b>{p[0]}</b> | {p[1]}\n📈 Уровень: {p[2]} | Очки: {p[7]}\n💰 Золото: {p[8]}\n\n"
                f"⚔️ Сила: {p[3]} | 🏃 Ловкость: {p[4]}\n🍀 Удача: {p[5]} | ❤️ Выносливость: {p[6]}\n\n"
                f"💡 /add [сила/ловкость/удача/выносливость] [кол-во]")
        bot.send_message(m.chat.id, text, parse_mode="HTML")
    conn.close()

@bot.message_handler(commands=['add'])
def add_stats(m):
    args = m.text.split()
    if len(args) < 3: return
    stat, val = args[1].lower(), int(args[2])
    conn = sqlite3.connect('stope_v2.db')
    c = conn.cursor()
    c.execute(f"UPDATE players SET {stat} = {stat} + ?, points = points - ? WHERE uid=? AND points >= ?", (val, val, m.chat.id, val))
    if c.rowcount > 0:
        conn.commit()
        bot.send_message(m.chat.id, f"✅ Успешно прокачано: {stat} на {val}.")
    else:
        bot.send_message(m.chat.id, "❌ Недостаточно очков или неверный параметр.")
    conn.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith("setcls_"))
def set_class(call):
    cls_name = call.data.split("_")[1]
    stats = CLASSES[cls_name]
    conn = sqlite3.connect('stope_v2.db')
    c = conn.cursor()
    c.execute("UPDATE players SET class=?, strength=?, dexterity=?, luck=?, vitality=? WHERE uid=?", 
              (cls_name, stats["atk"], stats["dex"], stats["luck"], stats["hp"]//10, call.from_user.id))
    conn.commit(); conn.close()
    bot.edit_message_text(f"✅ Путь {cls_name} выбран!", call.message.chat.id, call.message.message_id)

if __name__ == '__main__':
    Thread(target=run_web).start()
    bot.polling(none_stop=True)
    
