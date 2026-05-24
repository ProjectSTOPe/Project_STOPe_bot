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

# --- СПРАВОЧНИКИ И НАСТРОЙКИ ГАЧИ ---
RARITIES = {
    "Common": {"name": "⚪ Обычный", "dust": 1, "mult": 1, "chance": 60},
    "Rare": {"name": "🔵 Редкий", "dust": 3, "mult": 2, "chance": 25},
    "Epic": {"name": "🟣 Эпический", "dust": 10, "mult": 4, "chance": 12},
    "Legendary": {"name": "🟠 Легендарный", "dust": 35, "mult": 8, "chance": 3}
}

ITEM_NAMES = {
    "weapon": ["Клинок Клятвы", "Посох Послушника", "Лук Ветров", "Убийца Драконов", "Громобой"],
    "armor": ["Мантия Мудреца", "Кожаный Жилет", "Тяжелый Доспех", "Латный Нагрудник"],
    "jewelry": ["Кольцо Всевластия", "Амулет Крови", "Ожерелье Света", "Серьга Удачи"]
}

# --- ПОДГРУЗКА ЭФФЕКТИВНЫХ ХАРАКТЕРИСТИК ---
def get_total_stats(p):
    s = {
        "max_hp": p.get("max_hp", 100),
        "strength": p.get("strength", 5),
        "agility": p.get("agility", 5),
        "intelligence": p.get("intelligence", 5),
        "defense": p.get("defense", 2)
    }
    for slot in ["weapon", "armor", "jewelry"]:
        item = p.get("equipped", {}).get(slot)
        if item:
            b_type = item["bonus_type"]
            val = item["bonus_value"] + (item.get("upgrade", 0) * 3)
            if b_type in s:
                s[b_type] += val
    return s

def add_xp(user_id, amount):
    uid = str(user_id)
    if uid not in user_data: return ""
    p = user_data[uid]
    
    if p["level"] >= 999:
        return "⚡ Достигнут макс. уровень (999)!"
        
    p["xp"] += amount
    lvl_up_msg = ""
    
    while p["xp"] >= p["level"] * 50:
        p["xp"] -= p["level"] * 50
        p["level"] += 1
        
        if p["class"] == "Маг":
            p["intelligence"] += 4
            p["max_hp"] += 8
            p["defense"] += 1
        elif p["class"] == "Лучник":
            p["agility"] += 4
            p["max_hp"] += 12
            p["defense"] += 1
        elif p["class"] == "Танк":
            p["strength"] += 4
            p["max_hp"] += 20
            p["defense"] += 3
            
        stats = get_total_stats(p)
        p["hp"] = stats["max_hp"]
        lvl_up_msg += f"\n🎉 **УРОВЕНЬ ПОВЫШЕН! Теперь вы {p['level']} уровня!** ❤️ ОЗ восстановлены."
        
        if p["level"] >= 999:
            p["level"] = 999
            p["xp"] = 0
            break
            
    save_game(user_data)
    return lvl_up_msg

def generate_item():
    roll = random.randint(1, 100)
    curr_chance = 0
    rarity_key = "Common"
    for k, v in RARITIES.items():
        curr_chance += v["chance"]
        if roll <= curr_chance:
            rarity_key = k
            break
            
    slot = random.choice(["weapon", "armor", "jewelry"])
    name = f"{RARITIES[rarity_key]['name']} {random.choice(ITEM_NAMES[slot])}"
    
    if slot == "weapon": b_type = random.choice(["strength", "agility", "intelligence"])
    elif slot == "armor": b_type = "defense"
    else: b_type = "max_hp"
        
    b_val = random.randint(3, 7) * RARITIES[rarity_key]["mult"]
    
    return {
        "name": name, "slot": slot, "rarity": rarity_key,
        "bonus_type": b_type, "bonus_value": b_val, "upgrade": 0
    }

# --- КЛАВИАТУРЫ ГЕЙМПЛЕЯ ---
def get_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬆️", callback_data="move_up"), InlineKeyboardButton(text="⬇️", callback_data="move_down"), 
         InlineKeyboardButton(text="⬅️", callback_data="move_left"), InlineKeyboardButton(text="➡️", callback_data="move_right")],
        [InlineKeyboardButton(text="🎒 Инвентарь", callback_data="menu_inv"), InlineKeyboardButton(text="🔮 Гача (50💎)", callback_data="gacha_pull")],
        [InlineKeyboardButton(text="📊 Статус", callback_data="status"), InlineKeyboardButton(text="💸 Тест-Донат", callback_data="test_donate")]
    ])

