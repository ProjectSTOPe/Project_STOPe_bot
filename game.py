import telebot, sqlite3, os, random
from telebot import types
from flask import Flask
from threading import Thread

TOKEN = '8840112637:AAHKDM7xiUQlw9c4o_z79dTeIqs4jJtWLVc'
bot = telebot.TeleBot(TOKEN)
bot.remove_webhook()
app = Flask('')

# --- КОНФИГ ---
CLASSES = {
    "Ассасин": {"atk": 15, "dex": 20, "luck": 25, "hp": 100, "passive": "Крит. удар +8%"},
    "Авангард": {"atk": 10, "dex": 10, "luck": 10, "hp": 200, "passive": "Снижение урона -10%"},
    "Маг": {"atk": 25, "deff": 8, "luck": 15, "hp": 80, "passive": "+10% к урону, -5% защиты"}
}

def get_exp_for_level(lvl): return int(100 * (lvl ** 1.5))

# --- ЯДРО БОЯ ---
def calculate_fight(player, monster_lvl):
    # Упрощенная механика БК: (Сила + Рандом) - Защита
    p_dmg = player[3] + random.randint(1, 10)
    m_dmg = monster_lvl * 5 + random.randint(1, 5)
    return p_dmg, m_dmg

# --- ОБНОВЛЕННАЯ БАЗА ---
def init_db():
    conn = sqlite3.connect('stope_v2.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS players 
                 (uid INTEGER PRIMARY KEY, name TEXT, class TEXT, level INTEGER DEFAULT 1, exp INTEGER DEFAULT 0,
                  strength INTEGER DEFAULT 10, dexterity INTEGER DEFAULT 10, luck INTEGER DEFAULT 10, 
                  vitality INTEGER DEFAULT 10, points INTEGER DEFAULT 5, gold INTEGER DEFAULT 777000)''')
    conn.commit(); conn.close()
init_db()

# --- ЛОГИКА ДАНЖА С БОЕМ ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("dng_"))
def enter_dungeon(call):
    d_name = call.data.split("_")[1]
    conn = sqlite3.connect('stope_v2.db')
    c = conn.cursor()
    c.execute("SELECT strength, dexterity, luck, vitality, level, exp FROM players WHERE uid=?", (call.from_user.id,))
    p = c.fetchone()
    
    # Симуляция 3-х раундов боя
    p_dmg, m_dmg = calculate_fight(p, 1)
    
    if p_dmg > m_dmg:
        xp_gain = 50
        new_exp = p[5] + xp_gain
        # Проверка повышения уровня
        next_lvl_exp = get_exp_for_level(p[4])
        lvl_up = "📈 Уровень повышен!" if new_exp >= next_lvl_exp else ""
        
        c.execute("UPDATE players SET exp = ?, level = level + ? WHERE uid=?", 
                  (new_exp, (1 if new_exp >= next_lvl_exp else 0), call.from_user.id))
        conn.commit()
        bot.edit_message_text(f"⚔️ Победа в {d_name}!\nВы нанесли {p_dmg}, монстр {m_dmg}.\n+50 XP. {lvl_up}", 
                              call.message.chat.id, call.message.message_id)
    else:
        bot.edit_message_text("💀 Вы проиграли бой в данже.", call.message.chat.id, call.message.message_id)
    conn.close()

# (Остальной функционал start, hero_stats, add_stats оставляем прежним)
# ...
