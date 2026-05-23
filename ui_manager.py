from telebot import types
import config

def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    # Собираем всё в одном месте
    markup.add("⚔️ Арена", "🌿 Подземелья", "👤 Герой", "💪 Тренировка")
    return markup

def get_dungeon_menu():
    markup = types.InlineKeyboardMarkup()
    # Берем список подземелий из конфига
    for d_name in config.DUNGEONS.keys():
        markup.add(types.InlineKeyboardButton(f"🏰 {d_name}", callback_data=f"dng_{d_name}"))
    return markup

def format_hero_stats(p):
    # p — это кортеж с данными из БД
    return (f"👤 <b>ГЕРОЙ: {p[0]}</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"📈 Уровень: {p[1]}\n"
            f"⚔️ Сила: {p[4]} | 🍀 Удача: {p[6]}\n"
            f"💰 Золото: {p[3]} | 🛡 Класс: {p[8]}")

def get_shop_menu():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🗡 Меч (+10 стр) - 500г", callback_data="buy_sword"))
    markup.add(types.InlineKeyboardButton("🛡 Щит (+10 вит) - 500г", callback_data="buy_shield"))
    return markup

def get_class_menu():
    markup = types.InlineKeyboardMarkup()
    # Добавили все классы из конфига
    for class_name in config.CLASSES.keys():
        markup.add(types.InlineKeyboardButton(f"👤 {class_name}", callback_data=f"class_{class_name}"))
    return markup
    
