from telebot import types

def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("⚔️ PvP", "🌿 Подземелья", "👤 Герой", "🎒 Инвентарь")
    return markup

def get_dungeon_menu(dungeons):
    markup = types.InlineKeyboardMarkup()
    for d_name in dungeons.keys():
        markup.add(types.InlineKeyboardButton(f"🏰 {d_name}", callback_data=f"dng_{d_name}"))
    return markup

def format_hero_stats(p):
    return (f"👤 <b>ГЕРОЙ: {p[0]}</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"📈 Уровень: {p[1]}\n"
            f"⚔️ Сила: {p[2]} | 🏃 Ловкость: {p[3]}\n"
            f"🍀 Удача: {p[4]} | ❤️ Здоровье: {p[5]}\n"
            f"💰 Золото: {p[6]}\n"
            f"🛡 Класс: {p[7]}")

def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🌿 Подземелья", "👤 Герой", "💪 Тренировка") # Добавили кнопку
    return markup

def get_shop_menu():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🗡 Меч (+10 стр) - 500г", callback_data="buy_sword"))
    markup.add(types.InlineKeyboardButton("🛡 Щит (+10 вит) - 500г", callback_data="buy_shield"))
    return markup

def get_class_menu():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⚔️ Воин", callback_data="class_warrior"))
    markup.add(types.InlineKeyboardButton("🔮 Маг", callback_data="class_mage"))
    return markup
    
