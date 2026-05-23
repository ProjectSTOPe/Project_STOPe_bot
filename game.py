import telebot, sqlite3, random, time, requests, os
from telebot import types
from flask import Flask
from threading import Thread

TOKEN = '8840112637:AAFe2OMBNVdZ9bVCWrgVEsZeZc-9nsnhF4k'
bot = telebot.TeleBot(TOKEN)
MY_WALLET = "UQBpJQIxJSCMMatGblXhEm1832gmW473Zm8oYh5fsUNsSi8M"

# --- Веб-сервер для Render ---
app = Flask('')
@app.route('/')
def home(): return "Bot is alive"
def run_web(): app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

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
    if item_type in ["weapon", "ring", "amulet"]: return random.randint(3, 6) * mult, random.randint(0, 1) * mult
    return random.randint(0, 1) * mult, random.randint(4, 8) * mult

def get_total_stats(uid, c):
    c.execute("SELECT atk, deff, eq_weapon, eq_helm, eq_armor, eq_boots, eq_ring, eq_amulet, eq_shield FROM players WHERE uid=?", (uid,))
    p = c.fetchone()
    if not p: return 0, 0
    base_atk, base_deff = p[0], p[1]
    bonus_atk, bonus_deff = 0, 0
    for item_id in p[2:]:
        if item_id and item_id != 0:
            c.execute("SELECT item_atk, item_deff FROM inventory WHERE id=?", (item_id,))
            inv = c.fetchone()
            if inv: bonus_atk += inv[0]; bonus_deff += inv[1]
    return (base_atk + bonus_atk), (base_deff + bonus_deff)

@bot.message_handler(commands=['start'])
def start(m):
    conn = get_db(); c = conn.cursor()
    tg_name = m.from_user.first_name or "Охотник"
    c.execute("SELECT class FROM players WHERE uid=?", (m.chat.id,))
    user = c.fetchone()
    if user and user[0] is not None:
        c.execute("UPDATE players SET name=? WHERE uid=?", (tg_name, m.chat.id)); conn.commit()
        bot.send_message(m.chat.id, f"⚔️ С возвращением, <b>{tg_name}</b>!", reply_markup=main_menu(), parse_mode="HTML")
    else:
        markup = types.InlineKeyboardMarkup(row_width=2)
        for cls in CLASSES.keys(): markup.add(types.InlineKeyboardButton(cls, callback_data=f"setcls_{cls}"))
        c.execute("INSERT OR REPLACE INTO players (uid, name, lvl, exp, atk, deff, gold, crystals) VALUES (?, ?, 1, 0, 10, 10, 777000, 10000)", (m.chat.id, tg_name))
        conn.commit()
        bot.send_message(m.chat.id, f"🌑 Добро пожаловать, {tg_name}.\nВам начислено: 💰 777,000 и 💎 10,000!\nВыберите класс:", reply_markup=markup, parse_mode="HTML")
    conn.close()

@bot.message_handler(func=lambda m: m.text == "👤 Статы")
def profile_stats(m):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT name, class, lvl, exp, atk, deff, gold, crystals FROM players WHERE uid=?", (m.chat.id,))
    p = c.fetchone()
    if p:
        total_atk, total_deff = get_total_stats(m.chat.id, c)
        total_hp = 100 + (p[2] * 20) + (total_deff * 5)
        msg = f"👤 <b>Игрок:</b> {p[0]}\n🛡️ <b>Класс:</b> {p[1]}\n❤️ <b>HP:</b> {total_hp}\n⚔️ <b>Атака:</b> {total_atk}\n💰 <b>Золото:</b> {p[6]}\n💎 <b>Кристаллы:</b> {p[7]}"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔄 Сменить класс (10,000 💎)", callback_data="buy_class_change"))
        bot.send_message(m.chat.id, msg, reply_markup=markup, parse_mode="HTML")
    conn.close()

@bot.message_handler(func=lambda m: m.text == "🛒 Maгaзин / Донат")
def shop_menu(m):
    text = "🛒 <b>Магазин</b>\n💰 Курс: 100 💎 = 1 TON"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💎 100 Кристаллов (1 TON)", callback_data="donate_100"))
    bot.send_message(m.chat.id, text, reply_markup=markup, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "💎 Гача")
def gacha_menu(m):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT crystals FROM players WHERE uid=?", (m.chat.id,))
    crystals = c.fetchone()[0]
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔮 1 Крутка (100 💎)", callback_data="gacha_1"))
    bot.send_message(m.chat.id, f"💎 Твой баланс: {crystals}", reply_markup=markup)
    conn.close()

@bot.message_handler(func=lambda m: m.text == "🎒 Инвентарь")
def inventory_menu(m): send_inventory(m.chat.id)

def send_inventory(uid, message_id=None):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id, item_name, grade, item_atk, item_deff FROM inventory WHERE uid=?", (uid,))
    items = c.fetchall()
    text = "🎒 <b>Твой инвентарь:</b>\n" + "\n".join([f"{GRADES[i[2]]} {i[1]}" for i in items])
    if message_id: bot.edit_message_text(text, uid, message_id, parse_mode="HTML")
    else: bot.send_message(uid, text, parse_mode="HTML")
    conn.close()

@bot.message_handler(func=lambda m: m.text == "🤖 Охота (АФК)")
def hunt_menu(m):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🌍 1 час охоты", callback_data="starthunt_1"))
    bot.send_message(m.chat.id, "🗺️ Выберите зону:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🥊 Арена PvP")
def pvp_arena(m):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT name FROM players WHERE uid != ? ORDER BY RANDOM() LIMIT 1", (m.chat.id,))
    opp = c.fetchone()
    if opp: bot.send_message(m.chat.id, f"⚔️ Ты сразился с {opp[0]} и победил!")
    conn.close()

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    uid = call.from_user.id
    conn = get_db(); c = conn.cursor()
    if call.data.startswith("setcls_"):
        cls = call.data.split("_")[1]
        c.execute("UPDATE players SET class=? WHERE uid=?", (cls, uid))
        conn.commit(); bot.send_message(uid, f"Класс {cls} выбран!")
    elif call.data == "gacha_1":
        c.execute("UPDATE players SET crystals=crystals-100 WHERE uid=?", (uid,))
        conn.commit(); bot.send_message(uid, "🔮 Предмет получен!")
    conn.close()

if __name__ == '__main__':
    t = Thread(target=run_web)
    t.start()
    while True:
        try: bot.polling(none_stop=True, interval=2, timeout=40)
        except Exception: time.sleep(5)
            
