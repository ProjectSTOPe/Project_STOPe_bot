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
    # p - это кортеж из БД
    return (f"👤 <b>ГЕРОЙ: {p[0]}</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"📈 Уровень: {p[1]}\n"
            f"⚔️ Сила: {p[2]} | 🏃 Ловкость: {p[3]}\n"
            f"🍀 Удача: {p[4]} | ❤️ Здоровье: {p[5]}\n"
            f"💰 Золото: {p[6]}")
