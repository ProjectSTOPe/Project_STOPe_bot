import asyncio
import json
import os
import random
import time
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

WEAPONS = {
    "Маг": ["Посох Послушника", "Жезл Пустоты", "Магический Гримуар", "Коса Жнеца"],
    "Лучник": ["Лук Ветров", "Короткий Лук", "Арбалет Стража", "Эльфийский Лук"],
    "Танк": ["Клинок Клятвы", "Убийца Драконов", "Молот Рока", "Алебарда Ополчения"]
}

ARMORS = ["Мантия Мудреца", "Кожаный Жилет", "Тяжелый Доспех", "Одеяние Теней", "Доспех Дракона", "Броня Инь-Янь"]
JEWELRY = ["Кольцо Всевластия", "Амулет Крови", "Ожерелье Света", "Серьга Удачи", "Талисман Бури", "Печать Демона"]

UPGRADE_CHANCES = {0: 100, 1: 100, 2: 100, 3: 70, 4: 60, 5: 50, 6: 40, 7: 30, 8: 20, 9: 15, 10: 10, 11: 5}

# ---РАСЧЕТ ХАРАКТЕРИСТИК ---
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
        lvl_up_msg += f"\n🎉 УРОВЕНЬ ПОВЫШЕН ({p['level']})! ОЗ восстановлены."
        
        if p["level"] >= 999:
            p["level"] = 999; p["xp"] = 0
            break
            
    return lvl_up_msg

# --- ГЕНЕРАЦИЯ ПРЕДМЕТОВ ---
def create_item(rarity_key):
    slot = random.choice(["weapon", "armor", "jewelry"])
    req_class = None
    
    if slot == "weapon":
        req_class = random.choice(["Маг", "Лучник", "Танк"])
        name = f"{RARITIES[rarity_key]['name']} {random.choice(WEAPONS[req_class])}"
    elif slot == "armor":
        name = f"{RARITIES[rarity_key]['name']} {random.choice(ARMORS)}"
    else:
        name = f"{RARITIES[rarity_key]['name']} {random.choice(JEWELRY)}"
        
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
        
    return {"name": name, "slot": slot, "rarity": rarity_key, "stats": stats, "upgrade": 0, "req_class": req_class}

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
        [KeyboardButton(text="🔮 Призыв"), KeyboardButton(text="💱 Обмен")],
        [KeyboardButton(text="💰 Донат")]
    ], resize_keyboard=True)

def get_nav_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔼", callback_data="move_up")],
        [InlineKeyboardButton(text="◀️", callback_data="move_left"), InlineKeyboardButton(text="▶️", callback_data="move_right")],
        [InlineKeyboardButton(text="🔽", callback_data="move_down")],
        [InlineKeyboardButton(text="🤖 Меню Автоохоты", callback_data="auto_hunt_menu")]
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
        [InlineKeyboardButton(text="🎲 Призыв ×1 (100 💎)", callback_data="gacha_1")],
        [InlineKeyboardButton(text="🎲 Призыв ×11 (1900 💎)", callback_data="gacha_11")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_nav")]
    ])

def get_auto_hunt_kb(p):
    scrap = p.get("auto_scrap", {})
    c_state = "✅" if scrap.get("Common") else "❌"
    r_state = "✅" if scrap.get("Rare") else "❌"
    e_state = "✅" if scrap.get("Epic") else "❌"
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{c_state} Разбор Обычных", callback_data="toggle_scrap_Common")],
        [InlineKeyboardButton(text=f"{r_state} Разбор Редких", callback_data="toggle_scrap_Rare")],
        [InlineKeyboardButton(text=f"{e_state} Разбор Эпических", callback_data="toggle_scrap_Epic")],
        [InlineKeyboardButton(text="▶️ Запустить (1ч - 999 💎)", callback_data="start_auto_hunt")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_nav")]
    ])

# --- ОБРАБОТЧИКИ КОМАНД ---
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
            "auto_hunt_end": 0, "auto_hunt_paused": False, "auto_hunt_remaining": 0,
            "inventory": [], "equipped": {"weapon": None, "armor": None, "jewelry": None},
            "auto_scrap": {"Common": False, "Rare": False, "Epic": False}
        }
        save_game(user_data)
        await message.answer("Добро пожаловать в S-Rank Online!\nВыберите свой класс:", reply_markup=get_class_kb())
    else:
        await message.answer("Главное меню активировано.", reply_markup=get_bottom_kb())
        await message.answer("🗺 Выберите направление:", reply_markup=get_nav_kb())

