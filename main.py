import asyncio
import json
import os
import random
import time
from datetime import date
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, LabeledPrice
from aiohttp import web

# --- КОНФИГУРАЦИЯ БОТА И ОПЛАТЫ ---
BOT_TOKEN = "8824282617:AAEd4ycUGPfdktkJR_Uks2sYlv7KgleJudE"
PAYMENT_PROVIDER_TOKEN = "" # Оставь пустым для приема Telegram Stars (XTR)
SAVE_FILE = "game_save.json" # Для Render замени на "/data/game_save.json"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
data_lock = asyncio.Lock()

# --- ДЕФОЛТНАЯ СТРУКТУРА ДАННЫХ ИГРОКА ---
DEFAULT_PLAYER_DATA = {
    "name": "Игрок",
    "class": None, 
    "level": 1, 
    "xp": 0,
    "gold": 5000, 
    "crystals": 10000, 
    "dust": 0, 
    "hp": 100, 
    "max_hp": 100,
    "strength": 5, 
    "agility": 5, 
    "intelligence": 5, 
    "defense": 2,
    "x": 10, 
    "y": 10, 
    "enemy_hp": 0, 
    "enemy_max": 0, 
    "enemy_type": "normal",
    "enemy_atk_mult": 1, 
    "pity_epic": 0, 
    "pity_leg": 0, 
    "auto_hunt_end": 0, 
    "auto_hunt_paused": False, 
    "auto_hunt_remaining": 0,
    "inventory": [], 
    "equipped": {"weapon": None, "armor": None, "jewelry": None},
    "auto_scrap": {"Common": False, "Rare": False, "Epic": False},
    # Новые поля для PvP:
    "pvp_rating": 1000,
    "pvp_wins": 0,
    "pvp_losses": 0,
    "pvp_attempts": 5,
    "pvp_last_reset": ""
}

user_data = {}

# --- УМНАЯ СИСТЕМА ЗАГРУЗКИ И СОХРАНЕНИЯ ---
def load_game():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for uid, player in data.items():
                    for key, default_value in DEFAULT_PLAYER_DATA.items():
                        if key not in player:
                            player[key] = default_value
                    if not isinstance(player.get("equipped"), dict):
                        player["equipped"] = DEFAULT_PLAYER_DATA["equipped"].copy()
                    if not isinstance(player.get("auto_scrap"), dict):
                        player["auto_scrap"] = DEFAULT_PLAYER_DATA["auto_scrap"].copy()
                return data
        except Exception as e:
            print(f"Ошибка чтения БД: {e}")
            return {}
    return {}

async def save_game():
    async with data_lock:
        try:
            with open(SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump(user_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Ошибка записи в БД: {e}")

# --- БАЗЫ ДАННЫХ И НАСТРОЙКИ ПРЕДМЕТОВ ---
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
ARMORS = ["Мантия Мудреца", "Кожаный Жилет", "Тяжелый Доспех", "Одеяние Теней", "Доспех Дракона"]
JEWELRY = ["Кольцо Всевластия", "Амулет Крови", "Ожерелье Света", "Серьга Удачи", "Талисман Бури"]

UPGRADE_CHANCES = {0: 100, 1: 100, 2: 100, 3: 70, 4: 60, 5: 50, 6: 40, 7: 30, 8: 20, 9: 15, 10: 10, 11: 5}

# --- МЕХАНИКА ХАРАКТЕРИСТИК И УРОВНЕЙ ---
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
    if p["level"] >= 999: return "\n⚡ Достигнут максимальный уровень!"
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
        lvl_up_msg += f"\n🎉 <b>УРОВЕНЬ ПОВЫШЕН до {p['level']}!</b> ОЗ полностью восстановлены."
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
        stats["atk"] = random.randint(5, 12) * mult; stats["hp"] = random.randint(0, 5) * mult
    elif slot == "armor":
        stats["hp"] = random.randint(20, 40) * mult; stats["def"] = random.randint(3, 8) * mult
    else: 
        stats["atk"] = random.randint(2, 6) * mult; stats["hp"] = random.randint(10, 20) * mult; stats["def"] = random.randint(1, 4) * mult
    return {"name": name, "slot": slot, "rarity": rarity_key, "stats": stats, "upgrade": 0, "req_class": req_class}

def perform_gacha_pull(p):
    p["pity_epic"] = p.get("pity_epic", 0) + 1
    p["pity_leg"] = p.get("pity_leg", 0) + 1
    forced_rarity = None
    if p["pity_leg"] >= 80: forced_rarity = "Legendary"
    elif p["pity_epic"] >= 20: forced_rarity = "Epic"
        
    if forced_rarity: rarity_key = forced_rarity
    else:
        roll = random.uniform(0, 100)
        if roll <= 0.5: rarity_key = "Mythic"
        elif roll <= 3.0: rarity_key = "Legendary"
        elif roll <= 15.0: rarity_key = "Epic"
        elif roll <= 40.0: rarity_key = "Rare"
        else: rarity_key = "Common"
            
    if rarity_key in ["Legendary", "Mythic"]: p["pity_leg"] = 0; p["pity_epic"] = 0
    elif rarity_key == "Epic": p["pity_epic"] = 0
    return create_item(rarity_key)

def format_item_stats(item):
    s = item["stats"]
    upg = item.get("upgrade", 0)
    return f"🗡 Атк: {s.get('atk',0)+(upg*2)} | 🛡 Защ: {s.get('def',0)+upg} | ❤️ HP: {s.get('hp',0)+(upg*5)}"

# --- МЕНЮ И КЛАВИАТУРЫ ---
def get_bottom_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🗺 Навигация"), KeyboardButton(text="⚔️ PvP")],
        [KeyboardButton(text="👤 Герой"), KeyboardButton(text="🎒 Инвентарь")],
        [KeyboardButton(text="🔮 Призыв"), KeyboardButton(text="💱 Обмен")],
        [KeyboardButton(text="💰 Донат")]
    ], resize_keyboard=True)

