import asyncio
import json
import os
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "8824282617:AAF-4RmuPwJDMudFzzTjaf2koXvvBo1KlP4"
SAVE_FILE = "game_save.json"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- СИСТЕМА СОХРАНЕНИЙ ---
def load_game():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r") as f: return json.load(f)
    return {}

def save_game(data):
    with open(SAVE_FILE, "w") as f: json.dump(data, f)

user_data = load_game()

# --- ИГРОВЫЕ ФУНКЦИИ ---
def add_xp(user_id, amount):
    uid = str(user_id)
    if uid not in user_data: return
    user = user_data[uid]
    user["xp"] = user.get("xp", 0) + amount
    if user["xp"] >= 100:
        user["level"] += 1
        user["xp"] -= 100
        user["max_hp"] += 10
        user["hp"] = user["max_hp"] # Полное исцеление при левелапе
        user["strength"] += 2
    save_game(user_data)

# --- КЛАВИАТУРЫ (МЕНЮ) ---
def get_game_kb(state="main"):
    kb = []
    if state == "combat":
        kb.append([InlineKeyboardButton(text="⚔️ Атаковать", callback_data="attack"), InlineKeyboardButton(text="🏃 Сбежать", callback_data="flee")])
        kb.append([InlineKeyboardButton(text="💊 Выпить зелье", callback_data="combat_heal")])
    elif state == "shop":
        kb.append([InlineKeyboardButton(text="💊 Купить зелье (25з)", callback_data="buy_potion")])
        kb.append([InlineKeyboardButton(text="🗡 Улучшить меч (100з)", callback_data="buy_weapon")])
        kb.append([InlineKeyboardButton(text="🛡 Улучшить броню (100з)", callback_data="buy_armor")])
        kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])
    elif state == "inventory":
        kb.append([InlineKeyboardButton(text="💊 Использовать зелье", callback_data="use_potion")])
        kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])
    else: # main
        kb.append([InlineKeyboardButton(text="⬆️", callback_data="move_up"), InlineKeyboardButton(text="⬇️", callback_data="move_down")])
        kb.append([InlineKeyboardButton(text="⬅️", callback_data="move_left"), InlineKeyboardButton(text="➡️", callback_data="move_right")])
        kb.append([InlineKeyboardButton(text="🎒 Инвентарь", callback_data="menu_inv"), InlineKeyboardButton(text="🏪 Магазин", callback_data="menu_shop")])
        kb.append([InlineKeyboardButton(text="📊 Статус", callback_data="status")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- СТАРТ ИГРЫ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id not in user_data:
        # Добавили max_hp, potions, armor, weapon
        user_data[user_id] = {
            "name": message.from_user.first_name, "hp": 30, "max_hp": 30, "strength": 5, "armor": 0, "weapon": 0,
            "gold": 100, "level": 1, "xp": 0, "x": 0, "y": 0, "potions": 3, "enemy_hp": 0
        }
        save_game(user_data)
    await message.answer("Добро пожаловать в Project STOPe!\nВы находитесь в стартовом лагере.", reply_markup=get_game_kb("main"))

# --- ПЕРЕМЕЩЕНИЕ И ГЕНЕРАЦИЯ МИРА ---
@dp.callback_query(F.data.startswith("move_"))
async def callback_move(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data[user_id]
    
    if p.get('enemy_hp', 0) > 0:
        await callback.answer("Вы в бою! Нельзя просто уйти.")
        return

    locs = ["Темный Лес", "Заброшенные Шахты", "Кровавое Болото", "Руины Древних"]
    direction = callback.data.split("_")[1]
    
    if direction == "up": p['y'] -= 1
    elif direction == "down": p['y'] += 1
    elif direction == "left": p['x'] -= 1
    elif direction == "right": p['x'] += 1
    
    # 35% шанс встретить монстра
    if random.random() < 0.35:
        p['enemy_hp'] = random.randint(15 + p['level']*5, 25 + p['level']*8)
        await callback.message.edit_text(f"⚠️ Из засады нападает монстр! HP врага: {p['enemy_hp']}", reply_markup=get_game_kb("combat"))
    else:
        # Если координаты 0:0 - это город
        if p['x'] == 0 and p['y'] == 0:
            await callback.message.edit_text("🏙 Вы вернулись в безопасный город.", reply_markup=get_game_kb("main"))
        else:
            await callback.message.edit_text(f"Вы исследуете: {random.choice(locs)}\n📍 Координаты: {p['x']}:{p['y']}", reply_markup=get_game_kb("main"))
    save_game(user_data)

# --- БОЕВАЯ СИСТЕМА ---
@dp.callback_query(F.data == "attack")
async def callback_attack(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data[user_id]
    
    if p['enemy_hp'] <= 0: return

    # Урон игрока (базовая сила + заточка оружия)
    damage = random.randint(p['strength'], p['strength'] + 3) + (p['weapon'] * 2)
    p['enemy_hp'] -= damage
    
    if p['enemy_hp'] <= 0:
        gold_drop = random.randint(10, 25) + p['level'] * 2
        p['gold'] += gold_drop
        add_xp(user_id, 35)
        await callback.message.edit_text(f"Враг повержен! 🩸\nВы получили +{gold_drop} 💰 и +35 XP.", reply_markup=get_game_kb("main"))
    else:
        # Ответный удар монстра (с учетом брони игрока)
        monster_dmg = max(1, random.randint(3 + p['level'], 8 + p['level']) - p['armor'])
        p['hp'] -= monster_dmg
        
        # Проверка на смерть
        if p['hp'] <= 0:
            p['hp'] = p['max_hp']
            p['gold'] = max(0, p['gold'] - 50) # Штраф за смерть
            p['x'], p['y'] = 0, 0 # Возврат в город
            p['enemy_hp'] = 0
            await callback.message.edit_text("💀 Вы погибли!\nВы потеряли часть золота и очнулись в городе.", reply_markup=get_game_kb("main"))
        else:
            await callback.message.edit_text(f"⚔️ Вы нанесли {damage} урона.\n👹 Враг ударил вас на {monster_dmg} урона.\n\nВаше здоровье: {p['hp']}/{p['max_hp']} ❤️\nЗдоровье врага: {p['enemy_hp']}", reply_markup=get_game_kb("combat"))
    save_game(user_data)

@dp.callback_query(F.data == "flee")
async def callback_flee(callback: types.CallbackQuery):
    p = user_data[str(callback.from_user.id)]
    if random.random() < 0.5: # 50% шанс сбежать
        p['enemy_hp'] = 0
        await callback.message.edit_text("🏃 Вы успешно сбежали от монстра!", reply_markup=get_game_kb("main"))
    else:
        monster_dmg = max(1, random.randint(5, 10) - p['armor'])
        p['hp'] -= monster_dmg
        if p['hp'] <= 0:
            p['hp'] = p['max_hp']
            p['x'], p['y'], p['enemy_hp'] = 0, 0, 0
            await callback.message.edit_text("💀 Вы споткнулись во время побега и монстр добил вас...", reply_markup=get_game_kb("main"))
        else:
            await callback.message.edit_text(f"❌ Побег не удался! Враг бьет в спину на {monster_dmg} урона.\nВаше здоровье: {p['hp']}/{p['max_hp']} ❤️", reply_markup=get_game_kb("combat"))
    save_game(user_data)

# --- ИНВЕНТАРЬ И ХИЛ ---
@dp.callback_query(F.data == "menu_inv")
async def menu_inv(callback: types.CallbackQuery):
    p = user_data[str(callback.from_user.id)]
    await callback.message.edit_text(f"🎒 Ваш инвентарь:\nЗелья здоровья (лечат 20 HP): {p['potions']} шт.", reply_markup=get_game_kb("inventory"))

@dp.callback_query(F.data.in_(["use_potion", "combat_heal"]))
async def use_potion(callback: types.CallbackQuery):
    p = user_data[str(callback.from_user.id)]
    if p['potions'] > 0:
        if p['hp'] == p['max_hp']:
            await callback.answer("У вас и так полное здоровье!")
            return
        p['potions'] -= 1
        p['hp'] = min(p['max_hp'], p['hp'] + 20)
        save_game(user_data)
        if callback.data == "combat_heal":
            await callback.message.edit_text(f"🧪 Вы выпили зелье (+20 HP).\nВаше здоровье: {p['hp']}/{p['max_hp']} ❤️\nЗдоровье врага: {p['enemy_hp']}", reply_markup=get_game_kb("combat"))
        else:
            await callback.message.edit_text(f"🧪 Вы выпили зелье. Здоровье: {p['hp']}/{p['max_hp']} ❤️\nОсталось зелий: {p['potions']}", reply_markup=get_game_kb("inventory"))
    else:
        await callback.answer("У вас нет зелий!")

# --- МАГАЗИН ---
@dp.callback_query(F.data == "menu_shop")
async def menu_shop(callback: types.CallbackQuery):
    p = user_data[str(callback.from_user.id)]
    if p['x'] != 0 or p['y'] != 0:
        await callback.answer("Магазин доступен только в городе (координаты 0:0)!")
        return
    await callback.message.edit_text(f"🏪 Торговец\nУ вас: {p['gold']} 💰\nЧто желаете приобрести?", reply_markup=get_game_kb("shop"))

@dp.callback_query(F.data.startswith("buy_"))
async def buy_item(callback: types.CallbackQuery):
    p = user_data[str(callback.from_user.id)]
    item = callback.data.split("_")[1]
    
    if item == "potion" and p['gold'] >= 25:
        p['gold'] -= 25
        p['potions'] += 1
        await callback.message.edit_text(f"✅ Вы купили зелье! У вас: {p['gold']} 💰\nЗелий: {p['potions']}", reply_markup=get_game_kb("shop"))
    elif item == "weapon" and p['gold'] >= 100:
        p['gold'] -= 100
        p['weapon'] += 1
        await callback.message.edit_text(f"✅ Вы заточили меч до уровня +{p['weapon']}! У вас: {p['gold']} 💰", reply_markup=get_game_kb("shop"))
    elif item == "armor" and p['gold'] >= 100:
        p['gold'] -= 100
        p['armor'] += 1
        await callback.message.edit_text(f"✅ Вы улучшили броню до уровня +{p['armor']}! У вас: {p['gold']} 💰", reply_markup=get_game_kb("shop"))
    else:
        await callback.answer("Недостаточно золота!")
    save_game(user_data)

# --- СТАТУС И НАВИГАЦИЯ ---
@dp.callback_query(F.data == "status")
async def callback_status(callback: types.CallbackQuery):
    p = user_data[str(callback.from_user.id)]
    status_text = (f"👤 Имя: {p['name']}\n"
                   f"🎖 Уровень: {p['level']} (XP: {p['xp']}/100)\n"
                   f"❤️ Здоровье: {p['hp']}/{p['max_hp']}\n"
                   f"⚔️ Сила (с мечом): {p['strength']} (+{p['weapon']*2})\n"
                   f"🛡 Броня: {p['armor']}\n"
                   f"💰 Золото: {p['gold']}\n"
                   f"📍 Локация: {p['x']}:{p['y']}")
    await callback.message.edit_text(status_text, reply_markup=get_game_kb("main"))

@dp.callback_query(F.data == "back_main")
async def back_main(callback: types.CallbackQuery):
    p = user_data[str(callback.from_user.id)]
    await callback.message.edit_text(f"📍 Вы на координатах {p['x']}:{p['y']}", reply_markup=get_game_kb("main"))

async def main():
    # Удаляем вебхуки и запускаем поллинг (drop_pending_updates чтобы избежать старых кликов)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