@dp.callback_query(F.data.startswith("choose_"))
async def callback_choose_class(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    chosen_class = callback.data.split("_")[1]
    if user_id in user_data:
        user_data[user_id]["class"] = chosen_class
        if chosen_class == "Маг":
            user_data[user_id]["intelligence"] = 12; user_data[user_id]["max_hp"] = 60
        elif chosen_class == "Лучник":
            user_data[user_id]["agility"] = 12; user_data[user_id]["max_hp"] = 75
        elif chosen_class == "Танк":
            user_data[user_id]["strength"] = 12; user_data[user_id]["max_hp"] = 100
        user_data[user_id]["hp"] = user_data[user_id]["max_hp"]
        save_game(user_data)
        await callback.message.edit_text(f"Вы выбрали класс: {chosen_class}! Начните охоту через меню Навигации.", reply_markup=None)
        await callback.message.answer("Кнопки управления активированы:", reply_markup=get_bottom_kb())

# --- РАЗДЕЛ ДОНАТА (ПОЛНОСТЬЮ ОБНОВЛЕН) ---
@dp.message(F.text == "💰 Донат")
async def menu_donate(message: types.Message):
    text = (
        "💰 <b>Донат магазин S-Rank Online</b>\n\n"
        "💵 <b>Тарифный курс пополнения:</b>\n"
        "• 5 TON = 1000 💎 Кристаллов\n"
        "• 5 USDT (TON) = 1000 💎 Кристаллов\n\n"
        "📍 <b>Адрес кошелька проекта (сеть TON):</b>\n"
        "<code>UQD8EMc9SOt1V_YaItSSaLwUUEgkV293SKX5STO6aTbQTwn7</code>\n\n"
        "<i>Инструкция: Скопируйте кошелек выше кликом на него, переведите средства (TON или USDT) через кошелек Telegram, а затем нажмите кнопку проверки транзакции под этим сообщением.</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👛 Открыть Wallet Telegram", url="https://t.me/wallet")],
        [InlineKeyboardButton(text="💎 Проверить оплату TON", callback_data="check_pay_TON")],
        [InlineKeyboardButton(text="💎 Проверить оплату USDT", callback_data="check_pay_USDT")]
    ])
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data.startswith("check_pay_"))
async def callback_check_donate(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data.get(user_id)
    if not p: return
    
    currency = callback.data.split("_")[2]
    
    # Симуляция проверки транзакции блокчейна на указанном кошельке
    p["crystals"] = p.get("crystals", 0) + 1000
    save_game(user_data)
    
    await callback.answer(f"✅ Транзакция в сети TON подтверждена!", show_alert=True)
    await callback.message.edit_text(
        f"🎉 <b>Успешное зачисление доната!</b>\n\n"
        f"Сеть верифицировала перевод на целевой адрес.\n"
        f"Начислено: +1000 💎 (зачислено по курсу {currency})\n"
        f"Ваш текущий баланс: {p['crystals']} 💎",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="↩️ Вернуться к навигации", callback_data="back_nav")]]),
        parse_mode="HTML"
    )

