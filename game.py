import telebot, sqlite3, os, json, random
from telebot import types
from flask import Flask
from threading import Thread
import combat_engine # Наш отдельный файл с логикой боя

TOKEN = '8840112637:AAHKDM7xiUQlw9c4o_z79dTeIqs4jJtWLVc'
bot = telebot.TeleBot(TOKEN)
bot.remove_webhook()
app = Flask('')

# Загрузка данных из внешних JSON
def load_json(name):
    with open(f'{name}.json', 'r', encoding='utf-8') as f: return json.load(f)

CLASSES = load_json('data_classes')
DUNGEONS = load_json('data_dungeons')

@app.route('/')
def home(): return "Project STOPe is running"

def run_web(): app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# База данных (упрощенная)
def init_db():
    conn = sqlite3.connect('stope_v2.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS players 
                 (uid INTEGER PRIMARY KEY, name TEXT, class TEXT, level INTEGER DEFAULT 1, 
                  strength INTEGER DEFAULT 10, dexterity INTEGER DEFAULT 10, luck INTEGER DEFAULT 10, 
                  vitality INTEGER DEFAULT 10, gold INTEGER DEFAULT 777000)''')
    conn.commit(); conn.close()
init_db()

# Основное меню
@bot.message_handler(commands=['start'])
def main_menu(m):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("⚔️ PvP", "🌿 Подземелья", "👤 Герой")
    bot.send_message(m.chat.id, "Добро пожаловать в Project STOPe", reply_markup=markup)

# Пример использования внешнего модуля боя
@bot.message_handler(func=lambda m: m.text == "🌿 Подземелья")
def dungeon_menu(m):
    # Тут логика выбора подземелья из DUNGEONS
    pass

if __name__ == '__main__':
    Thread(target=run_web).start()
    bot.polling(none_stop=True)
    
