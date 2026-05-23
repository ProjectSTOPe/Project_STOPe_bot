import telebot, sqlite3, json, ui_manager, combat_engine
from telebot import types

TOKEN = '8840112637:AAHKDM7xiUQlw9c4o_z79dTeIqs4jJtWLVc'
bot = telebot.TeleBot(TOKEN)

# Загрузка JSON данных
def load_data(name):
    try:
        with open(f'{name}.json', 'r', encoding='utf-8') as f: return json.load(f)
    except: return {}

DUNGEONS = load_data('data_dungeons')

@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "Добро пожаловать в Project STOPe!", reply_markup=ui_manager.get_main_menu())

@bot.message_handler(func=lambda m: m.text == "👤 Герой")
def hero(m):
    conn = sqlite3.connect('stope_v2.db')
    c = conn.cursor()
    c.execute("SELECT name, level, strength, dexterity, luck, vitality, gold FROM players WHERE uid=?", (m.chat.id,))
    p = c.fetchone()
    if p:
        bot.send_message(m.chat.id, ui_manager.format_hero_stats(p), parse_mode="HTML")
    else:
        bot.send_message(m.chat.id, "Персонаж не найден. Введите /start")
    conn.close()

@bot.message_handler(func=lambda m: m.text == "🌿 Подземелья")
def show_dungeons(m):
    bot.send_message(m.chat.id, "Выберите локацию:", reply_markup=ui_manager.get_dungeon_menu(DUNGEONS))

# Обработка входа в данж (БК-стайл: выбор зоны)
@bot.callback_query_handler(func=lambda call: call.data.startswith("dng_"))
def start_dungeon_fight(call):
    d_name = call.data.split("_")[1]
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("⚔️ Голова", callback_data=f"hit_Голова_{d_name}"),
        types.InlineKeyboardButton("⚔️ Грудь", callback_data=f"hit_Грудь_{d_name}"),
        types.InlineKeyboardButton("⚔️ Пояс", callback_data=f"hit_Пояс_{d_name}"),
        types.InlineKeyboardButton("⚔️ Ноги", callback_data=f"hit_Ноги_{d_name}")
    )
    bot.edit_message_text(f"⚔️ Вы в {d_name}. Куда ударить?", 
                          call.message.chat.id, call.message.message_id, reply_markup=markup)

# Обработка удара
@bot.callback_query_handler(func=lambda call: call.data.startswith("hit_"))
def process_hit(call):
    # Тут будет вызов combat_engine.calculate_fight
    zone = call.data.split("_")[1]
    bot.answer_callback_query(call.id, f"Вы нанесли удар в {zone}!")
    bot.edit_message_text(f"💥 Удар в {zone} успешно прошел!", call.message.chat.id, call.message.message_id)

if __name__ == '__main__':
    bot.remove_webhook()
    bot.polling(none_stop=True, interval=0)
    
