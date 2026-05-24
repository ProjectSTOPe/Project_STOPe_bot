import asyncio
import json
import os
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Токен лучше хранить в переменных окружения, но для теста оставим здесь
BOT_TOKEN = "8824282617:AAF-4RmuPwJDMudFzzTjaf2koXvvBo1KlP4"
SAVE_FILE = "game_save.json"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def load_game():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r") as f: return json.load(f)
    return {}

def save_game(data):
    with open(SAVE_FILE, "w") as f: json.dump(data, f)

user_data = load_game()

def add_xp(user_id, amount):
    uid = str(user_id)
    if uid not in user_data: return
    user = user_data[uid]
    user["xp"] = user.get("xp", 0) + amount
    if user["xp"] >= 100:
        user["level"] += 1
        user["xp"] -= 100
        user["hp"] += 10
        user["strength"] += 2
    save_game(user_data)

# Улучшенное меню
def get_game_kb(in_combat=False):
    if in_combat:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚔️ Атаковать", callback_data="attack"), InlineKeyboardButton(text="🏃 Побег", callback_data="flee")]
        ])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬆️", callback_data="move_up"), InlineKeyboardButton(text="⬇️", callback_data="move_down")],
        [InlineKeyboardButton(text="⬅️", callback_data="move_left"), InlineKeyboardButton(text="➡️", callback_data="move_right")],
        [InlineKeyboardButton(text="🎒 Инвентарь", callback_data="inv"), InlineKeyboardButton(text="📊 Статус", callback_data="status")]
    ])

@dp.callback_query(F.data.startswith("move_"))
async def callback_move(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data[user_id]
    
    # Генерация мира
    locs = ["Лес", "Горы", "Болото", "Руины"]
    
    direction = callback.data.split("_")[1]
    if direction == "up": p['y'] -= 1
    elif direction == "down": p['y'] += 1
    elif direction == "left": p['x'] -= 1
    elif direction == "right": p['x'] += 1
    
    if random.random() < 0.35:
        p['enemy_hp'] = random.randint(10 + p['level']*5, 20 + p['level']*5)
        p['enemy_max'] = p['enemy_hp']
        await callback.message.edit_text(f"⚠️ Встретил монстра! HP: {p['enemy_hp']}", reply_markup=get_game_kb(in_combat=True))
    else:
        await callback.message.edit_text(f"Вы исследуете: {random.choice(locs)}\nКоординаты: {p['x']}:{p['y']}", reply_markup=get_game_kb())
    save_game(user_data)

@dp.callback_query(F.data == "attack")
async def callback_attack(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data[user_id]
    
    damage = random.randint(p['strength']-1, p['strength']+2)
    p['enemy_hp'] -= damage
    
    if p['enemy_hp'] <= 0:
        gold_drop = random.randint(5, 15)
        p['gold'] += gold_drop
        add_xp(user_id, 40)
        await callback.answer(f"Победа! +{gold_drop} золота")
        await callback.message.edit_text("Враг повержен! Куда идем дальше?", reply_markup=get_game_kb())
    else:
        # Ответный удар монстра
        monster_dmg = random.randint(2, 5)
        p['hp'] -= monster_dmg
        await callback.message.edit_text(f"Вы нанесли {damage} урона. Враг ударил вас на {monster_dmg}. У врага {p['enemy_hp']} HP", reply_markup=get_game_kb(in_combat=True))
    save_game(user_data)

@dp.callback_query(F.data == "flee")
async def callback_flee(callback: types.CallbackQuery):
    user_data[str(callback.from_user.id)]['enemy_hp'] = 0
    await callback.message.edit_text("Вы убежали от страха!", reply_markup=get_game_kb())

@dp.callback_query(F.data == "status")
async def callback_status(callback: types.CallbackQuery):
    p = user_data[str(callback.from_user.id)]
    await callback.message.edit_text(f"👤 {p['name']}\nУр: {p['level']} | XP: {p['xp']}/100\n❤️ {p['hp']} | 💰 {p['gold']} | ⚔️ Сила: {p['strength']}", reply_markup=get_game_kb())

async def main():
    await dp.start_polling(bot, drop_pending_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
    
