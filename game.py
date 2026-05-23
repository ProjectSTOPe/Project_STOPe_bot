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

@bot.message_handler(func=lambda m: m.text == "💪 Тренировка")
def train(m):
    result = db_manager.buy_strength(m.chat.id)
    bot.send_message(m.chat.id, result)

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

@bot.message_handler(commands=['get_sword'])
def get_sword(m):
    # Пример выдачи меча (+5 к силе)
    db_manager.add_item(m.chat.id, "Стальной меч", 5)
    bot.send_message(m.chat.id, "Ты получил Стальной меч! (+5 к силе)")

@bot.message_handler(func=lambda m: m.text == "⚔️ Арена")
def arena(m):
    opponent = db_manager.get_random_opponent(m.chat.id)
    if not opponent:
        bot.send_message(m.chat.id, "Нет доступных противников.")
        return
    
    is_win = combat.run_pvp(m.chat.id, opponent[0])
    if is_win:
        bot.send_message(m.chat.id, f"🏆 Ты победил {opponent[1]} на арене!")
    else:
        bot.send_message(m.chat.id, f"❌ Ты проиграл {opponent[1]} на арене.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def shop_purchase(call):
    uid = call.message.chat.id
    if call.data == "buy_sword":
        success = db_manager.buy_item(uid, "Меч", 500, 10)
    
    if success:
        bot.answer_callback_query(call.id, "Куплено!")
    else:
        bot.answer_callback_query(call.id, "Не хватает золота!")

@bot.callback_query_handler(func=lambda call: call.data.startswith("class_"))
def choose_class(call):
    class_map = {"class_warrior": "Воин", "class_mage": "Маг"}
    db_manager.set_player_class(call.message.chat.id, class_map[call.data])
    bot.edit_message_text(f"Выбран класс: {class_map[call.data]}", call.message.chat.id, call.message.message_id)
    
@bot.callback_query_handler(func=lambda call: call.data.startswith("dng_"))
def handle_dungeon(call):
    if not combat.can_fight(call.message.chat.id):
        bot.answer_callback_query(call.id, "Отдохни, герой! Подожди 10 сек.")
        return
        
    dungeon_lvl = int(call.data.split("_")[1])
    msg = combat.run_battle(call.message.chat.id, dungeon_lvl)
    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id)
    