def get_class_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔮 Маг (Упор на Интеллект)", callback_data="choose_Маг")],
        [InlineKeyboardButton(text="🏹 Лучник (Упор на Ловкость)", callback_data="choose_Лучник")],
        [InlineKeyboardButton(text="🛡 Танк (Упор на Силу и ХП)", callback_data="choose_Танк")]
    ])

def get_combat_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Нанести Удар", callback_data="battle_hit"), InlineKeyboardButton(text="🏃 Сбежать", callback_data="battle_flee")]
    ])

# --- ЛОГИКА ОБРАБОТКИ СТАРТА ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = str(message.from_user.id)
    # Если это новый игрок или старый сейв без класса - сбрасываем прогресс для выбора класса
    if user_id not in user_data or user_data[user_id].get("class") is None:
        user_data[user_id] = {
            "name": message.from_user.first_name, "class": None, "level": 1, "xp": 0,
            "gold": 200, "crystals": 150, "dust": 0, "hp": 50, "max_hp": 50,
            "strength": 5, "agility": 5, "intelligence": 5, "defense": 2,
            "x": 10, "y": 10, "enemy_hp": 0, "enemy_max": 0, "enemy_type": "normal",
            "inventory": [], "equipped": {"weapon": None, "armor": None, "jewelry": None}
        }
        save_game(user_data)
        await message.answer("Добро пожаловать в мир Project STOPe!\nВыберите свой класс персонажа для начала приключения:", reply_markup=get_class_kb())
    else:
        await message.answer("Вы уже в игре! Продолжайте исследование:", reply_markup=get_main_kb())