def get_pvp_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🏆 Рейтинговое PvP 1:1")],
        [KeyboardButton(text="🏅 Топ PvP - Игроков")],
        [KeyboardButton(text="🔙 Назад")]
    ], resize_keyboard=True)

def get_nav_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔼", callback_data="move_up")],
        [InlineKeyboardButton(text="◀️", callback_data="move_left"), InlineKeyboardButton(text="▶️", callback_data="move_right")],
        [InlineKeyboardButton(text="🔽", callback_data="move_down")],
        [InlineKeyboardButton(text="🤖 Автоохота", callback_data="auto_hunt_menu")]
    ])

def get_class_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔮 Маг", callback_data="choose_Маг")],
        [InlineKeyboardButton(text="🏹 Лучник", callback_data="choose_Лучник")],
        [InlineKeyboardButton(text="🛡 Танк", callback_data="choose_Танк")]
    ])

def get_combat_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Ударить", callback_data="battle_hit")],
        [InlineKeyboardButton(text="🧪 Зелье (50💰)", callback_data="battle_heal"), InlineKeyboardButton(text="🏃 Сбежать", callback_data="battle_flee")]
    ])

def get_gacha_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 Призыв ×1 (100 💎)", callback_data="gacha_1")],
        [InlineKeyboardButton(text="🎲 Призыв ×11 (1900 💎)", callback_data="gacha_11")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_nav")]
    ])

def get_auto_hunt_kb(p):
    scrap = p.get("auto_scrap", {})
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{'✅' if scrap.get('Common') else '❌'} Разбор Обычных", callback_data="toggle_scrap_Common")],
        [InlineKeyboardButton(text=f"{'✅' if scrap.get('Rare') else '❌'} Разбор Редких", callback_data="toggle_scrap_Rare")],
        [InlineKeyboardButton(text=f"{'✅' if scrap.get('Epic') else '❌'} Разбор Эпических", callback_data="toggle_scrap_Epic")],
        [InlineKeyboardButton(text="▶️ Запустить 1 час (999 💎)", callback_data="start_auto_hunt")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_nav")]
    ])

def get_donate_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 1000 кр. (5.5 TON / 9 USDT)", callback_data="buy_pack_1000")],
        [InlineKeyboardButton(text="💎 3000 кр. (16.5 TON / 27 USDT)", callback_data="buy_pack_3000")],
        [InlineKeyboardButton(text="💎 5000 кр. (27.5 TON / 45 USDT)", callback_data="buy_pack_5000")],
        [InlineKeyboardButton(text="💎 10000 кр. (55 TON / 90 USDT)", callback_data="buy_pack_10000")]
    ])

# --- ЛОГИКА PVP ---
def reset_pvp_attempts(p):
    today = date.today().isoformat()
    if p.get("pvp_last_reset") != today:
        p["pvp_attempts"] = 5
        p["pvp_last_reset"] = today

@dp.message(F.text == "⚔️ PvP")
async def menu_pvp_main(message: types.Message):
    await message.answer("⚔️ <b>Арена Героев</b>\nВыберите режим поединка снизу:", reply_markup=get_pvp_kb(), parse_mode="HTML")

@dp.message(F.text == "🔙 Назад")
async def menu_back_to_main(message: types.Message):
    await message.answer("Вы вернулись в главное меню.", reply_markup=get_bottom_kb())

@dp.message(F.text == "🏅 Топ PvP - Игроков")
async def menu_pvp_top(message: types.Message):
    sorted_users = sorted(user_data.values(), key=lambda x: x.get("pvp_rating", 1000), reverse=True)
    text = "🏆 <b>Топ-10 Арены:</b>\n\n"
    for i, u in enumerate(sorted_users[:10], 1):
        if not u.get("class"): continue # Пропускаем тех, кто не выбрал класс
        text += f"<b>{i}. {u['name']}</b> — {u.get('pvp_rating', 1000)} 🏆 (Поб: {u.get('pvp_wins',0)} | Пор: {u.get('pvp_losses',0)})\n"
    await message.answer(text, parse_mode="HTML")

