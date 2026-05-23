import telebot, sqlite3, json, ui_manager, combat_engine
from telebot import types

TOKEN = '8840112637:AAHKDM7xiUQlw9c4o_z79dTeIqs4jJtWLVc'
bot = telebot.TeleBot(TOKEN)

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
    c.execute("SELECT name, level, strength, dexterity, luck, vitality, gold, class FROM players WHERE uid=?", (m.chat.id,))
    p = c.fetchone()
    if p:
        bot.send_message(m.chat.id, ui_manager.format_hero_stats(p), parse_mode="HTML")
    else:
        bot.send_message(m.chat.id, "Персонаж не найден.")
    conn.close()

@bot.message_handler(func=lambda m: m.text == "🌿 Подземелья")
def show_dungeons(m):
    bot.send_message(m.chat.id, "Выберите локацию:", reply_markup=ui_manager.get_dungeon_menu(DUNGEONS))

@bot.callback_query_handler(func=lambda call: call.data.startswith("dng_"))
def auto_fight(call):
    conn = sqlite3.connect('stope_v2.db')
    c = conn.cursor()
    c.execute("SELECT strength, luck, class FROM players WHERE uid=?", (call.message.chat.id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        bot.answer_callback_query(call.id, "Создайте персонажа!")
        return

    p_stats = {'strength': row[0], 'luck': row[1], 'class': row[2]}
    dmg, is_crit = combat_engine.calculate_fight(p_stats)
    
    msg = f"⚔️ Бой завершен!\n💥 Урон: {dmg}" + (" (КРИТ!)" if is_crit else "")
    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id)

if __name__ == '__main__':
    bot.remove_webhook()
    bot.polling(none_stop=True, interval=0)
    