@dp.callback_query(F.data.startswith("choose_"))
async def callback_class_select(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    selected_class = callback.data.split("_")[1]
    p = user_data[user_id]
    
    p["class"] = selected_class
    if selected_class == "Маг":
        p["intelligence"] = 15
        p["max_hp"] = 60
    elif selected_class == "Лучник":
        p["agility"] = 15
        p["max_hp"] = 75
    elif selected_class == "Танк":
        p["strength"] = 15
        p["max_hp"] = 110
        p["defense"] = 6
        
    p["hp"] = p["max_hp"]
    save_game(user_data)
    await callback.message.edit_text(f"⚔️ Вы выбрали класс: **{selected_class}**!\nИспользуйте кнопки ниже для перемещения.", reply_markup=get_main_kb())

# --- ДВИЖЕНИЕ И ГЕНЕРАЦИЯ БИТВЫ (ТЕПЕРЬ С БОССАМИ) ---
@dp.callback_query(F.data.startswith("move_"))
async def callback_move(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data.get(user_id)
    if not p or p.get("class") is None: 
        await callback.answer("Напишите /start чтобы создать персонажа!")
        return
    
    if p.get("enemy_hp", 0) > 0:
        await callback.answer("🚨 Вы в бою! Сначала победите врага или сбегите.", show_alert=True)
        return
        
    direction = callback.data.split("_")[1]
    if direction == "up": p["y"] -= 1
    elif direction == "down": p["y"] += 1
    elif direction == "left": p["x"] -= 1
    elif direction == "right": p["x"] += 1
    
    rand_enc = random.random()
    if rand_enc < 0.10: # 10% шанс на БОССА
        p["enemy_type"] = "boss"
        p["enemy_hp"] = random.randint(80 + p["level"] * 15, 120 + p["level"] * 25)
        p["enemy_max"] = p["enemy_hp"]
        await callback.message.edit_text(f"👑 **БОСС ЛОКАЦИИ!**\nИз тьмы выходит гигантский монстр!\nЗдоровье Врага: {p['enemy_hp']} HP.", reply_markup=get_combat_kb())
    elif rand_enc < 0.40: # 30% шанс на обычного моба
        p["enemy_type"] = "normal"
        p["enemy_hp"] = random.randint(20 + p["level"] * 6, 40 + p["level"] * 10)
        p["enemy_max"] = p["enemy_hp"]
        await callback.message.edit_text(f"👹 На вас нападает монстр!\nЗдоровье Врага: {p['enemy_hp']} HP.", reply_markup=get_combat_kb())
    else:
        await callback.message.edit_text(f"🌲 Чисто.\n📍 Координаты: X: {p['x']} | Y: {p['y']}", reply_markup=get_main_kb())
    save_game(user_data)

# --- БОЕВОЙ ЦИКЛ ---
@dp.callback_query(F.data == "battle_hit")
async def callback_battle_hit(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data[user_id]
    if p["enemy_hp"] <= 0: return
    
    stats = get_total_stats(p)
    if p["class"] == "Маг": base_dmg = stats["intelligence"]
    elif p["class"] == "Лучник": base_dmg = stats["agility"]
    else: base_dmg = stats["strength"]
    
    player_dmg = random.randint(base_dmg, base_dmg + 5)
    p["enemy_hp"] -= player_dmg
    
    if p["enemy_hp"] <= 0:
        p["enemy_hp"] = 0
        if p.get("enemy_type") == "boss":
            xp_gain = 100 + (p["level"] * 15)
            gold_gain = random.randint(100, 200) + (p["level"] * 5)
            crystal_gain = random.randint(30, 80) # Боссы всегда дают много кристаллов
            reward_txt = f"👑 **БОСС ПОВЕРЖЕН! ЭПИЧЕСКАЯ ПОБЕДА!**\nУдар нанес {player_dmg} урона."
        else:
            xp_gain = 20 + (p["level"] * 5)
            gold_gain = random.randint(15, 30) + (p["level"] * 3)
            crystal_gain = random.randint(5, 12) if random.random() < 0.45 else 0
            reward_txt = f"⚔️ Удар нанес {player_dmg} урона. Враг уничтожен!"

        p["gold"] += gold_gain
        p["crystals"] += crystal_gain
        lvl_up_text = add_xp(user_id, xp_gain)
        
        await callback.message.edit_text(f"{reward_txt}\n\n**Награда:**\n🔹 Опыт: +{xp_gain}\n💰 Золото: +{gold_gain}\n💎 Кристаллы: +{crystal_gain}{lvl_up_text}", reply_markup=get_main_kb())
    else:
        # Ответ врага
        multiplier = 2 if p.get("enemy_type") == "boss" else 1
        monster_base = (5 + (p["level"] * 4)) * multiplier
        monster_dmg = max(1, random.randint(monster_base, monster_base + 6) - stats["defense"])
        p["hp"] -= monster_dmg
        
        if p["hp"] <= 0:
            p["hp"] = int(stats["max_hp"] * 0.5)
            p["gold"] = max(0, p["gold"] - 40)
            p["enemy_hp"] = 0
            p["x"], p["y"] = 10, 10
            await callback.message.edit_text("💀 Вы погибли! Очнулись в лагере. Штраф: -40 золота.", reply_markup=get_main_kb())
        else:
            await callback.message.edit_text(f"⚔️ Вы нанесли: {player_dmg} урона.\n👹 Враг ударил на: {monster_dmg} урона.\n\n❤️ Ваше здоровье: {p['hp']}/{stats['max_hp']}\n🩸 Враг: {p['enemy_hp']}/{p['enemy_max']}", reply_markup=get_combat_kb())
            
    save_game(user_data)

@dp.callback_query(F.data == "battle_flee")
async def callback_battle_flee(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data[user_id]
    if p.get("enemy_type") == "boss":
        await callback.answer("❌ От Босса нельзя сбежать!", show_alert=True)
        return
    p["enemy_hp"] = 0
    save_game(user_data)
    await callback.message.edit_text("💨 Вы сбежали в безопасную зону.", reply_markup=get_main_kb())

# --- ДОНАТ (ТЕСТ) И ГАЧА ---
@dp.callback_query(F.data == "test_donate")
async def callback_test_donate(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    user_data[user_id]["crystals"] += 500
    save_game(user_data)
    await callback.answer("💸 Получено 500 кристаллов! (Тестовый режим)", show_alert=True)
    await callback_status(callback)

@dp.callback_query(F.data == "gacha_pull")
async def callback_gacha(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data[user_id]
    
    if p["crystals"] < 50:
        await callback.answer("❌ Недостаточно кристаллов! Нужно 50 💎.", show_alert=True)
        return
        
    p["crystals"] -= 50
    new_item = generate_item()
    p["inventory"].append(new_item)
    save_game(user_data)
    
    b_map = {"strength": "Сила", "agility": "Ловкость", "intelligence": "Интеллект", "max_hp": "Макс ОЗ", "defense": "Защита"}
    await callback.message.edit_text(f"🔮 **Алтарь Призыва!**\n\n📦 Получено: *{new_item['name']}*\n✨ Эффект: +{new_item['bonus_value']} к {b_map[new_item['bonus_type']]}", reply_markup=get_main_kb())

# --- ИНВЕНТАРЬ ---
@dp.callback_query(F.data == "menu_inv")
async def callback_inv_list(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data[user_id]
    
    text = f"🎒 **Снаряжение:**\n🔮 Пыль: {p.get('dust', 0)}\n\n🛡 **Надето:**\n"
    for slot in ["weapon", "armor", "jewelry"]:
        eq = p["equipped"].get(slot)
        if eq: text += f"• {slot.capitalize()}: {eq['name']} (+{eq['upgrade']})\n"
        else: text += f"• {slot.capitalize()}: <Пусто>\n"
        
    text += "\n📦 **В сумке:**\n"
    if not p["inventory"]:
        text += "_Пусто._"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]])
    else:
        kb_buttons = []
        for idx, item in enumerate(p["inventory"][:6]):
            text += f"{idx+1}. {item['name']} (+{item['upgrade']})\n"
            kb_buttons.append([
                InlineKeyboardButton(text=f"👕 Надеть {idx+1}", callback_data=f"inv_equip_{idx}"),
                InlineKeyboardButton(text=f"♻️ В пыль {idx+1}", callback_data=f"inv_scrap_{idx}")
            ])
        kb_buttons.append([InlineKeyboardButton(text="🔺 Точить Надетое Оружие", callback_data="upg_weapon")])
        kb_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])
        kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
        
    await callback.message.edit_text(text, reply_markup=kb)

@dp.callback_query(F.data.startswith("inv_equip_"))
async def callback_inv_equip(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    idx = int(callback.data.split("_")[2])
    p = user_data[user_id]
    if idx >= len(p["inventory"]): return
        
    item = p["inventory"].pop(idx)
    slot = item["slot"]
    old_item = p["equipped"].get(slot)
    if old_item: p["inventory"].append(old_item)
    
    p["equipped"][slot] = item
    save_game(user_data)
    await callback_inv_list(callback)

@dp.callback_query(F.data.startswith("inv_scrap_"))
async def callback_inv_scrap(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    idx = int(callback.data.split("_")[2])
    p = user_data[user_id]
    if idx >= len(p["inventory"]): return
    
    item = p["inventory"].pop(idx)
    p["dust"] = p.get("dust", 0) + RARITIES[item["rarity"]]["dust"]
    save_game(user_data)
    await callback_inv_list(callback)

@dp.callback_query(F.data == "upg_weapon")
async def callback_upgrade_weapon(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data[user_id]
    wp = p["equipped"].get("weapon")
    if not wp:
        await callback.answer("Сначала наденьте оружие!", show_alert=True)
        return
    cost = (wp.get("upgrade", 0) + 1) * 3
    if p.get("dust", 0) < cost:
        await callback.answer(f"Нужно {cost} пыли!", show_alert=True)
        return
    p["dust"] -= cost
    wp["upgrade"] = wp.get("upgrade", 0) + 1
    save_game(user_data)
    await callback_inv_list(callback)

# --- СТАТУС ---
@dp.callback_query(F.data == "status")
async def callback_status(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data[user_id]
    stats = get_total_stats(p)
    
    status_text = (
        f"👤 {p['name']} | 🎖 {p['class']} ({p['level']} ур.)\n"
        f"❤️ Здоровье: {p['hp']}/{stats['max_hp']}\n"
        f"⚔️ С: {stats['strength']} | 🏹 Л: {stats['agility']} | 🔮 И: {stats['intelligence']}\n"
        f"🛡 Защита: {stats['defense']}\n"
        f"💰 Золото: {p['gold']} | 💎 Кристаллы: {p['crystals']}"
    )
    await callback.message.edit_text(status_text, reply_markup=get_main_kb())

@dp.callback_query(F.data == "back_main")
async def callback_back(callback: types.CallbackQuery):
    await callback.message.edit_text("🗺 Панель навигации:", reply_markup=get_main_kb())

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
                   
