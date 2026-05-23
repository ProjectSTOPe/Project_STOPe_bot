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
@bot.callback_query_handler(func=lambda call: call.data.startswith("dng_"))
def start_dungeon_fight(call):
    d_name = call.data.split("_")[1]
    # Создаем кнопки зон удара (БК-стайл)
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("⚔️ Голова", callback_data=f"hit_Голова_{d_name}"),
        types.InlineKeyboardButton("⚔️ Грудь", callback_data=f"hit_Грудь_{d_name}"),
        types.InlineKeyboardButton("⚔️ Пояс", callback_data=f"hit_Пояс_{d_name}"),
        types.InlineKeyboardButton("⚔️ Ноги", callback_data=f"hit_Ноги_{d_name}")
    )
    bot.edit_message_text(f"⚔️ Вы вошли в {d_name}. Куда наносим первый удар?", 
                          call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("hit_"))
def process_hit(call):
    data = call.data.split("_")
    zone = data[1]
    d_name = data[2]
    
    # 1. Загружаем статы игрока из БД (нужно будет сделать SELECT)
    # 2. Вызываем функцию из combat_engine.py
    # import combat_engine
    # result, damage = combat_engine.calculate_fight(player_stats, monster_stats, zone, "Голова")
    
    bot.edit_message_text(f"💥 Вы ударили в {zone}! Результат: {damage} урона.", 
                          call.message.chat.id, call.message.message_id)
    
