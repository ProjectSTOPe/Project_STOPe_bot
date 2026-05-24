import asyncio
import json
import os
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiohttp import web # <--- ДОБАВЛЕНО ДЛЯ RENDER

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
    "Common": {"name": "⬜ Обычный", "dust": 1, "mult": 1, "chance": 60.0},
    "Rare": {"name": "🔵 Редкий", "dust": 3, "mult": 2, "chance": 25.0},
    "Epic": {"name": "🟣 Эпический", "dust": 10, "mult": 4, "chance": 12.0},
    "Legendary": {"name": "🟡 Легендарный", "dust": 35, "mult": 8, "chance": 2.5},
    "Mythic": {"name": "🔴 Мифический", "dust": 100, "mult": 15, "chance": 0.5}
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
        "defense": p.get("defense", 2),
        "bonus_atk": 0,
        "bonus_hp": 0,
        "bonus_def": 0
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
    
    if p["level"] >= 999:
        return "\n⚡ Достигнут макс. уровень (999)!"
        
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

# --- УМНАЯ ГЕНЕРАЦИЯ ПРЕДМЕТА С УЧЕТОМ ГАРАНТОВ ---
def perform_gacha_pull(p):
    p["pity_epic"] = p.get("pity_epic", 0) + 1
    p["pity_leg"] = p.get("pity_leg", 0) + 1
    
    forced_rarity = None
    if p["pity_leg"] >= 80:
        forced_rarity = "Legendary"
    elif p["pity_epic"] >= 20:
        forced_rarity = "Epic"
        
    if forced_rarity:
        rarity_key = forced_rarity
    else:
        roll = random.uniform(0, 100)
        if roll <= 0.5:
            rarity_key = "Mythic"
        elif roll <= 3.0:
            rarity_key = "Legendary"
        elif roll <= 15.0:
            rarity_key = "Epic"
        elif roll <= 40.0:
            rarity_key = "Rare"
        else:
            rarity_key = "Common"
            
    if rarity_key in ["Legendary", "Mythic"]:
        p["pity_leg"] = 0
        p["pity_epic"] = 0
    elif rarity_key == "Epic":
        p["pity_epic"] = 0
        
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
        
    return {
        "name": name, "slot": slot, "rarity": rarity_key,
        "stats": stats, "upgrade": 0
    }

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
            "gold": 500, "crystals": 300, "dust": 0, "hp": 50, "max_hp": 50,
            "strength": 5, "agility": 5, "intelligence": 5, "defense": 2,
            "x": 10, "y": 10, "enemy_hp": 0, "enemy_max": 0, "enemy_type": "normal",
            "pity_epic": 0, "pity_leg": 0,
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
    await message.answer("🗺 Панель перемещения:", reply_markup=get_nav_kb())

@dp.message(F.text == "🔮 Призыв")
async def menu_gacha(message: types.Message):
    user_id = str(message.from_user.id)
    p = user_data.get(user_id)
    if not p: return
    
    p["pity_epic"] = p.get("pity_epic", 0)
    p["pity_leg"] = p.get("pity_leg", 0)
    
    text = (
        f"🎰 **Призыв**\n\n"
        f"💎 Кристаллы: {p['crystals']}\n\n"
        f"Шансы:\n"
        f"🔴 Мифический: 0.5%\n"
        f"🟡 Легендарный: 2.5% (гарант: 80 попыток)\n"
        f"🟣 Эпический: 12% (гарант: 20 попыток)\n"
        f"🔵 Редкий: 25%\n"
        f"⬜ Обычный: ~60%"
    )
    await message.answer(text, reply_markup=get_gacha_kb())

@dp.message(F.text == "👤 Герой")
async def menu_hero(message: types.Message):
    p = user_data.get(str(message.from_user.id))
    if not p: return
    stats = get_total_stats(p)
    
    
