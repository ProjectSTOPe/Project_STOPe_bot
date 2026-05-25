import asyncio
import json
import os
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiohttp import web

BOT_TOKEN = "8824282617:AAFl4gMea_Ocy9tz57E4S4Fmw9lzQckldEQ"
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

# --- СПРАВОЧНИКИ И НАСТРОЙКИ ---
RARITIES = {
    "Common": {"name": "⬜ Обычный", "dust": 1, "mult": 1, "chance": 60.0},
    "Rare": {"name": "🔵 Редкий", "dust": 3, "mult": 2, "chance": 25.0},
    "Epic": {"name": "🟣 Эпический", "dust": 10, "mult": 4, "chance": 12.0},
    "Legendary": {"name": "🟡 Легендарный", "dust": 35, "mult": 8, "chance": 2.5},
    "Mythic": {"name": "🔴 Мифический", "dust": 100, "mult": 15, "chance": 0.5}
}

ITEM_NAMES = {
    "weapon": ["Клинок Клятвы", "Посох Послушника", "Лук Ветров", "Убийца Драконов", "Громобой", 
               "Теневой Кинжал", "Молот Рока", "Коса Жнеца", "Рапира Иллюзий", "Алебарда Стража", 
               "Жезл Пустоты", "Пылающий Меч"],
    "armor": ["Мантия Мудреца", "Кожаный Жилет", "Тяжелый Доспех", "Латный Нагрудник", 
              "Одеяние Теней", "Доспех Дракона", "Кольчуга Света", "Плащ Иллюзиониста", 
              "Кираса Титана", "Ритуальная Роба", "Броня Инь-Янь"],
    "jewelry": ["Кольцо Всевластия", "Амулет Крови", "Ожерелье Света", "Серьга Удачи", 
                "Перстень Монаха", "Кулон Звездопада", "Талисман Бури", "Браслет Жизни", 
                "Кольцо Затмения", "Амулет Дракона", "Печать Демона"]
}

# --- ПОДГРУЗКА ЭФФЕКТИВНЫХ ХАРАКТЕРИСТИК ---
def get_total_stats(p):
    s = {
        "max_hp": p.get("max_hp", 100),
        "strength": p.get("strength", 5),
        "agility": p.get("agility", 5),
        "intelligence": p.get("intelligence", 5),
        "defense": p.get("defense", 2),
        "bonus_atk": 0, "bonus_hp": 0, "bonus_def": 0
    }
    
    for slot in ["weapon", "armor", "jewelry"]:
        item = p.get("equipped", {}).get(slot)
        if item and "stats" in item:
            upg = item.get("upgrade", 0)
            s["bonus_atk"] += item["stats"].get("atk", 0) + (upg * 2)
            s["bonus_hp"] += item["stats"].get("hp", 0) + (upg * 5)
            s["bonus_def"] += item["stats"].get("def", 0) + upg

    s["total_max_hp"] = s["max_hp"] + s["bonus_hp"]
    s["total_def"] = s["defense"] + s["bonus_def"]
    
    if p["class"] == "Маг": base_dmg = s["intelligence"]
    elif p["class"] == "Лучник": base_dmg = s["agility"]
    else: base_dmg = s["strength"]
    s["total_atk"] = base_dmg + s["bonus_atk"]

    return s

def add_xp(user_id, amount):
    uid = str(user_id)
    if uid not in user_data: return ""
    p = user_data[uid]
    
    if p["level"] >= 999: return "\n⚡ Достигнут макс. уровень (999)!"
        
    p["xp"] += amount
    lvl_up_msg = ""
    
    while p["xp"] >= p["level"] * 50:
        p["xp"] -= p["level"] * 50
        p["level"] += 1
        
        if p["class"] == "Маг":
            p["intelligence"] += 4; p["max_hp"] += 8; p["defense"] += 1
        elif p["class"] == "Лучник":
            p["agility"] += 4; p["max_hp"] += 12; p["defense"] += 1
        elif p["class"] == "Танк":
            p["strength"] += 4; p["max_hp"] += 20; p["defense"] += 3
            
        stats = get_total_stats(p)
        p["hp"] = stats["total_max_hp"]
        lvl_up_msg += f"\n🎉 **УРОВЕНЬ ПОВЫШЕН ({p['level']})!** ОЗ восстановлены."
        
        if p["level"] >= 999:
            p["level"] = 999; p["xp"] = 0
            break
            
    save_game(user_data)
    return lvl_up_msg

