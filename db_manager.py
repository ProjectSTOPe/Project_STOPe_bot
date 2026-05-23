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