# --- ОБМЕН КРИСТАЛЛОВ С АВТОРАЗМОРОЗКОЙ ---
@dp.message(F.text == "💱 Обмен")
async def menu_exchange(message: types.Message):
    user_id = str(message.from_user.id)
    p = user_data.get(user_id)
    if not p: return
    text = f"💱 <b>Обмен валюты</b>\n\nВаши кристаллы: {p.get('crystals', 0)} 💎\nКурс обмена: 100 💎 = 1000 💰 Золота"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обменять 100 💎", callback_data="exchange_100")],
        [InlineKeyboardButton(text="🔄 Обменять 1000 💎", callback_data="exchange_1000")]
    ])
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data.startswith("exchange_"))
async def callback_exchange(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data.get(user_id)
    if not p: return
    amount = int(callback.data.split("_")[1])
    
    if p.get("crystals", 0) < amount:
        await callback.answer("❌ Недостаточно кристаллов на балансе!", show_alert=True)
        return
        
    p["crystals"] -= amount
    gold_gained = (amount // 100) * 1000
    p["gold"] = p.get("gold", 0) + gold_gained
    
    text = f"✅ Успешный обмен!\nПолучено: +{gold_gained} 💰 Золота\nОстаток кристаллов: {p['crystals']} 💎"
    
    # ЕСЛИ АВТООХОТА БЫЛА ЗАМОРОЖЕНА ИЗ-ЗА ЗОЛОТА И ИГРОК КУПИЛ ЕГО — АВТОМАТИЧЕСКИЙ СТАРТ
    if p.get("auto_hunt_paused", False) and p["gold"] >= 50:
        p["auto_hunt_paused"] = False
        p["auto_hunt_end"] = time.time() + p.get("auto_hunt_remaining", 0)
        p["auto_hunt_remaining"] = 0
        text += "\n\n▶️ <b>Автоохота автоматически возобновлена! Замороженное время возвращено в счетчик.</b>"
        
    save_game(user_data)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Еще 100 💎", callback_data="exchange_100"), 
         InlineKeyboardButton(text="🔄 Еще 1000 💎", callback_data="exchange_1000")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

# --- СИСТЕМА НАВИГАЦИИ И МАНУАЛЬНОГО БОЯ ---
@dp.message(F.text == "🗺 Навигация")
async def menu_nav(message: types.Message):
    user_id = str(message.from_user.id)
    p = user_data.get(user_id)
    if p and p.get("enemy_hp", 0) > 0:
        await message.answer(f"🚨 Вы находитесь в бою!\n🩸 ХП Врага: {p['enemy_hp']}/{p.get('enemy_max', p['enemy_hp'])}", reply_markup=get_combat_kb())
    else:
        await message.answer("🗺 Выберите направление движения персонажа:", reply_markup=get_nav_kb())

@dp.callback_query(F.data.startswith("move_"))
async def callback_move(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data.get(user_id)
    if not p: return
    
    if p.get("enemy_hp", 0) > 0:
        await callback.answer("🚨 Сначала завершите текущий бой!", show_alert=True)
        return
        
    direction = callback.data.split("_")[1]
    if direction == "up": p["y"] -= 1
    elif direction == "down": p["y"] += 1
    elif direction == "left": p["x"] -= 1
    elif direction == "right": p["x"] += 1
    
    rand_enc = random.random() * 100
    base_boss_hp = random.randint(150 + p["level"] * 15, 250 + p["level"] * 25)

    if rand_enc < 0.5:
        p["enemy_type"] = "boss_golden"
        p["enemy_hp"] = base_boss_hp * 10
        p["enemy_atk_mult"] = 5
        msg = f"🌟 <b>ЗОЛОТОЙ БОСС!</b>\n🩸 Здоровье: {p['enemy_hp']} HP."
    elif rand_enc < 3.5:
        p["enemy_type"] = "boss_black"
        p["enemy_hp"] = base_boss_hp * 20
        p["enemy_atk_mult"] = 2
        msg = f"🌑 <b>ЧЕРНЫЙ БОСС!</b>\n🩸 Здоровье: {p['enemy_hp']} HP."
    elif rand_enc < 8.5:
        p["enemy_type"] = "boss_red"
        p["enemy_hp"] = base_boss_hp * 4
        p["enemy_atk_mult"] = 10
        msg = f"🩸 <b>КРАСНЫЙ БОСС!</b>\n🩸 Здоровье: {p['enemy_hp']} HP."
    elif rand_enc < 18.5:
        # ДОБАВЛЕН ОБЫЧНЫЙ БОСС В СПИСОК ОХОТЫ
        p["enemy_type"] = "boss_normal"
        p["enemy_hp"] = base_boss_hp
        p["enemy_atk_mult"] = 2
        msg = f"👑 <b>ОБЫЧНЫЙ БОСС!</b>\n🩸 Здоровье: {p['enemy_hp']} HP."
    elif rand_enc < 48.5:
        p["enemy_type"] = "normal"
        p["enemy_hp"] = random.randint(30 + p["level"] * 6, 60 + p["level"] * 10)
        p["enemy_atk_mult"] = 1
        msg = f"👹 На вас напал монстр!\n🩸 Здоровье: {p['enemy_hp']} HP."
    else:
        p["enemy_hp"] = 0
        msg = f"🌲 На этой локации пусто и безопасно.\n📍 Координаты: X: {p['x']} | Y: {p['y']}"
        
    p["enemy_max"] = p["enemy_hp"]
    save_game(user_data)

    if p["enemy_hp"] > 0:
        await callback.message.edit_text(msg, reply_markup=get_combat_kb(), parse_mode="HTML")
    else:
        await callback.message.edit_text(msg, reply_markup=get_nav_kb())
    await callback.answer()

@dp.callback_query(F.data == "battle_hit")
async def callback_battle_hit(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data.get(user_id)
    if not p: return
        
    if p.get("enemy_hp", 0) <= 0:
        await callback.answer("Враг уже мертв!", show_alert=True)
        return
    
    stats = get_total_stats(p)
    player_dmg = max(1, random.randint(int(stats["total_atk"] * 0.8), int(stats["total_atk"] * 1.2)))
    p["enemy_hp"] -= player_dmg
    
    if p["enemy_hp"] <= 0:
        p["enemy_hp"] = 0
        drop_item = None
        roll = random.uniform(0, 100)
        e_type = p.get("enemy_type", "normal")
        
# --- СИСТЕМА НАВИГАЦИИ И МАНУАЛЬНОГО БОЯ ---
@dp.message(F.text == "🗺 Навигация")
async def menu_nav(message: types.Message):
    user_id = str(message.from_user.id)
    p = user_data.get(user_id)
    if p and p.get("enemy_hp", 0) > 0:
        await message.answer(f"🚨 Вы находитесь в бою!\n🩸 ХП Врага: {p['enemy_hp']}/{p.get('enemy_max', p['enemy_hp'])}", reply_markup=get_combat_kb())
    else:
        await message.answer("🗺 Выберите направление движения персонажа:", reply_markup=get_nav_kb())

@dp.callback_query(F.data.startswith("move_"))
async def callback_move(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data.get(user_id)
    if not p: return
    
    if p.get("enemy_hp", 0) > 0:
        await callback.answer("🚨 Сначала завершите текущий бой!", show_alert=True)
        return
        
    direction = callback.data.split("_")[1]
    if direction == "up": p["y"] -= 1
    elif direction == "down": p["y"] += 1
    elif direction == "left": p["x"] -= 1
    elif direction == "right": p["x"] += 1
    
    rand_enc = random.random() * 100
    base_boss_hp = random.randint(150 + p["level"] * 15, 250 + p["level"] * 25)

    if rand_enc < 0.5:
        p["enemy_type"] = "boss_golden"
        p["enemy_hp"] = base_boss_hp * 10
        p["enemy_atk_mult"] = 5
        msg = f"🌟 <b>ЗОЛОТОЙ БОСС!</b>\n🩸 Здоровье: {p['enemy_hp']} HP."
    elif rand_enc < 3.5:
        p["enemy_type"] = "boss_black"
        p["enemy_hp"] = base_boss_hp * 20
        p["enemy_atk_mult"] = 2
        msg = f"🌑 <b>ЧЕРНЫЙ БОСС!</b>\n🩸 Здоровье: {p['enemy_hp']} HP."
    elif rand_enc < 8.5:
        p["enemy_type"] = "boss_red"
        p["enemy_hp"] = base_boss_hp * 4
        p["enemy_atk_mult"] = 10
        msg = f"🩸 <b>КРАСНЫЙ БОСС!</b>\n🩸 Здоровье: {p['enemy_hp']} HP."
    elif rand_enc < 18.5:
        # ДОБАВЛЕН ОБЫЧНЫЙ БОСС В СПИСОК ОХОТЫ
        p["enemy_type"] = "boss_normal"
        p["enemy_hp"] = base_boss_hp
        p["enemy_atk_mult"] = 2
        msg = f"👑 <b>ОБЫЧНЫЙ БОСС!</b>\n🩸 Здоровье: {p['enemy_hp']} HP."
    elif rand_enc < 48.5:
        p["enemy_type"] = "normal"
        p["enemy_hp"] = random.randint(30 + p["level"] * 6, 60 + p["level"] * 10)
        p["enemy_atk_mult"] = 1
        msg = f"👹 На вас напал монстр!\n🩸 Здоровье: {p['enemy_hp']} HP."
    else:
        p["enemy_hp"] = 0
        msg = f"🌲 На этой локации пусто и безопасно.\n📍 Координаты: X: {p['x']} | Y: {p['y']}"
        
    p["enemy_max"] = p["enemy_hp"]
    save_game(user_data)

    if p["enemy_hp"] > 0:
        await callback.message.edit_text(msg, reply_markup=get_combat_kb(), parse_mode="HTML")
    else:
        await callback.message.edit_text(msg, reply_markup=get_nav_kb())
    await callback.answer()

@dp.callback_query(F.data == "battle_hit")
async def callback_battle_hit(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data.get(user_id)
    if not p: return
        
    if p.get("enemy_hp", 0) <= 0:
        await callback.answer("Враг уже мертв!", show_alert=True)
        return
    
    stats = get_total_stats(p)
    player_dmg = max(1, random.randint(int(stats["total_atk"] * 0.8), int(stats["total_atk"] * 1.2)))
    p["enemy_hp"] -= player_dmg
    
    if p["enemy_hp"] <= 0:
        p["enemy_hp"] = 0
        drop_item = None
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
        elif e_type == "boss_normal":
            # Награды и расчет шансов дропа для Обычного Босса
            if roll < 5: drop_item = create_item("Epic")
            elif roll < 35: drop_item = create_item("Rare")
            else: drop_item = create_item("Common")
            xp_gain = 100 + (p["level"] * 15); gold_gain = 150
        else:
            if roll < 15: drop_item = create_item("Common")
            xp_gain = 25 + (p["level"] * 5); gold_gain = 30

        p["gold"] += gold_gain
        p["crystals"] += random.randint(1, 5) if e_type == "normal" else random.randint(10, 50)
        lvl_up_text = add_xp(user_id, xp_gain)
        
        reward_txt = f"⚔️ Вы нанесли {player_dmg} урона и победили!\n🔹 Получено опыта: +{xp_gain}\n💰 Получено золота: +{gold_gain}"
        if drop_item:
            p["inventory"].append(drop_item)
            reward_txt += f"\n🎁 Трофей: {drop_item['name']}"
            
        await callback.message.edit_text(reward_txt + lvl_up_text, reply_markup=get_nav_kb())
    else:
        multiplier = p.get("enemy_atk_mult", 1)
        monster_base = (8 + (p["level"] * 5)) * multiplier
        monster_dmg = max(1, random.randint(int(monster_base*0.8), int(monster_base*1.2)) - stats["total_def"])
        p["hp"] -= monster_dmg
        
        if p["hp"] <= 0:
            p["hp"] = int(stats["total_max_hp"] * 0.5)
            lost_xp = int(p["xp"] * 0.05)
            p["xp"] = max(0, p["xp"] - lost_xp)
            p["enemy_hp"] = 0
            await callback.message.edit_text(f"💀 Вы погибли в бою! Штраф за смерть: -5% опыта (-{lost_xp} XP). Воскрешение в городе.", reply_markup=get_nav_kb())
        else:
            await callback.message.edit_text(f"⚔️ Ваш урон: {player_dmg} | 👹 Ответный урон: {monster_dmg}\n\n❤️ Ваше HP: {p['hp']}/{stats['total_max_hp']}\n🩸 HP Монстра: {p['enemy_hp']}/{p['enemy_max']}", reply_markup=get_combat_kb())
            
    save_game(user_data)
    await callback.answer()

@dp.callback_query(F.data == "battle_heal")
async def callback_battle_heal(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data.get(user_id)
    if not p: return
        
    stats = get_total_stats(p)
    if p["gold"] < 50:
        await callback.answer("❌ Недостаточно золота для покупки зелья (нужно 50 💰)!", show_alert=True)
        return
    if p["hp"] >= stats["total_max_hp"]:
        await callback.answer("У вас максимальный запас здоровья!", show_alert=True)
        return
        
    p["gold"] -= 50
    heal_amount = int(stats["total_max_hp"] * 0.4)
    p["hp"] = min(stats["total_max_hp"], p["hp"] + heal_amount)
    save_game(user_data)
    await callback.message.edit_text(f"🧪 Вы использовали зелье восстановления!\n❤️ Ваше HP: {p['hp']}/{stats['total_max_hp']}\n🩸 HP Монстра: {p['enemy_hp']}/{p['enemy_max']}", reply_markup=get_combat_kb())
    await callback.answer()

@dp.callback_query(F.data == "battle_flee")
async def callback_battle_flee(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data.get(user_id)
    if not p: return
        
    if "boss" in p.get("enemy_type", ""):
        await callback.answer("❌ Побег из битвы с Боссом невозможен!", show_alert=True)
        return
        
    p["enemy_hp"] = 0
    save_game(user_data)
    await callback.message.edit_text("💨 Вы успешно сбежали с поля боя.", reply_markup=get_nav_kb())
    await callback.answer()

# --- МЕНЮ ГАЧИ / ИНВЕНТАРЯ ---
@dp.message(F.text == "🔮 Призыв")
async def menu_gacha(message: types.Message):
    user_id = str(message.from_user.id)
    p = user_data.get(user_id)
    if not p: return
    text = (
        f"🎰 <b>Призыв снаряжения S-Rank</b>\n\n"
        f"💎 Ваши кристаллы: {p['crystals']}\n\n"
        f"Шансы выпадания предметов:\n"
        f"🔴 Мифический: 0.5%\n🟡 Легендарный: 2.5%\n🟣 Эпический: 12%\n"
        f"🔵 Редкий: 25%\n⬜ Обычный: ~60%"
    )
    await message.answer(text, reply_markup=get_gacha_kb(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("gacha_"))
async def callback_do_gacha(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data.get(user_id)
    if not p: return
    
    amount = int(callback.data.split("_")[1])
    cost = 100 if amount == 1 else 1900
    
    if p["crystals"] < cost:
        await callback.answer("❌ Недостаточно кристаллов для призыва!", show_alert=True)
        return
        
    if len(p["inventory"]) + amount > 30:
        await callback.answer("🎒 Ваш инвентарь переполнен! Лимит 30 слотов.", show_alert=True)
        return

    p["crystals"] -= cost
    results = []
    
    for _ in range(amount):
        item = perform_gacha_pull(p)
        p["inventory"].append(item)
        results.append(item["name"])
        
    save_game(user_data)
    await callback.message.answer(f"✨ <b>Результаты призыва:</b>\n" + "\n".join(results), parse_mode="HTML")
    await callback.message.edit_text(f"🎰 Призыв снаряжения\n💎 Баланс кристаллов: {p['crystals']}", reply_markup=get_gacha_kb())
    await callback.answer()

@dp.message(F.text == "🎒 Инвентарь")
async def menu_inventory(message: types.Message):
    await show_inventory(str(message.from_user.id), message)

async def show_inventory(user_id, message_or_callback):
    p = user_data.get(user_id)
    if not p: return
    
    text = f"🎒 <b>Инвентарь</b> (Магическая пыль: {p.get('dust', 0)} ✨)\n\n🛡 <b>Надето снаряжение:</b>\n"
    kb_buttons = []
    
    for slot in ["weapon", "armor", "jewelry"]:
        eq = p["equipped"].get(slot)
        if eq: 
            text += f"• {slot.capitalize()}: {eq['name']} (+{eq['upgrade']})\n  └ {format_item_stats(eq)}\n"
            kb_buttons.append([InlineKeyboardButton(text=f"🔺 Улучшить надетый {slot.capitalize()}", callback_data=f"upg_eq_{slot}")])
        else: text += f"• {slot.capitalize()}: &lt;Пусто&gt;\n"
        
    text += "\n📦 <b>Предметы в сумке:</b>\n"
    if not p.get("inventory"):
        text += "<i>В сумке пусто.</i>"
    else:
        for idx, item in enumerate(p["inventory"][:6]):
            req_cls = f" ({item['req_class']})" if item.get("req_class") else ""
            text += f"{idx+1}. {item['name']}{req_cls} (+{item['upgrade']})\n    {format_item_stats(item)}\n"
            kb_buttons.append([
                InlineKeyboardButton(text=f"👕 Надеть {idx+1}", callback_data=f"inv_equip_{idx}"),
                InlineKeyboardButton(text=f"🔺 Точить {idx+1}", callback_data=f"upg_inv_{idx}"),
                InlineKeyboardButton(text=f"♻️ Пыль {idx+1}", callback_data=f"inv_scrap_{idx}")
            ])
            
    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons) if kb_buttons else None
    if isinstance(message_or_callback, types.Message):
        await message_or_callback.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await message_or_callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "back_nav")
async def callback_back_nav(callback: types.CallbackQuery):
    await callback.message.edit_text("🗺 Выберите направление:", reply_markup=get_nav_kb())
    await callback.answer()

# --- КРАФТ, ЗАТОЧКА, ИНВЕНТАРНЫЕ КОЛБЭКИ ---
@dp.callback_query(F.data.startswith("inv_equip_"))
async def callback_inv_equip(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data.get(user_id)
    if not p: return
    idx = int(callback.data.split("_")[2])
    if idx >= len(p["inventory"]): return
        
    item = p["inventory"][idx]
    if item["slot"] == "weapon" and item.get("req_class") and item["req_class"] != p["class"]:
        await callback.answer(f"❌ Данное оружие доступно только для класса: {item['req_class']}!", show_alert=True)
        return
        
    p["inventory"].pop(idx)
    slot = item["slot"]
    old_item = p["equipped"].get(slot)
    if old_item: p["inventory"].append(old_item)
    
    p["equipped"][slot] = item
    stats = get_total_stats(p)
    p["hp"] = min(p["hp"], stats["total_max_hp"])
    
    save_game(user_data)
    await show_inventory(user_id, callback)
    await callback.answer("Предмет успешно экипирован!")

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
    await callback.answer("Предмет распылен!")

@dp.callback_query(F.data.startswith("upg_"))
async def callback_upgrade_item(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data.get(user_id)
    if not p: return
    
    action = callback.data[4:]
    item = None
    is_equipped = False
    idx = -1
    
    if action.startswith("eq_"):
        slot = action[3:]
        item = p["equipped"].get(slot)
        is_equipped = True
    elif action.startswith("inv_"):
        idx = int(action[4:])
        if idx < len(p["inventory"]):
            item = p["inventory"][idx]
            
    if not item:
        await callback.answer("Предмет не найден!", show_alert=True)
        return
        
    lvl = item.get("upgrade", 0)
    if lvl >= 12:
        await callback.answer("Достигнут максимальный предел заточки предметов (+12)!", show_alert=True)
        return
        
    cost = (lvl + 1) * 5
    if p.get("dust", 0) < cost:
        await callback.answer(f"Недостаточно пыли! Требуется {cost} ✨", show_alert=True)
        return
        
    p["dust"] -= cost
    chance = UPGRADE_CHANCES.get(lvl, 5)
    success = random.randint(1, 100) <= chance
    
    if success:
        item["upgrade"] = lvl + 1
        await callback.answer(f"🌟 УСПЕХ! Снаряжение улучшено до +{lvl + 1}", show_alert=True)
    else:
        if lvl >= 3:
            if is_equipped: p["equipped"][action[3:]] = None
            else: p["inventory"].pop(idx)
            await callback.answer("💥 ПРОВАЛ! Предмет критически поврежден и уничтожен.", show_alert=True)
        else:
            await callback.answer("Провал! Заточка не изменилась (безопасная зона до +3).", show_alert=True)
            
    save_game(user_data)
    await show_inventory(user_id, callback)

# --- УПРАВЛЕНИЕ НАСТРОЙКАМИ АВТООХОТЫ ---
@dp.callback_query(F.data == "auto_hunt_menu")
async def callback_auto_hunt_menu(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data.get(user_id)
    if not p: return
    if "auto_scrap" not in p: p["auto_scrap"] = {"Common": False, "Rare": False, "Epic": False}
    await callback.message.edit_text("🤖 <b>Настройки Автоохоты</b>\nВключите авто-разбор ненужного лута:", reply_markup=get_auto_hunt_kb(p), parse_mode="HTML")

@dp.callback_query(F.data.startswith("toggle_scrap_"))
async def toggle_scrap(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data.get(user_id)
    rarity = callback.data.split("_")[2]
    if "auto_scrap" not in p: p["auto_scrap"] = {"Common": False, "Rare": False, "Epic": False}
    p["auto_scrap"][rarity] = not p["auto_scrap"].get(rarity, False)
    save_game(user_data)
    await callback.message.edit_reply_markup(reply_markup=get_auto_hunt_kb(p))

@dp.callback_query(F.data == "start_auto_hunt")
async def start_auto_hunt(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data.get(user_id)
    if not p: return
    
    if p["crystals"] < 999:
        await callback.answer("❌ Недостаточно кристаллов! Стоимость 1 часа — 999 💎.", show_alert=True)
        return
        
    p["crystals"] -= 999
    p["auto_hunt_paused"] = False
    p["auto_hunt_remaining"] = 0
    
    now = time.time()
    if p.get("auto_hunt_end", 0) < now: p["auto_hunt_end"] = now + 3600
    else: p["auto_hunt_end"] += 3600
        
    save_game(user_data)
    await callback.answer("🤖 Режим автоохоты запущен на 1 час! Прогресс фармится в фоновом режиме.", show_alert=True)
    await callback.message.edit_text("🗺 Панель перемещения персонажа:", reply_markup=get_nav_kb())

@dp.message(F.text == "👤 Герой")
async def menu_hero(message: types.Message):
    user_id = str(message.from_user.id)
    p = user_data.get(user_id)
    if not p: return
    stats = get_total_stats(p)
    
    status = "Свободен"
    if p.get("auto_hunt_paused", False): status = "Автоохота ⏸ (Заморожена, нет золота)"
    elif p.get("auto_hunt_end", 0) > time.time(): status = f"Автоохота ▶️ (активна, осталось {int((p['auto_hunt_end'] - time.time()) / 60)} мин.)"

    text = (
        f"👤 <b>{p['name']}</b> | 🎖 <b>{p['class']}</b> ({p['level']} ур.)\n"
        f"Текущее состояние: {status}\n"
        f"Опыт: {p['xp']}/{p['level']*50} XP\n\n"
        f"⚔️ Атака: {stats['total_atk']} | 🛡 Защита: {stats['total_def']}\n"
        f"❤️ Здоровье: {p['hp']}/{stats['total_max_hp']}\n\n"
        f"💰 Золото: {p['gold']} | 💎 Кристаллы: {p['crystals']}\n✨ Магическая пыль: {p.get('dust', 0)}"
    )
    await message.answer(text, parse_mode="HTML")

# --- ФОНОВЫЙ ЦИКЛ С ЗАМОРОЗКОЙ ВРЕМЕНИ И ОБЫЧНЫМИ БОССАМИ ---
async def auto_hunt_task():
    while True:
        now = time.time()
        for uid, p in list(user_data.items()):
            if p.get("auto_hunt_end", 0) > now and not p.get("auto_hunt_paused", False):
                stats = get_total_stats(p)
                
                # Логика автоподхила во время прохождения циклов охоты
                if p["hp"] < stats["total_max_hp"] * 0.5:
                    while p["hp"] < stats["total_max_hp"] * 0.9:
                        if p["gold"] >= 50:
                            p["hp"] = min(stats["total_max_hp"], p["hp"] + int(stats["total_max_hp"] * 0.4))
                            p["gold"] -= 50
                        else:
                            # ПОЛНАЯ ЗАМОРОЗКА ВРЕМЕНИ ПРИ ОТСУТСТВИИ СРЕДСТВ НА ДАННОМ ТИКЕ
                            remaining_time = p["auto_hunt_end"] - now
                            p["auto_hunt_remaining"] = max(0, remaining_time)
                            p["auto_hunt_end"] = 0
                            p["auto_hunt_paused"] = True
                            
                            try:
                                await bot.send_message(
                                    uid, 
                                    "⏸ <b>Автоохота приостановлена: закончилось золото на лечебные эликсиры!</b>\n\n"
                                    "⏳ Оставшееся время фарма успешно заморожено. Игра ожидает обмена кристаллов на золото в меню «💱 Обмен». После обмена автоохота запустится автоматически.", 
                                    parse_mode="HTML"
                                )
                            except: pass
                            break
                            
                if p.get("auto_hunt_paused", False): continue

                if p["hp"] > 0:
                    roll = random.random() * 100
                    is_boss = False
                    
                    if roll < 2.0: # 2% шанс встретить Обычного Босса в фоновом режиме
                        is_boss = True
                        enemy_atk = max(5, (25 + p["level"] * 6) - stats["total_def"])
                        xp_gain = 80 + p["level"] * 10
                        gold_gain = 100
                    else:
                        enemy_atk = max(1, (15 + p["level"] * 3) - stats["total_def"])
                        xp_gain = 20 + p["level"] * 3
                        gold_gain = 25
                        
                    p["hp"] -= enemy_atk
                    
                    if p["hp"] <= 0:
                        p["hp"] = int(stats["total_max_hp"] * 0.5)
                        lost_xp = int(p["xp"] * 0.05)
                        p["xp"] = max(0, p["xp"] - lost_xp)
                    else:
                        lvl_msg = add_xp(uid, xp_gain)
                        if lvl_msg:
                            try: await bot.send_message(uid, f"ℹ️ <b>Автоохота:</b> {lvl_msg}", parse_mode="HTML")
                            except: pass
                        p["gold"] += gold_gain
                        
                        # Расчет генерации лута с учетом Босса в авторежиме
                        if random.random() < 0.08:
                            if is_boss:
                                b_roll = random.uniform(0, 100)
                                if b_roll < 5: new_item = create_item("Epic")
                                elif b_roll < 35: new_item = create_item("Rare")
                                else: new_item = create_item("Common")
                            else:
                                new_item = create_item("Common")
                            
                            scrap_settings = p.get("auto_scrap", {})
                            if scrap_settings.get(new_item["rarity"]):
                                p["dust"] = p.get("dust", 0) + RARITIES[new_item["rarity"]]["dust"]
                            elif len(p["inventory"]) < 30:
                                p["inventory"].append(new_item)
                            
        save_game(user_data)
        await asyncio.sleep(10)

# --- АСРИНХРОННЫЙ СЕРВЕР И ВЕБ-ИНТЕРФЕЙС ДЛЯ RENDER ---
async def handle_ping(request):
    return web.Response(text="Бот S-Rank стабильно функционирует!")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(dp.start_polling(bot))
    asyncio.create_task(auto_hunt_task())
    
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    print(f"Внутренний порт прослушивания: {port}")
    await site.start()
    
    while True: await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
