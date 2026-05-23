import telebot, sqlite3, json, ui_manager # Импортируем наш дизайн

bot = telebot.TeleBot('8840112637:AAHKDM7xiUQlw9c4o_z79dTeIqs4jJtWLVc')

# Загрузка данных
def load_data(name):
    with open(f'{name}.json', 'r', encoding='utf-8') as f: return json.load(f)

DUNGEONS = load_data('data_dungeons')

@bot.message_handler(commands=['start'])
def start(m):
    # Используем ui_manager для вывода меню
    bot.send_message(m.chat.id, "Добро пожаловать в Project STOPe!", reply_markup=ui_manager.get_main_menu())

@bot.message_handler(func=lambda m: m.text == "🌿 Подземелья")
def show_dungeons(m):
    # Используем ui_manager для списка данжей
    bot.send_message(m.chat.id, "Выберите локацию:", reply_markup=ui_manager.get_dungeon_menu(DUNGEONS))

@bot.message_handler(func=lambda m: m.text == "👤 Герой")
def hero(m):
    conn = sqlite3.connect('stope_v2.db')
    c = conn.cursor()
    c.execute("SELECT name, level, strength, dexterity, luck, vitality, gold FROM players WHERE uid=?", (m.chat.id,))
    p = c.fetchone()
    # Используем ui_manager для красивого оформления статов
    bot.send_message(m.chat.id, ui_manager.format_hero_stats(p), parse_mode="HTML")
    conn.close()

bot.polling(none_stop=True)
