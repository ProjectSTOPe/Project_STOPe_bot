import sqlite3
import config

def get_db():
    return sqlite3.connect('stope_v2.db', check_same_thread=False)

def init_db():
    conn = get_db()
    c = conn.cursor()
    # Таблица игроков
    c.execute("""CREATE TABLE IF NOT EXISTS players 
                 (uid INTEGER PRIMARY KEY, name TEXT, lvl INTEGER, exp INTEGER, gold INTEGER, 
                  str INTEGER, dex INTEGER, luk INTEGER, vit INTEGER, class TEXT)""")
    # Таблица вещей
    c.execute("""CREATE TABLE IF NOT EXISTS inventory 
                 (uid INTEGER, item_name TEXT, str_bonus INTEGER)""")
    # Таблица логов
    c.execute('''CREATE TABLE IF NOT EXISTS logs 
                 (id INTEGER PRIMARY KEY, uid INTEGER, action TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def get_stats():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*), SUM(gold) FROM players")
    data = c.fetchone()
    conn.close()
    return data[0] or 0, data[1] or 0

def give_gold(uid, amount):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE players SET gold = gold + ? WHERE uid=?", (amount, uid))
    conn.commit()
    conn.close()

def buy_strength(uid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT gold FROM players WHERE uid=?", (uid,))
    gold = c.fetchone()[0]
    if gold >= 100:
        c.execute("UPDATE players SET gold = gold - 100, str = str + 2 WHERE uid=?", (uid,))
        conn.commit()
        conn.close()
        return "✅ Сила увеличена на +2!"
    conn.close()
    return "❌ Недостаточно золота (нужно 100)!"

def check_level_up(uid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT lvl, exp FROM players WHERE uid=?", (uid,))
    p = c.fetchone()
    if p:
        lvl, exp = p
        if exp >= lvl * 100:
            c.execute("UPDATE players SET lvl = lvl + 1, exp = 0 WHERE uid=?", (uid,))
            conn.commit()
            conn.close()
            return True
    conn.close()
    return False

def add_item(uid, item_name, str_bonus):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO inventory (uid, item_name, str_bonus) VALUES (?, ?, ?)", (uid, item_name, str_bonus))
    conn.commit()
    conn.close()

def get_total_str(uid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT str FROM players WHERE uid=?", (uid,))
    row = c.fetchone()
    base_str = row[0] if row else 10
    c.execute("SELECT SUM(str_bonus) FROM inventory WHERE uid=?", (uid,))
    bonus = c.fetchone()[0] or 0
    conn.close()
    return base_str + bonus

def get_random_opponent(uid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT uid, name FROM players WHERE uid != ? ORDER BY RANDOM() LIMIT 1", (uid,))
    opponent = c.fetchone()
    conn.close()
    return opponent

def buy_item(uid, item_name, cost, bonus):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT gold FROM players WHERE uid=?", (uid,))
    gold = c.fetchone()[0]
    if gold >= cost:
        c.execute("UPDATE players SET gold = gold - ? WHERE uid=?", (cost, uid))
        c.execute("INSERT INTO inventory (uid, item_name, str_bonus) VALUES (?, ?, ?)", (uid, item_name, bonus))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def set_player_class(uid, class_name):
    # Теперь берем статы из config.py
    stats = config.CLASSES.get(class_name, {"atk": 15, "dex": 10, "luk": 10, "hp": 100})
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE players SET class = ?, str = ?, dex = ?, luk = ?, vit = ? WHERE uid = ?", 
              (class_name, stats['atk'], stats['dex'], stats['luck'], stats['hp'], uid))
    conn.commit()
    conn.close()

def log_action(uid, action):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO logs (uid, action) VALUES (?, ?)", (uid, action))
    conn.commit()
    conn.close()
    