@dp.message(F.text == "🏆 Рейтинговое PvP 1:1")
async def menu_pvp_ranked(message: types.Message):
    uid = str(message.from_user.id)
    p = user_data.get(uid)
    if not p: return
    reset_pvp_attempts(p)
    text = (
        f"🏆 <b>Рейтинговое PvP</b>\n\n"
        f"Ваш текущий рейтинг: <b>{p.get('pvp_rating', 1000)}</b> 🏆\n"
        f"Статистика: {p.get('pvp_wins', 0)} Поб. / {p.get('pvp_losses', 0)} Пор.\n"
        f"Попыток на сегодня: {p.get('pvp_attempts', 5)}/5"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔍 Искать Противника", callback_data="pvp_search")]])
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "pvp_search")
async def pvp_search_opponent(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    p = user_data.get(uid)
    if not p: return
    reset_pvp_attempts(p)
    
    # Ищем игроков, исключая себя и тех, кто не прошел обучение (нет класса)
    opponents = [u for u, data in user_data.items() if u != uid and data.get("class")]
    if not opponents:
        await callback.answer("Противники не найдены! В игре пока мало людей.", show_alert=True)
        return

    opp_id = random.choice(opponents)
    opp = user_data[opp_id]
    opp_stats = get_total_stats(opp)

    text = (
        f"🔍 <b>Противник найден!</b>\n\n"
        f"👤 <b>{opp['name']}</b> | 🎖 {opp['class']} ({opp['level']} ур.)\n"
        f"🏆 Рейтинг: {opp.get('pvp_rating', 1000)}\n"
        f"⚔️ Атака: {opp_stats['total_atk']} | 🛡 Защита: {opp_stats['total_def']}\n"
        f"❤️ HP: {opp_stats['total_max_hp']}\n"
        f"📊 Win/Loss: {opp.get('pvp_wins', 0)} / {opp.get('pvp_losses', 0)}\n\n"
        f"<i>У вас попыток: {p['pvp_attempts']}/5</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Атаковать", callback_data=f"pvp_attack_{opp_id}")],
        [InlineKeyboardButton(text="⏭ Следующий", callback_data="pvp_search")],
        [InlineKeyboardButton(text="➕ Купить Попытки +1 (300💰)", callback_data=f"pvp_buy_{opp_id}")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data.startswith("pvp_buy_"))