# --- ГЕНЕРАЦИЯ ПРЕДМЕТОВ ---
def create_item(rarity_key):
    slot = random.choice(["weapon", "armor", "jewelry"])
    name = f"{RARITIES[rarity_key]['name']} {random.choice(ITEM_NAMES[slot])}"
    mult = RARITIES[rarity_key]["mult"]
    
    stats = {"hp": 0, "atk": 0, "def": 0}
    if slot == "weapon":
        stats["atk"] = random.randint(5, 12) * mult
        stats["hp"] = random.randint(0, 5) * mult
        stats["def"] = random.randint(0, 2) * mult
    elif slot == "armor":
        stats["atk"] = random.randint(0, 3) * mult
        stats["hp"] = random.randint(15, 30) * mult
        stats["def"] = random.randint(3, 8) * mult
    else: 
        stats["atk"] = random.randint(2, 6) * mult
        stats["hp"] = random.randint(10, 20) * mult
        stats["def"] = random.randint(1, 4) * mult
        
    return {"name": name, "slot": slot, "rarity": rarity_key, "stats": stats, "upgrade": 0}

def perform_gacha_pull(p):
    p["pity_epic"] = p.get("pity_epic", 0) + 1
    p["pity_leg"] = p.get("pity_leg", 0) + 1
    
    forced_rarity = None
    if p["pity_leg"] >= 80: forced_rarity = "Legendary"
    elif p["pity_epic"] >= 20: forced_rarity = "Epic"
        
    if forced_rarity:
        rarity_key = forced_rarity
    else:
        roll = random.uniform(0, 100)
        if roll <= 0.5: rarity_key = "Mythic"
        elif roll <= 3.0: rarity_key = "Legendary"
        elif roll <= 15.0: rarity_key = "Epic"
        elif roll <= 40.0: rarity_key = "Rare"
        else: rarity_key = "Common"
            
    if rarity_key in ["Legendary", "Mythic"]:
        p["pity_leg"] = 0; p["pity_epic"] = 0
    elif rarity_key == "Epic":
        p["pity_epic"] = 0
        
    return create_item(rarity_key)

def format_item_stats(item):
    s = item["stats"]
    upg = item.get("upgrade", 0)
    return f"🗡 Атака: {s.get('atk',0)+(upg*2)} | 🛡 Защ: {s.get('def',0)+upg} | ❤️ HP: {s.get('hp',0)+(upg*5)}"

# --- КЛАВИАТУРЫ ---
def get_bottom_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🗺 Навигация")],
        [KeyboardButton(text="👤 Герой"), KeyboardButton(text="🎒 Инвентарь")],
        [KeyboardButton(text="🔮 Призыв")]
    ], resize_keyboard=True)

def get_nav_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔼", callback_data="move_up")],
        [InlineKeyboardButton(text="◀️", callback_data="move_left"), InlineKeyboardButton(text="▶️", callback_data="move_right")],
        [InlineKeyboardButton(text="🔽", callback_data="move_down")]
    ])

def get_class_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔮 Маг", callback_data="choose_Маг")],
        [InlineKeyboardButton(text="🏹 Лучник", callback_data="choose_Лучник")],
        [InlineKeyboardButton(text="🛡 Танк", callback_data="choose_Танк")]
    ])

def get_combat_kb(cost_heal=50):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Атака", callback_data="battle_hit")],
        [InlineKeyboardButton(text=f"🧪 Зелье ({cost_heal}💰)", callback_data="battle_heal"), InlineKeyboardButton(text="🏃 Сбежать", callback_data="battle_flee")]
    ])

def get_gacha_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 Призыв ×1 (50 💎)", callback_data="gacha_1")],
        [InlineKeyboardButton(text="🎲 Призыв ×10 (450 💎)", callback_data="gacha_10")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_nav")]
    ])

