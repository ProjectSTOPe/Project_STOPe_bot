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

def load_game():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r") as f: return json.load(f)
    return {}

def save_game(data):
    with open(SAVE_FILE, "w") as f: json.dump(data, f)

user_data = load_game()

# Функция добавления опыта
def add_xp(user_id, amount):
    user = user_data.get(str(user_id))
    if not user: return
    
    user["xp"] = user.get("xp", 0) + amount
    if user["xp"] >= 100:
        user["level"] += 1
        user["xp"] = 0
        user["hp"] += 5 
    save_game(user_data)

# ТВОИ СТРЕЛОЧКИ И МЕНЮ
def get_game_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬆️ Вверх", callback_data="move_up"), InlineKeyboardButton(text="⬇️ Вниз", callback_data="move_down")],
        [InlineKeyboardButton(text="⬅️ Влево", callback_data="move_left"), InlineKeyboardButton(text="➡️ Вправо", callback_data="move_right")],
        [InlineKeyboardButton(text="🔍 Исследовать", callback_data="explore"), InlineKeyboardButton(text="⚔️ Атака", callback_data="attack")],
        [InlineKeyboardButton(text="📊 Статус", callback_data="status")]
    ])

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id not in user_data:
        user_data[user_id] = {
            "name": "Raimund", "hp": 20, "strength": 5, "gold": 250, 
            "level": 1, "xp": 0, "x": 15, "y": 9, "inventory": ["Зелье"], "enemy_hp": 0
        }
        save_game(user_data)
    await message.answer("Добро пожаловать в Project STOPe!", reply_markup=get_game_kb())

@dp.callback_query(F.data.startswith("move_"))
async def callback_move(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    direction = callback.data.split("_")[1]
    p = user_data[user_id]
    
    if direction == "up": p['y'] -= 1
    elif direction == "down": p['y'] += 1
    elif direction == "left": p['x'] -= 1
    elif direction == "right": p['x'] += 1
    
    if random.random() < 0.3:
        p['enemy_hp'] = random.randint(10, 15)
        await callback.message.edit_text(f"⚠️ Встретил врага! HP: {p['enemy_hp']}", reply_markup=get_game_kb())
    else:
        await callback.message.edit_text(f"Координаты: X={p['x']}, Y={p['y']}", reply_markup=get_game_kb())
    save_game(user_data)

@dp.callback_query(F.data == "attack")
async def callback_attack(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data[user_id]
    if p.get('enemy_hp', 0) > 0:
        p['enemy_hp'] -= p['strength']
        if p['enemy_hp'] <= 0:
            add_xp(user_id, 30)
            await callback.answer("Враг побежден! +30 XP")
            await callback.message.edit_text("Враг повержен!", reply_markup=get_game_kb())
        else:
            await callback.answer(f"Удар! Осталось {p['enemy_hp']} HP")
    else:
        await callback.answer("Врагов нет!")
    save_game(user_data)

@dp.callback_query(F.data == "status")
async def callback_status(callback: types.CallbackQuery):
    p = user_data[str(callback.from_user.id)]
    status_text = (f"👤 {p['name']} | Ур: {p['level']} | XP: {p['xp']}/100\n"
                   f"❤️ {p['hp']} | 💰 {p['gold']} | ⚔️ Сила: {p['strength']}\n"
                   f"📍 Координаты: {p['x']}:{p['y']}")
    await callback.message.edit_text(status_text, reply_markup=get_game_kb())

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