async def pvp_buy_attempt(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    p = user_data.get(uid)
    if not p: return
    opp_id = callback.data.split("_")[2]
    
    if p["gold"] < 300:
        await callback.answer("❌ Недостаточно золота (нужно 300 💰)!", show_alert=True)
        return
        
    p["gold"] -= 300
    p["pvp_attempts"] += 1
    await save_game()
    await callback.answer("✅ Попытка успешно куплена!", show_alert=True)
    
    # Обновляем текст, чтобы показать новую попытку
    opp = user_data.get(opp_id)
    if opp:
        opp_stats = get_total_stats(opp)
        text = (
            f"🔍 <b>Противник найден!</b>\n\n"
            f"👤 <b>{opp['name']}</b> | 🎖 {opp['class']} ({opp['level']} ур.)\n"
            f"🏆 Рейтинг: {opp.get('pvp_rating', 1000)}\n"
            f"⚔️ Атака: {opp_stats['total_atk']} | 🛡 Защита: {opp_stats['total_def']}\n"
            f"❤️ HP: {opp_stats['total_max_hp']}\n"
            f"📊 Win/Loss: {opp.get('pvp_wins', 0)} / {opp.get('pvp_losses', 0)}\n\n"
            f"<i>У вас попыток: {p['pvp_attempts']}</i>"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚔️ Атаковать", callback_data=f"pvp_attack_{opp_id}")],
            [InlineKeyboardButton(text="⏭ Следующий", callback_data="pvp_search")],
            [InlineKeyboardButton(text="➕ Купить Попытки +1 (300💰)", callback_data=f"pvp_buy_{opp_id}")]
        ])
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data.startswith("pvp_attack_"))
async def pvp_execute_attack(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    p = user_data.get(uid)
    if not p: return
    reset_pvp_attempts(p)

    if p["pvp_attempts"] <= 0:
        await callback.answer("❌ У вас закончились попытки! Купите новые или подождите до завтра.", show_alert=True)
        return

    opp_id = callback.data.split("_")[2]
    opp = user_data.get(opp_id)
    if not opp:
        await callback.answer("Противник не найден (возможно удалил профиль)!", show_alert=True)
        return

    p["pvp_attempts"] -= 1

    p_stats = get_total_stats(p)
    opp_stats = get_total_stats(opp)

    # Симуляция боя
    p_hp = p_stats["total_max_hp"]
    opp_hp = opp_stats["total_max_hp"]
    winner = None

    for _ in range(30): # Лимит в 30 раундов
        dmg_to_opp = max(1, random.randint(int(p_stats["total_atk"] * 0.8), int(p_stats["total_atk"] * 1.2)) - opp_stats["total_def"])
        opp_hp -= dmg_to_opp
        if opp_hp <= 0:
            winner = "player"
            break

        dmg_to_p = max(1, random.randint(int(opp_stats["total_atk"] * 0.8), int(opp_stats["total_atk"] * 1.2)) - p_stats["total_def"])
        p_hp -= dmg_to_p
        if p_hp <= 0:
            winner = "opp"
            break

    if winner is None:
        winner = "player" if p_hp > opp_hp else "opp"

    # Расчет рейтинга
    p_rating = p.get("pvp_rating", 1000)
    opp_rating = opp.get("pvp_rating", 1000)
    rating_diff = opp_rating - p_rating
    
    gain = int(40 + (rating_diff * 0.1))
    gain = max(10, min(80, gain)) # Очки рейтинга от 10 до 80

    if winner == "player":
        p["pvp_rating"] = p_rating + gain
        p["pvp_wins"] = p.get("pvp_wins", 0) + 1
        opp["pvp_losses"] = opp.get("pvp_losses", 0) + 1
        result_txt = f"🎉 <b>Вы одержали ПОБЕДУ над {opp['name']}!</b>\n\n🏆 Рейтинг: +{gain} (Текущий: {p['pvp_rating']})"
    else:
        loss = gain // 2
        p["pvp_rating"] = max(0, p_rating - loss)
        p["pvp_losses"] = p.get("pvp_losses", 0) + 1
        opp["pvp_wins"] = opp.get("pvp_wins", 0) + 1
        result_txt = f"💀 <b>Вы ПРОИГРАЛИ бой против {opp['name']}.</b>\n\n🏆 Рейтинг: -{loss} (Текущий: {p['pvp_rating']})"

    await save_game()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔍 Искать Противника", callback_data="pvp_search")]])
    await callback.message.edit_text(result_txt, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

# --- ОСНОВНЫЕ ОБРАБОТЧИКИ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id not in user_data or user_data[user_id].get("class") is None:
        user_data[user_id] = DEFAULT_PLAYER_DATA.copy()
        user_data[user_id]["name"] = message.from_user.first_name
        await save_game()
        await message.answer("Добро пожаловать в S-Rank Online!\nВыберите свой начальный класс:", reply_markup=get_class_kb())
    else:
        await message.answer("С возвращением в мир!", reply_markup=get_bottom_kb())
        await message.answer("🗺 Куда отправимся?", reply_markup=get_nav_kb())

@dp.callback_query(F.data.startswith("choose_"))
async def callback_choose_class(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    chosen_class = callback.data.split("_")[1]
    if user_id in user_data:
        user_data[user_id]["class"] = chosen_class
        if chosen_class == "Маг":
            user_data[user_id]["intelligence"] = 12; user_data[user_id]["max_hp"] = 70
        elif chosen_class == "Лучник":
            user_data[user_id]["agility"] = 12; user_data[user_id]["max_hp"] = 85
        elif chosen_class == "Танк":
            user_data[user_id]["strength"] = 12; user_data[user_id]["max_hp"] = 110
        user_data[user_id]["hp"] = user_data[user_id]["max_hp"]
        await save_game()
        await callback.message.edit_text(f"Вы выбрали класс: <b>{chosen_class}</b>! Ваше приключение началось.", reply_markup=None, parse_mode="HTML")
        await callback.message.answer("Панель управления активирована:", reply_markup=get_bottom_kb())

@dp.message(F.text == "💰 Донат")
async def menu_donate(message: types.Message):
    text = (
        "💰 <b>Донат-магазин кристаллов</b>\n\n"
        "💳 <b>Прайс-лист:</b>\n"
        "• 1 000 💎 — 5.5 TON / 9 USDT (450 ⭐️)\n"
        "• 3 000 💎 — 16.5 TON / 27 USDT (1350 ⭐️)\n"
        "• 5 000 💎 — 27.5 TON / 45 USDT (2250 ⭐️)\n"
        "• 10 000 💎 — 55.0 TON / 90 USDT (4500 ⭐️)"
    )
    await message.answer(text, reply_markup=get_donate_kb(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("buy_pack_"))
async def callback_buy_pack(callback: types.CallbackQuery):
    amount = int(callback.data.split("_")[2])
    if amount == 1000: stars_price = 450
    elif amount == 3000: stars_price = 1350
    elif amount == 5000: stars_price = 2250
    elif amount == 10000: stars_price = 4500
    else: stars_price = (amount // 1000) * 450
    
    await callback.message.answer_invoice(
        title=f"Пакет: {amount} Кристаллов",
        description=f"Зачисление +{amount} кристаллов.",
        payload=f"crystals_{amount}",
        provider_token=PAYMENT_PROVIDER_TOKEN,
        currency="XTR", 
        prices=[LabeledPrice(label=f"{amount} Кристаллов", amount=stars_price)]
    )
    await callback.answer()

@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def process_successful_payment(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id not in user_data: return
    amount = int(message.successful_payment.invoice_payload.split("_")[1])
    user_data[user_id]["crystals"] += amount
    await save_game()
    await message.answer(f"🎉 <b>Донат успешен!</b>\nНачислено: +{amount} 💎.", reply_markup=get_bottom_kb(), parse_mode="HTML")

@dp.message(F.text == "💱 Обмен")
async def menu_exchange(message: types.Message):
    user_id = str(message.from_user.id)
    p = user_data.get(user_id)
    if not p: return
    text = f"💱 <b>Обменник</b>\nВаши кристаллы: {p.get('crystals', 0)} 💎\nКурс: 100 💎 = 1000 💰"
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
        await callback.answer("❌ Недостаточно кристаллов!", show_alert=True)
        return
    p["crystals"] -= amount
    gold_gained = (amount // 100) * 1000
    p["gold"] = p.get("gold", 0) + gold_gained
    text = f"✅ Успешный обмен!\nПолучено: +{gold_gained} 💰\nОстаток: {p['crystals']} 💎"
    
    if p.get("auto_hunt_paused", False) and p["gold"] >= 50:
        p["auto_hunt_paused"] = False
        p["auto_hunt_end"] = time.time() + p.get("auto_hunt_remaining", 0)
        p["auto_hunt_remaining"] = 0
        text += "\n\n🤖 <b>Автоохота автоматически запущена снова!</b>"
        
    await save_game()
    await callback.message.edit_text(text, reply_markup=get_nav_kb(), parse_mode="HTML")

@dp.message(F.text == "🗺 Навигация")
async def menu_nav(message: types.Message):
    user_id = str(message.from_user.id)
    p = user_data.get(user_id)
    if p and p.get("enemy_hp", 0) > 0:
        await message.answer(f"🚨 Вы в бою!\n🩸 ХП Врага: {p['enemy_hp']}/{p['enemy_max']}", reply_markup=get_combat_kb())
    else:
        await message.answer("🗺 Выберите направление движения:", reply_markup=get_nav_kb())

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
        p["enemy_type"] = "boss_golden"; p["enemy_hp"] = base_boss_hp * 10; p["enemy_atk_mult"] = 5
        msg = f"🌟 <b>ЗОЛОТОЙ БОСС!</b>\n🩸 Здоровье: {p['enemy_hp']} HP."
    elif rand_enc < 3.5:
        p["enemy_type"] = "boss_black"; p["enemy_hp"] = base_boss_hp * 20; p["enemy_atk_mult"] = 2
        msg = f"🌑 <b>ЧЕРНЫЙ БОСС!</b>\n🩸 Здоровье: {p['enemy_hp']} HP."
    elif rand_enc < 8.5:
        p["enemy_type"] = "boss_red"; p["enemy_hp"] = base_boss_hp * 4; p["enemy_atk_mult"] = 10
        msg = f"🩸 <b>КРАСНЫЙ БОСС!</b>\n🩸 Здоровье: {p['enemy_hp']} HP."
    elif rand_enc < 18.5:
        p["enemy_type"] = "boss_normal"; p["enemy_hp"] = base_boss_hp; p["enemy_atk_mult"] = 2
        msg = f"👑 <b>ОБЫЧНЫЙ БОСС!</b>\n🩸 Здоровье: {p['enemy_hp']} HP."
    elif rand_enc < 48.5:
        p["enemy_type"] = "normal"
        p["enemy_hp"] = random.randint(30 + p["level"] * 6, 60 + p["level"] * 10)
        p["enemy_atk_mult"] = 1
        msg = f"👹 На вас напал монстр!\n🩸 Здоровье: {p['enemy_hp']} HP."
    else:
        p["enemy_hp"] = 0
        msg = f"🌲 На локации пусто.\n📍 Координаты: X: {p['x']} | Y: {p['y']}"
        
    p["enemy_max"] = p["enemy_hp"]
    await save_game()
    if p["enemy_hp"] > 0:
        await callback.message.edit_text(msg, reply_markup=get_combat_kb(), parse_mode="HTML")
    else:
        await callback.message.edit_text(msg, reply_markup=get_nav_kb())

@dp.callback_query(F.data == "battle_hit")
async def callback_battle_hit(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data.get(user_id)
    if not p or p.get("enemy_hp", 0) <= 0: return
    stats = get_total_stats(p)
    player_dmg = max(1, random.randint(int(stats["total_atk"] * 0.8), int(stats["total_atk"] * 1.2)))
    p["enemy_hp"] -= player_dmg
    
    if p["enemy_hp"] <= 0:
        p["enemy_hp"] = 0
        drop_item = None
        roll = random.uniform(0, 100)
        e_type = p.get("enemy_type", "normal")
        
        if e_type == "boss_golden": drop_item = create_item("Mythic" if roll < 1 else "Legendary" if roll < 12 else "Epic"); xp_gain = 500 + (p["level"] * 50); gold_gain = 1000
        elif e_type == "boss_black": drop_item = create_item("Legendary" if roll < 5 else "Epic" if roll < 25 else "Rare"); xp_gain = 300 + (p["level"] * 30); gold_gain = 500
        elif e_type == "boss_red": drop_item = create_item("Legendary" if roll < 3 else "Epic" if roll < 15 else "Rare"); xp_gain = 250 + (p["level"] * 25); gold_gain = 400
        elif e_type == "boss_normal": drop_item = create_item("Epic" if roll < 5 else "Rare" if roll < 35 else "Common"); xp_gain = 100 + (p["level"] * 15); gold_gain = 150
        else:
            if roll < 15: drop_item = create_item("Common")
            xp_gain = 25 + (p["level"] * 5); gold_gain = 30

        p["gold"] += gold_gain
        p["crystals"] += random.randint(1, 5) if e_type == "normal" else random.randint(10, 50)
        lvl_up_text = add_xp(user_id, xp_gain)
        
        reward_txt = f"⚔️ <b>Вы победили!</b>\n🔹 Опыт: +{xp_gain}\n💰 Золото: +{gold_gain}"
        if drop_item:
            p["inventory"].append(drop_item)
            reward_txt += f"\n🎁 Награда: {drop_item['name']}"
        await callback.message.edit_text(reward_txt + lvl_up_text, reply_markup=get_nav_kb(), parse_mode="HTML")
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
            await callback.message.edit_text(f"💀 <b>Вы погибли!</b> Потеря опыта: -{lost_xp} XP.", reply_markup=get_nav_kb(), parse_mode="HTML")
        else:
            await callback.message.edit_text(f"⚔️ Урон: {player_dmg} | 👹 Ответный удар: {monster_dmg}\n\n❤️ Ваше HP: {p['hp']}/{stats['total_max_hp']}\n🩸 HP Врага: {p['enemy_hp']}/{p['enemy_max']}", reply_markup=get_combat_kb())
    await save_game()

@dp.callback_query(F.data == "battle_heal")
async def callback_battle_heal(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data.get(user_id)
    if not p: return
    stats = get_total_stats(p)
    if p["gold"] < 50:
        await callback.answer("❌ Нужно 50 💰 для покупки зелья!", show_alert=True)
        return
    if p["hp"] >= stats["total_max_hp"]:
        await callback.answer("Здоровье уже заполнено!", show_alert=True)
        return
    p["gold"] -= 50
    p["hp"] = min(stats["total_max_hp"], p["hp"] + int(stats["total_max_hp"] * 0.4))
    await save_game()
    await callback.message.edit_text(f"🧪 Вы выпили зелье!\n❤️ Ваше HP: {p['hp']}/{stats['total_max_hp']}\n🩸 HP Врага: {p['enemy_hp']}/{p['enemy_max']}", reply_markup=get_combat_kb())

@dp.callback_query(F.data == "battle_flee")
async def callback_battle_flee(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data.get(user_id)
    if not p: return
    if "boss" in p.get("enemy_type", ""):
        await callback.answer("❌ Из логова Босса сбежать нельзя!", show_alert=True)
        return
    p["enemy_hp"] = 0
    await save_game()
    await callback.message.edit_text("💨 Вы успешно сбежали из боя.", reply_markup=get_nav_kb())

@dp.message(F.text == "🔮 Призыв")
async def menu_gacha(message: types.Message):
    user_id = str(message.from_user.id)
    p = user_data.get(user_id)
    if not p: return
    text = f"🎰 <b>Призыв S-Rank Оружия и Брони</b>\n\n💎 Баланс: {p['crystals']} кр.\nМифик: 0.5% | Легенда: 2.5% | Эпик: 12%"
    await message.answer(text, reply_markup=get_gacha_kb(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("gacha_"))
async def callback_do_gacha(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data.get(user_id)
    if not p: return
    amount = int(callback.data.split("_")[1])
    cost = 100 if amount == 1 else 1900
    if p["crystals"] < cost:
        await callback.answer("❌ Не хватает кристаллов!", show_alert=True)
        return
    if len(p["inventory"]) + amount > 30:
        await callback.answer("🎒 Инвентарь переполнен! Максимум 30 предметов.", show_alert=True)
        return

    p["crystals"] -= cost
    results = []
    for _ in range(amount):
        item = perform_gacha_pull(p)
        p["inventory"].append(item)
        results.append(item["name"])
    await save_game()
    await callback.message.answer(f"✨ <b>Результаты призыва:</b>\n" + "\n".join(results), parse_mode="HTML")
    await callback.message.edit_text(f"🎰 Призыв снаряжения\n💎 Кристаллы: {p['crystals']}", reply_markup=get_gacha_kb())

@dp.message(F.text == "🎒 Инвентарь")
async def menu_inventory(message: types.Message):
    await show_inventory(str(message.from_user.id), message)

async def show_inventory(user_id, message_or_callback):
    p = user_data.get(user_id)
    if not p: return
    text = f"🎒 <b>Инвентарь</b> (Энерг. пыль: {p.get('dust', 0)} ✨)\n\n🛡 <b>Экипировано:</b>\n"
    kb_buttons = []
    for slot in ["weapon", "armor", "jewelry"]:
        eq = p["equipped"].get(slot)
        if eq: 
            text += f"• {slot.capitalize()}: {eq['name']} (+{eq['upgrade']})\n  └ {format_item_stats(eq)}\n"
            kb_buttons.append([InlineKeyboardButton(text=f"🔺 Улучшить {slot.capitalize()}", callback_data=f"upg_eq_{slot}")])
        else: text += f"• {slot.capitalize()}: &lt;Пусто&gt;\n"
        
    text += "\n📦 <b>В сумке:</b>\n"
    if not p.get("inventory"): text += "<i>Пусто.</i>"
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
    await callback.message.edit_text("🗺 Выберите направление движения:", reply_markup=get_nav_kb())

@dp.callback_query(F.data.startswith("inv_equip_"))
async def callback_inv_equip(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data.get(user_id)
    idx = int(callback.data.split("_")[2])
    if idx >= len(p["inventory"]): return
    item = p["inventory"][idx]
    if item["slot"] == "weapon" and item.get("req_class") and item["req_class"] != p["class"]:
        await callback.answer(f"❌ Оружие только для класса: {item['req_class']}!", show_alert=True)
        return
    p["inventory"].pop(idx)
    slot = item["slot"]
    old_item = p["equipped"].get(slot)
    if old_item: p["inventory"].append(old_item)
    p["equipped"][slot] = item
    stats = get_total_stats(p)
    p["hp"] = min(p["hp"], stats["total_max_hp"])
    await save_game()
    await show_inventory(user_id, callback)

@dp.callback_query(F.data.startswith("inv_scrap_"))
async def callback_inv_scrap(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data.get(user_id)
    idx = int(callback.data.split("_")[2])
    if idx >= len(p["inventory"]): return
    item = p["inventory"].pop(idx)
    p["dust"] = p.get("dust", 0) + RARITIES[item["rarity"]]["dust"]
    await save_game()
    await show_inventory(user_id, callback)

@dp.callback_query(F.data.startswith("upg_"))
async def callback_upgrade_item(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data.get(user_id)
    if not p: return
    action = callback.data[4:]
    item = None; is_equipped = False; idx = -1
    
    if action.startswith("eq_"):
        slot = action[3:]
        item = p["equipped"].get(slot)
        is_equipped = True
    elif action.startswith("inv_"):
        idx = int(action[4:])
        if idx < len(p["inventory"]): item = p["inventory"][idx]
            
    if not item: return
    lvl = item.get("upgrade", 0)
    if lvl >= 12: 
        await callback.answer("Максимальный уровень заточки предмета (+12)!", show_alert=True)
        return
    cost = (lvl + 1) * 5
    if p.get("dust", 0) < cost:
        await callback.answer(f"Не хватает пыли! Требуется: {cost} ✨", show_alert=True)
        return
        
    p["dust"] -= cost
    if random.randint(1, 100) <= UPGRADE_CHANCES.get(lvl, 5):
        item["upgrade"] = lvl + 1
        await callback.answer(f"🌟 Заточка успешна! Уровень поднят до +{lvl + 1}", show_alert=True)
    else:
        if lvl >= 3:
            if is_equipped: p["equipped"][action[3:]] = None
            else: p["inventory"].pop(idx)
            await callback.answer("💥 КРИТИЧЕСКИЙ ПРОВАЛ! Предмет полностью уничтожен.", show_alert=True)
        else:
            await callback.answer("Провал! Но уровень заточки сохранен (безопасная зона).", show_alert=True)
    await save_game()
    await show_inventory(user_id, callback)

@dp.callback_query(F.data == "auto_hunt_menu")
async def callback_auto_hunt_menu(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data.get(user_id)
    if not p: return
    await callback.message.edit_text("🤖 <b>Настройки AFK-автоохоты</b>", reply_markup=get_auto_hunt_kb(p), parse_mode="HTML")

@dp.callback_query(F.data.startswith("toggle_scrap_"))
async def toggle_scrap(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data.get(user_id)
    rarity = callback.data.split("_")[2]
    p["auto_scrap"][rarity] = not p["auto_scrap"].get(rarity, False)
    await save_game()
    await callback.message.edit_reply_markup(reply_markup=get_auto_hunt_kb(p))

@dp.callback_query(F.data == "start_auto_hunt")
async def start_auto_hunt(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data.get(user_id)
    if not p: return
    if p["crystals"] < 999:
        await callback.answer("❌ Нужно 999 💎 на 1 час!", show_alert=True)
        return
    p["crystals"] -= 999
    p["auto_hunt_paused"] = False
    p["auto_hunt_remaining"] = 0
    now = time.time()
    p["auto_hunt_end"] = now + 3600 if p.get("auto_hunt_end", 0) < now else p["auto_hunt_end"] + 3600
    await save_game()
    await callback.answer("🤖 Модуль автоохоты запущен!", show_alert=True)
    await callback.message.edit_text("🗺 Выберите направление движения:", reply_markup=get_nav_kb())

@dp.message(F.text == "👤 Герой")
async def menu_hero(message: types.Message):
    user_id = str(message.from_user.id)
    p = user_data.get(user_id)
    if not p: return
    stats = get_total_stats(p)
    status = "В городе (Отдых)"
    if p.get("auto_hunt_paused", False): status = "Автоохота ⏸ (Заморожена — нет золота)"
    elif p.get("auto_hunt_end", 0) > time.time(): status = f"Автоохота ▶️ (Осталось {int((p['auto_hunt_end'] - time.time()) / 60)} мин.)"

    text = (
        f"👤 <b>{p['name']}</b> | 🎖 <b>{p['class']}</b> ({p['level']} ур.)\n"
        f"Статус: {status}\nОпыт: {p['xp']}/{p['level']*50} XP\n\n"
        f"⚔️ Атака: {stats['total_atk']} | 🛡 Защита: {stats['total_def']}\n"
        f"❤️ Здоровье: {p['hp']}/{stats['total_max_hp']}\n\n"
        f"💰 Золото: {p['gold']} | 💎 Кристаллы: {p['crystals']}\n✨ Пыль: {p.get('dust', 0)}"
    )
    await message.answer(text, parse_mode="HTML")

# --- ФОНОВЫЙ ЦИКЛ ОБРАБОТКИ АВТООХОТЫ ---
async def auto_hunt_task():
    while True:
        now = time.time()
        for uid, p in list(user_data.items()):
            if p.get("auto_hunt_end", 0) > now and not p.get("auto_hunt_paused", False):
                stats = get_total_stats(p)
                if p["hp"] < stats["total_max_hp"] * 0.5:
                    while p["hp"] < stats["total_max_hp"] * 0.9:
                        if p["gold"] >= 50:
                            p["hp"] = min(stats["total_max_hp"], p["hp"] + int(stats["total_max_hp"] * 0.4))
                            p["gold"] -= 50
                        else:
                            p["auto_hunt_remaining"] = max(0, p["auto_hunt_end"] - now)
                            p["auto_hunt_end"] = 0; p["auto_hunt_paused"] = True
                            try: await bot.send_message(uid, "⏸ <b>Автоохота приостановлена: закончилось золото!</b>", parse_mode="HTML")
                            except: pass
                            break
                            
                if p.get("auto_hunt_paused", False): continue
                if p["hp"] > 0:
                    roll = random.random() * 100
                    is_boss = roll < 2.0
                    if is_boss:
                        enemy_atk = max(5, (25 + p["level"] * 6) - stats["total_def"])
                        xp_gain = 80 + p["level"] * 10; gold_gain = 100
                    else:
                        enemy_atk = max(1, (15 + p["level"] * 3) - stats["total_def"])
                        xp_gain = 20 + p["level"] * 3; gold_gain = 25
                        
                    p["hp"] -= enemy_atk
                    if p["hp"] <= 0:
                        p["hp"] = int(stats["total_max_hp"] * 0.5)
                        p["xp"] = max(0, p["xp"] - int(p["xp"] * 0.05))
                    else:
                        lvl_msg = add_xp(uid, xp_gain)
                        if lvl_msg:
                            try: await bot.send_message(uid, lvl_msg, parse_mode="HTML")
                            except: pass
                        p["gold"] += gold_gain
                        if random.random() < 0.08:
                            if is_boss:
                                b_roll = random.uniform(0, 100)
                                new_item = create_item("Epic" if b_roll < 10 else "Rare" if b_roll < 45 else "Common")
                            else: new_item = create_item("Common")
                            if p["auto_scrap"].get(new_item["rarity"]):
                                p["dust"] = p.get("dust", 0) + RARITIES[new_item["rarity"]]["dust"]
                            elif len(p["inventory"]) < 30: p["inventory"].append(new_item)
        await save_game()
        await asyncio.sleep(10)

async def handle_ping(request): return web.Response(text="S-Rank Online работает!")

async def main():
    global user_data
    user_data = load_game()
    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(dp.start_polling(bot))
    asyncio.create_task(auto_hunt_task())
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 10000))).start()
    while True: await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
