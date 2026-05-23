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
    
    