# --- СТАРТ И КЛАССЫ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id not in user_data or user_data[user_id].get("class") is None:
        user_data[user_id] = {
            "name": message.from_user.first_name, "class": None, "level": 1, "xp": 0,
            "gold": 5000, "crystals": 10000, "dust": 0, "hp": 50, "max_hp": 50,
            "strength": 5, "agility": 5, "intelligence": 5, "defense": 2,
            "x": 10, "y": 10, "enemy_hp": 0, "enemy_max": 0, "enemy_type": "normal",
            "enemy_atk_mult": 1, "pity_epic": 0, "pity_leg": 0,
            "inventory": [], "equipped": {"weapon": None, "armor": None, "jewelry": None}
        }
        save_game(user_data)
        await message.answer("Добро пожаловать в S-Rank Online!\nВыберите свой класс:", reply_markup=get_class_kb())
    else:
        await message.answer("Главное меню активировано.", reply_markup=get_bottom_kb())
        await message.answer("🗺 Выберите направление:", reply_markup=get_nav_kb())

@dp.callback_query(F.data.startswith("choose_"))
async def callback_class_select(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data.get(user_id)
    if not p:
        await callback.answer("⏳ Ошибка данных. Напишите /start", show_alert=True)
        return
        
    selected_class = callback.data.split("_")[1]
    p["class"] = selected_class
    if selected_class == "Маг": p["intelligence"] = 15; p["max_hp"] = 60
    elif selected_class == "Лучник": p["agility"] = 15; p["max_hp"] = 75
    elif selected_class == "Танк": p["strength"] = 15; p["max_hp"] = 110; p["defense"] = 6
        
    p["hp"] = p["max_hp"]
    save_game(user_data)
    await callback.message.delete()
    await bot.send_message(callback.from_user.id, f"⚔️ Вы выбрали класс: **{selected_class}**!", reply_markup=get_bottom_kb())
    await bot.send_message(callback.from_user.id, "🗺 Панель навигации:", reply_markup=get_nav_kb())
    await callback.answer()

# --- ОБРАБОТКА КНОПОК МЕНЮ ---
@dp.message(F.text == "🗺 Навигация")
async def menu_nav(message: types.Message):
    user_id = str(message.from_user.id)
    p = user_data.get(user_id)
    
    if p and p.get("enemy_hp", 0) > 0:
        await message.answer(f"🚨 Вы всё ещё в бою!\n🩸 Здоровье Врага: {p['enemy_hp']}/{p.get('enemy_max', p['enemy_hp'])}", reply_markup=get_combat_kb())
    else:
        await message.answer("🗺 Панель перемещения:", reply_markup=get_nav_kb())

@dp.message(F.text == "🔮 Призыв")
async def menu_gacha(message: types.Message):
    user_id = str(message.from_user.id)
    p = user_data.get(user_id)
    if not p: return
    
    text = (
        f"🎰 **Призыв**\n\n"
        f"💎 Кристаллы: {p['crystals']}\n\n"
        f"Шансы:\n🔴 Мифический: 0.5%\n🟡 Легендарный: 2.5%\n"
        f"🟣 Эпический: 12%\n🔵 Редкий: 25%\n⬜ Обычный: ~60%"
    )
    await message.answer(text, reply_markup=get_gacha_kb())

@dp.callback_query(F.data.startswith("gacha_"))
async def callback_do_gacha(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data.get(user_id)
    if not p: return
    
    amount = int(callback.data.split("_")[1])
    cost = 50 if amount == 1 else 450
    
    if p["crystals"] < cost:
        await callback.answer("❌ Недостаточно кристаллов!", show_alert=True)
        return
        
    if len(p["inventory"]) + amount > 30: # Ограничение сумки
        await callback.answer("🎒 Инвентарь переполнен! Освободите место.", show_alert=True)
        return

    p["crystals"] -= cost
    results = []
    
    for _ in range(amount):
        item = perform_gacha_pull(p)
        p["inventory"].append(item)
        results.append(item["name"])
        
    save_game(user_data)
    await callback.message.answer(f"✨ **Результат призыва:**\n" + "\n".join(results))
    await callback.message.edit_text(f"🎰 **Призыв**\n💎 Кристаллы: {p['crystals']}", reply_markup=get_gacha_kb())
    await callback.answer()

@dp.message(F.text == "👤 Герой")
async def menu_hero(message: types.Message):
    p = user_data.get(str(message.from_user.id))
    if not p: return
    stats = get_total_stats(p)
    
    text = (
        f"👤 {p['name']} | 🎖 {p['class']} ({p['level']} ур.)\n"
        f"Прогресс: {p['xp']}/{p['level']*50} XP\n\n"
        f"**Статы:**\n"
        f"⚔️ Атака: {stats['total_atk']} | 🛡 Защита: {stats['total_def']}\n"
        f"❤️ HP: {p['hp']}/{stats['total_max_hp']}\n\n"
        f"**Ресурсы:**\n💰 Золото: {p['gold']} | 💎 Кристаллы: {p['crystals']}\n✨ Пыль: {p.get('dust', 0)}"
    )
    await message.answer(text)

@dp.message(F.text == "🎒 Инвентарь")
async def menu_inventory(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id not in user_data: return
    await show_inventory(user_id, message)

async def show_inventory(user_id, message_or_callback):
    p = user_data.get(user_id)
    if not p: return
    
    text = f"🎒 **Инвентарь** (Пыль: {p.get('dust', 0)})\n\n🛡 **Надето:**\n"
    for slot in ["weapon", "armor", "jewelry"]:
        eq = p["equipped"].get(slot)
        if eq: 
            text += f"• {slot.capitalize()}: {eq['name']} (+{eq['upgrade']})\n  └ {format_item_stats(eq)}\n"
        else: text += f"• {slot.capitalize()}: <Пусто>\n"
        
    text += "\n📦 **В сумке:**\n"
    kb = None
    if not p.get("inventory"):
        text += "_Пусто._"
    else:
        kb_buttons = []
        for idx, item in enumerate(p["inventory"][:6]):
            text += f"{idx+1}. {item['name']} (+{item['upgrade']})\n    {format_item_stats(item)}\n"
            kb_buttons.append([
                InlineKeyboardButton(text=f"👕 Надеть {idx+1}", callback_data=f"inv_equip_{idx}"),
                InlineKeyboardButton(text=f"♻️ В пыль {idx+1}", callback_data=f"inv_scrap_{idx}")
            ])
        kb_buttons.append([InlineKeyboardButton(text="🔺 Точить Оружие", callback_data="upg_weapon")])
        kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
        
    if isinstance(message_or_callback, types.Message):
        await message_or_callback.answer(text, reply_markup=kb)
    else:
        await message_or_callback.message.edit_text(text, reply_markup=kb)

@dp.callback_query(F.data == "back_nav")
async def callback_back_nav(callback: types.CallbackQuery):
    await callback.message.edit_text("🗺 Выберите направление:", reply_markup=get_nav_kb())
    await callback.answer()

# --- ИНВЕНТАРЬ ОБРАБОТЧИКИ ---
@dp.callback_query(F.data.startswith("inv_equip_"))
async def callback_inv_equip(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data.get(user_id)
    if not p: return
        
    idx = int(callback.data.split("_")[2])
    if idx >= len(p["inventory"]): return
        
    item = p["inventory"].pop(idx)
    slot = item["slot"]
    old_item = p["equipped"].get(slot)
    if old_item: p["inventory"].append(old_item)
    
    p["equipped"][slot] = item
    stats = get_total_stats(p)
    p["hp"] = min(p["hp"], stats["total_max_hp"])
    
    save_game(user_data)
    await show_inventory(user_id, callback)
    await callback.answer()

@dp.callback_query(F.data.startswith("inv_scrap_"))
async def callback_inv_scrap(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data.get(user_id)
    if not p: return
        
    idx = int(callback.data.split("_")[2])
    if idx >= len(p["inventory"]): return
    
    item = p["inventory"].pop(idx)
    p["dust"] = p.get("dust", 0) + RARITIES[item["rarity"]]["dust"]
    save_game(user_data)
    await show_inventory(user_id, callback)
    await callback.answer()

@dp.callback_query(F.data == "upg_weapon")
async def callback_upgrade_weapon(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data.get(user_id)
    if not p: return
        
    wp = p["equipped"].get("weapon")
    if not wp:
        await callback.answer("Сначала наденьте оружие!", show_alert=True)
        return
        
    cost = (wp.get("upgrade", 0) + 1) * 5
    if p.get("dust", 0) < cost:
        await callback.answer(f"Нужно {cost} пыли!", show_alert=True)
        return
        
    p["dust"] -= cost
    wp["upgrade"] = wp.get("upgrade", 0) + 1
    save_game(user_data)
    await show_inventory(user_id, callback)
    await callback.answer("Оружие улучшено!", show_alert=False)

# --- ДВИЖЕНИЕ И БОЙ ---
@dp.callback_query(F.data.startswith("move_"))
async def callback_move(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data.get(user_id)
    if not p: return
    
    if p.get("enemy_hp", 0) > 0:
        await callback.answer("🚨 Вы в бою! Сначала победите врага.", show_alert=True)
        return
        
    direction = callback.data.split("_")[1]
    if direction == "up": p["y"] -= 1
    elif direction == "down": p["y"] += 1
    elif direction == "left": p["x"] -= 1
    elif direction == "right": p["x"] += 1
    
    # Шансы: 0.5% Золотой | 3% Черный | 5% Красный | 10% Эпик | 30% Обычный
    rand_enc = random.random() * 100
    base_boss_hp = random.randint(150 + p["level"] * 15, 250 + p["level"] * 25)

    if rand_enc < 0.5:
        p["enemy_type"] = "boss_golden"
        p["enemy_hp"] = base_boss_hp * 10
        p["enemy_atk_mult"] = 5
        msg = f"🌟 **ЗОЛОТОЙ БОСС!**\nЗдоровье: {p['enemy_hp']} HP."
    elif rand_enc < 3.5:
        p["enemy_type"] = "boss_black"
        p["enemy_hp"] = base_boss_hp * 20
        p["enemy_atk_mult"] = 2
        msg = f"🌑 **ЧЕРНЫЙ БОСС!**\nЗдоровье: {p['enemy_hp']} HP."
    elif rand_enc < 8.5:
        p["enemy_type"] = "boss_red"
        p["enemy_hp"] = base_boss_hp * 4
        p["enemy_atk_mult"] = 10
        msg = f"🩸 **КРАСНЫЙ БОСС!**\nЗдоровье: {p['enemy_hp']} HP."
    elif rand_enc < 18.5:
        p["enemy_type"] = "boss"
        p["enemy_hp"] = base_boss_hp
        p["enemy_atk_mult"] = 2
        msg = f"👑 **ЭПИЧЕСКИЙ БОСС!**\nЗдоровье: {p['enemy_hp']} HP."
    elif rand_enc < 48.5:
        p["enemy_type"] = "normal"
        p["enemy_hp"] = random.randint(30 + p["level"] * 6, 60 + p["level"] * 10)
        p["enemy_atk_mult"] = 1
        msg = f"👹 Монстр нападает!\nЗдоровье: {p['enemy_hp']} HP."
    else:
        p["enemy_hp"] = 0
        msg = f"🌲 Чисто.\n📍 Координаты: X: {p['x']} | Y: {p['y']}"
        
    p["enemy_max"] = p["enemy_hp"]
    save_game(user_data)

    if p["enemy_hp"] > 0:
        await callback.message.edit_text(msg, reply_markup=get_combat_kb())
    else:
        await callback.message.edit_text(msg, reply_markup=get_nav_kb())
    await callback.answer()

@dp.callback_query(F.data == "battle_hit")
async def callback_battle_hit(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data.get(user_id)
    if not p: return
        
    if p.get("enemy_hp", 0) <= 0:
        await callback.answer("Враг уже повержен!", show_alert=True)
        return
    
    stats = get_total_stats(p)
    player_dmg = max(1, random.randint(int(stats["total_atk"] * 0.8), int(stats["total_atk"] * 1.2)))
    p["enemy_hp"] -= player_dmg
    
    if p["enemy_hp"] <= 0:
        p["enemy_hp"] = 0
        drop_item = None
        
        # Логика дропа лута
        roll = random.uniform(0, 100)
        e_type = p.get("enemy_type", "normal")
        
        if e_type == "boss_golden":
            if roll < 1: drop_item = create_item("Mythic")
            elif roll < 10: drop_item = create_item("Legendary")
            else: drop_item = create_item("Epic")
            xp_gain = 500 + (p["level"] * 50); gold_gain = 1000
        elif e_type == "boss_black":
            if roll < 5: drop_item = create_item("Legendary")
            elif roll < 20: drop_item = create_item("Epic")
            else: drop_item = create_item("Rare")
            xp_gain = 300 + (p["level"] * 30); gold_gain = 500
        elif e_type == "boss_red":
            if roll < 2: drop_item = create_item("Legendary")
            elif roll < 5: drop_item = create_item("Epic")
            else: drop_item = create_item("Rare")
            xp_gain = 250 + (p["level"] * 25); gold_gain = 400
        elif e_type == "boss":
            if roll < 5: drop_item = create_item("Epic")
            elif roll < 35: drop_item = create_item("Rare")
            else: drop_item = create_item("Common")
            xp_gain = 100 + (p["level"] * 15); gold_gain = 150
        else:
            if roll < 15: drop_item = create_item("Common") # 15% с обычных мобов
            xp_gain = 25 + (p["level"] * 5); gold_gain = 30

        p["gold"] += gold_gain
        p["crystals"] += random.randint(1, 5) if e_type == "normal" else random.randint(10, 50)
        lvl_up_text = add_xp(user_id, xp_gain)
        
        reward_txt = f"⚔️ Враг повержен! ({player_dmg} урона)\n🔹 Опыт: +{xp_gain}\n💰 Золото: +{gold_gain}"
        if drop_item:
            p["inventory"].append(drop_item)
            reward_txt += f"\n🎁 **Лут:** {drop_item['name']}"
            
        await callback.message.edit_text(reward_txt + lvl_up_text, reply_markup=get_nav_kb())
    else:
        multiplier = p.get("enemy_atk_mult", 1)
        monster_base = (8 + (p["level"] * 5)) * multiplier
        monster_dmg = max(1, random.randint(int(monster_base*0.8), int(monster_base*1.2)) - stats["total_def"])
        p["hp"] -= monster_dmg
        
        if p["hp"] <= 0:
            p["hp"] = int(stats["total_max_hp"] * 0.5)
            p["gold"] = max(0, p["gold"] - 50)
            p["enemy_hp"] = 0
            await callback.message.edit_text("💀 Вы погибли! Очнулись в лагере. Штраф: -50 золота.", reply_markup=get_nav_kb())
        else:
            await callback.message.edit_text(f"⚔️ Урон: {player_dmg} | 👹 Враг: {monster_dmg}\n\n❤️ Здоровье: {p['hp']}/{stats['total_max_hp']}\n🩸 Враг: {p['enemy_hp']}/{p['enemy_max']}", reply_markup=get_combat_kb())
            
    save_game(user_data)
    await callback.answer()

@dp.callback_query(F.data == "battle_heal")
async def callback_battle_heal(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data.get(user_id)
    if not p: return
        
    stats = get_total_stats(p)
    if p["gold"] < 50:
        await callback.answer("❌ Не хватает золота! Нужно 50 💰.", show_alert=True)
        return
    if p["hp"] >= stats["total_max_hp"]:
        await callback.answer("У вас полное здоровье!", show_alert=True)
        return
        
    p["gold"] -= 50
    heal_amount = int(stats["total_max_hp"] * 0.4)
    p["hp"] = min(stats["total_max_hp"], p["hp"] + heal_amount)
    save_game(user_data)
    await callback.message.edit_text(f"🧪 Вы выпили зелье!\n❤️ Здоровье: {p['hp']}/{stats['total_max_hp']}\n🩸 Враг: {p['enemy_hp']}/{p['enemy_max']}", reply_markup=get_combat_kb())
    await callback.answer()

@dp.callback_query(F.data == "battle_flee")
async def callback_battle_flee(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data.get(user_id)
    if not p: return
        
    if "boss" in p.get("enemy_type", ""):
        await callback.answer("❌ От Босса нельзя сбежать!", show_alert=True)
        return
        
    p["enemy_hp"] = 0
    save_game(user_data)
    await callback.message.edit_text("💨 Вы сбежали.", reply_markup=get_nav_kb())
    await callback.answer()

# --- ФЕЙКОВЫЙ СЕРВЕР ДЛЯ RENDER ---
async def handle_ping(request):
    return web.Response(text="Bot is running!")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(dp.start_polling(bot))
    
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    print(f"Сервер запущен на порту {port}")
    await site.start()
    
    while True: await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
