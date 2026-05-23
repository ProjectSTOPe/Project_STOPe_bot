import sqlite3

def get_db():
    return sqlite3.connect('stope_v2.db', check_same_thread=False)

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS players
                 (uid INTEGER PRIMARY KEY, name TEXT, lvl INTEGER, exp INTEGER, gold INTEGER,
                  str INTEGER, dex INTEGER, luk INTEGER, vit INTEGER, class TEXT)""")
    conn.commit()
    conn.close()
    
def buy_strength(uid):
    conn = get_db()
    c = conn.cursor()
    # Проверяем золото
    c.execute("SELECT gold, str FROM players WHERE uid=?", (uid,))
    p = c.fetchone()
    if p and p[0] >= 100: # Стоимость 100 золота
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
        # Формула: 100 опыта на уровень
        if exp >= lvl * 100:
            c.execute("UPDATE players SET lvl = lvl + 1, exp = 0 WHERE uid=?", (uid,))
            conn.commit()
            conn.close()
            return True
    conn.close()
    return False

def init_db():
    conn = get_db()
    c = conn.cursor()
    # Таблица игроков
    c.execute("""CREATE TABLE IF NOT EXISTS players 
                 (uid INTEGER PRIMARY KEY, name TEXT, lvl INTEGER, exp INTEGER, gold INTEGER, 
                  str INTEGER, dex INTEGER, luk INTEGER, vit INTEGER, class TEXT)""")
    # Таблица вещей (инвентарь)
    c.execute("""CREATE TABLE IF NOT EXISTS inventory 
                 (uid INTEGER, item_name TEXT, str_bonus INTEGER)""")
    conn.commit()
    conn.close()

def add_item(uid, item_name, str_bonus):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO inventory VALUES (?, ?, ?)", (uid, item_name, str_bonus))
    conn.commit()
    conn.close()

def get_total_str(uid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT str FROM players WHERE uid=?", (uid,))
    base_str = c.fetchone()[0]
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
        c.execute("INSERT INTO inventory VALUES (?, ?, ?)", (uid, item_name, bonus))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def set_player_class(uid, class_name):
    conn = get_db()
    c = conn.cursor()
    # Уникальные бонусы для классов
    stats = {"Воин": (20, 5), "Маг": (10, 15)} # (str, vit)
    str_val, vit_val = stats.get(class_name, (15, 10))
    
    c.execute("UPDATE players SET class = ?, str = ?, vit = ? WHERE uid = ?", 
              (class_name, str_val, vit_val, uid))
    conn.commit()
    conn.close()
    
    
    
