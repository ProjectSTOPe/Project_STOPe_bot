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

CLASSES = {
    "Воин": {"hp": 30, "strength": 8},
    "Маг": {"hp": 15, "strength": 12},
    "Лучник": {"hp": 20, "strength": 6}
}

# Кнопки меню
def get_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Атака", callback_data="attack"), InlineKeyboardButton(text="🔍 Исследовать", callback_data="explore")],
        [InlineKeyboardButton(text="📊 Статус", callback_data="status")]
    ])

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id not in user_data:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Воин", callback_data="class_Воин")],
            [InlineKeyboardButton(text="Маг", callback_data="class_Маг")],
            [InlineKeyboardButton(text="Лучник", callback_data="class_Лучник")]
        ])
        await message.answer("Выберите ваш класс:", reply_markup=kb)
    else:
        await message.answer("Главное меню:", reply_markup=get_main_kb())

@dp.callback_query(F.data.startswith("class_"))
async def set_class(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    cls = callback.data.split("_")[1]
    stats = CLASSES[cls]
    user_data[user_id] = {
        "name": "Герой", "class": cls, "hp": stats["hp"], "max_hp": stats["hp"],
        "strength": stats["strength"], "level": 1, "xp": 0, "gold": 100
    }
    save_game(user_data)
    await callback.message.edit_text(f"Вы выбрали {cls}!", reply_markup=get_main_kb())

@dp.callback_query(F.data == "status")
async def callback_status(callback: types.CallbackQuery):
    p = user_data[str(callback.from_user.id)]
    text = (f"👤 {p['name']} ({p['class']})\n"
            f"⭐ Уровень: {p['level']} | XP: {p['xp']}/100\n"
            f"❤️ HP: {p['hp']}/{p['max_hp']}\n"
            f"⚔️ Сила: {p['strength']} | 💰 Золото: {p['gold']}")
    await callback.message.edit_text(text, reply_markup=get_main_kb())

@dp.callback_query(F.data == "attack")
async def callback_attack(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    p = user_data[user_id]
    p['xp'] += 20
    if p['xp'] >= 100:
        p['level'] += 1
        p['xp'] = 0
        p['max_hp'] += 10
        p['hp'] = p['max_hp']
        await callback.answer("Уровень повышен!")
    save_game(user_data)
    await callback.message.edit_text("Вы победили монстра! +20 XP", reply_markup=get_main_kb())

@dp.callback_query(F.data == "explore")
async def callback_explore(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    gold_found = random.randint(10, 50)
    user_data[user_id]['gold'] += gold_found
    save_game(user_data)
    await callback.message.edit_text(f"Вы исследовали местность и нашли {gold_found} золота!", reply_markup=get_main_kb())

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
