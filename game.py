import telebot
import db_manager
import ui_manager
import combat
from telebot import types

# Инициализация
TOKEN = '8840112637:AAHKDM7xiUQlw9c4o_z79dTeIqs4jJtWLVc'
bot = telebot.TeleBot(TOKEN)

# При запуске проверяем базу
db_manager.init_db()

@bot.message_handler(commands=['start'])
def start(m):
    # Создаем персонажа, если его нет
    conn = db_manager.get_db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO players VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
              (m.chat.id, "Герой", 1, 0, 100, 15, 10, 10, 10, "Воин"))
    conn.commit()
    conn.close()
    bot.send_message(m.chat.id, "Добро пожаловать в Project STOPe!", reply_markup=ui_manager.get_main_menu())

@bot.message_handler(func=lambda m: m.text == "👤 Герой")
def show_hero(m):
    conn = db_manager.get_db()
    c = conn.cursor()
    c.execute("SELECT name, lvl, exp, gold, str, dex, luk, vit, class FROM players WHERE uid=?", (m.chat.id,))
    p = c.fetchone()
    conn.close()
    if p:
        msg = (f"👤 {p[0]} (Уровень: {p[1]})\n"
               f"⚔️ Сила: {p[4]} | 🍀 Удача: {p[6]}\n"
               f"💰 Золото: {p[3]} | 📈 Опыт: {p[2]}")
        bot.send_message(m.chat.id, msg)

@bot.message_handler(func=lambda m: m.text == "🌿 Подземелья")
def show_dungeons(m):
    bot.send_message(m.chat.id, "Выберите уровень подземелья:", reply_markup=ui_manager.get_dungeon_menu())

@bot.callback_query_handler(func=lambda call: call.data.startswith("dng_"))
def handle_dungeon(call):
    # Берем уровень данжа из callback_data (например, dng_1 -> 1)
    dungeon_lvl = int(call.data.split("_")[1])
    
    # Запускаем бой через движок combat.py
    msg = combat.run_battle(call.message.chat.id, dungeon_lvl)
    
    # Редактируем сообщение с результатом
    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id)

if __name__ == '__main__':
    bot.remove_webhook()
    bot.polling(none_stop=True)
    
