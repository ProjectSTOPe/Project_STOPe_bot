import telebot, random, ui_manager, combat_engine
from telebot import types

bot = telebot.TeleBot('8840112637:AAHKDM7xiUQlw9c4o_z79dTeIqs4jJtWLVc')

@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "Добро пожаловать в Project STOPe!", reply_markup=ui_manager.get_main_menu())

@bot.message_handler(func=lambda m: m.text == "🌿 Подземелья")
def show_dungeons(m):
    # Вместо кнопок зон сразу предлагаем список данжей
    bot.send_message(m.chat.id, "Выберите подземелье, чтобы начать автоматический бой:", reply_markup=ui_manager.get_dungeon_menu({'Катакомбы': {}, 'Склеп': {}}))

@bot.callback_query_handler(func=lambda call: call.data.startswith("dng_"))
def auto_fight(call):
    # Рандомный выбор зоны за игрока
    zones = ["Голова", "Грудь", "Пояс", "Ноги"]
    p_zone = random.choice(zones)
    m_zone = random.choice(zones)
    
    # Расчет боя (упрощенно)
    dmg = combat_engine.calculate_fight({}, {}, p_zone)
    
    bot.edit_message_text(f"⚔️ Бой завершен!\nВы ударили в: {p_zone}\nУрон: {dmg}", 
                          call.message.chat.id, call.message.message_id)

if __name__ == '__main__':
    bot.remove_webhook()
    bot.polling(none_stop=True)
    
