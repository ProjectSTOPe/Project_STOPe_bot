import telebot, sqlite3, random, time, requests
from telebot import types
TOKEN = '8840112637:AAFe2OMBNVdZ9bVCWrgVEsZeZc-9nsnhF4k'
bot = telebot.TeleBot(TOKEN)
MY_WALLET = "UQBpJQIxJSCMMatGblXhEm1832gmW473Zm8oYh5fsUNsSi8M"
def init_db():
    conn = sqlite3.connect('stope_v2.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS players
                 (uid INTEGER PRIMARY KEY, name TEXT, class TEXT, lvl INTEGER, exp INTEGER,
                  atk INTEGER, deff INTEGER, gold INTEGER, crystals INTEGER DEFAULT 10000,
                  afk_start INTEGER DEFAULT 0, afk_hours INTEGER DEFAULT 0,
                  afk_type TEXT DEFAULT 'hunt',
                  dungeon_exp_limit INTEGER DEFAULT 0,
                  dungeon_gold_limit INTEGER DEFAULT 0,
                  dungeon_crystals_limit INTEGER DEFAULT 0,
                  eq_weapon INTEGER DEFAULT 0, eq_helm INTEGER DEFAULT 0, eq_armor INTEGER DEFAULT 0,
                  eq_boots INTEGER DEFAULT 0, eq_ring INTEGER DEFAULT 0, eq_amulet INTEGER DEFAULT 0,
                  eq_shield INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, uid INTEGER, item_name TEXT, item_type TEXT,
                  grade TEXT, enhance INTEGER, item_atk INTEGER DEFAULT 0, item_deff INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS payments (memo TEXT PRIMARY KEY)''')
    conn.commit(); conn.close()
init_db()
CLASSES = {
    "Berserker": {"atk": 45, "deff": 15}, "Vanguard": {"atk": 25, "deff": 35},
    "Assassin": {"atk": 55, "deff": 10}, "Night Ranger": {"atk": 40, "deff": 15},
    "Elementalist": {"atk": 50, "deff": 8}, "Deathbringer": {"atk": 42, "deff": 18},
    "Divine Caster": {"atk": 20, "deff": 25}, "Destroyer": {"atk": 35, "deff": 22}
}
GRADES = {"Серый": "⬜", "Зеленый": "🟢", "Синий": "🔵", "Фиолетовый": "🟣", "Золотой": "🟡", "Красный": "🔴"}
GRADE_MULTIPLIERS = {
    "Серый": 1, "Зеленый": 3, "Синий": 7, "Фиолетовый": 15, "Золотой": 35, "Красный": 80
}
LOOT_POOL = [
    {"name": "Стальной клинок", "type": "weapon"}, {"name": "Стальной шлем", "type": "helm"},
    {"name": "Чешуйчатый доспех", "type": "armor"}, {"name": "Кожаные сапоги охотника", "type": "boots"},
    {"name": "Оловянное кольцо", "type": "ring"}, {"name": "Серебряный амулет", "type": "amulet"},
    {"name": "Деревянный щит", "type": "shield"}, {"name": "Медное кольцо", "type": "ring"}
]
def get_db(): return sqlite3.connect('stope_v2.db', check_same_thread=False)
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🤖 Охота (АФК)", "🎒 Инвентарь", "🥊 Арена PvP", "👤 Статы", "🛒 Maгaзин / Донат", "💎 Гача")
    return markup
def generate_item_stats(item_type, grade):
    mult = GRADE_MULTIPLIERS.get(grade, 1)
    item_atk, item_deff = 0, 0
    if item_type in ["weapon", "ring", "amulet"]:
        item_atk = random.randint(3, 6) * mult
        item_deff = random.randint(0, 1) * mult
    else:
        item_atk = random.randint(0, 1) * mult
        item_deff = random.randint(4, 8) * mult
    return item_atk, item_deff
def get_total_stats(uid, c):
    c.execute("SELECT atk, deff, eq_weapon, eq_helm, eq_armor, eq_boots, eq_ring, eq_amulet, eq_shield FROM players WHERE uid=?", (uid,))
    p = c.fetchone()
    if not p: return 0, 0
    base_atk, base_deff = p[0], p[1]
    eq_ids = p[2:]
    bonus_atk, bonus_deff = 0, 0
    for item_id in eq_ids:
        if item_id and item_id != 0:
            c.execute("SELECT item_atk, item_deff FROM inventory WHERE id=?", (item_id,))
            inv_stat = c.fetchone()
            if inv_stat:
                bonus_atk += inv_stat[0]
                bonus_deff += inv_stat[1]
    return (base_atk + bonus_atk), (base_deff + bonus_deff)
@bot.message_handler(commands=['start'])
def start(m):
    conn = get_db(); c = conn.cursor()
    tg_name = m.from_user.first_name if m.from_user.first_name else "Охотник"
    c.execute("SELECT class FROM players WHERE uid=?", (m.chat.id,))
    user = c.fetchone()
    if user and user[0] is not None:
        c.execute("UPDATE players SET name=? WHERE uid=?", (tg_name, m.chat.id)); conn.commit()
        bot.send_message(m.chat.id, f"⚔️ С возвращением, <b>{tg_name}</b>!", reply_markup=main_menu(), parse_mode="HTML")
    else:
        markup = types.InlineKeyboardMarkup(row_width=2)
        for cls in CLASSES.keys(): markup.add(types.InlineKeyboardButton(cls, callback_data=f"setcls_{cls}"))
        c.execute("INSERT OR REPLACE INTO players (uid, name, class, lvl, exp, atk, deff, gold, crystals) VALUES (?, ?, NULL, 1, 0, 10, 10, 777000, 10000)")
        conn.commit()
        bot.send_message(m.chat.id, f"🌑 Добро пожаловать, {tg_name}.\nВам начислено стартовый бонус: 💰 777,000 Золота и 💎 10,000 Алмазов!\nВыберите стартовый класс для продолжения:", reply_markup=markup)
    conn.close()
@bot.message_handler(func=lambda m: m.text == "👤 Статы")
def profile_stats(m):
    conn = get_db(); c = conn.cursor()
    tg_name = m.from_user.first_name if m.from_user.first_name else "Охотник"
    c.execute("UPDATE players SET name=? WHERE uid=?", (tg_name, m.chat.id)); conn.commit()
    c.execute("SELECT name, class, lvl, exp, atk, deff, gold, crystals FROM players WHERE uid=?", (m.chat.id,))
    p = c.fetchone()
    if p:
        total_atk, total_deff = get_total_stats(m.chat.id, c)
        total_hp = 100 + (p[2] * 20) + (total_deff * 5)
        msg = f"👤 <b>Игрок:</b> {p[0]}\n🛡️ <b>Класс:</b> {p[1]}\n📊 <b>Уровень:</b> {p[2]} (XP: {p[3]})\n" \
              f"❤️ <b>Здоровье (HP):</b> {total_hp}\n\n" \
              f"⚔️ <b>Общая Атака:</b> {total_atk} <tg-spoiler>(базовая {p[4]})</tg-spoiler>\n" \
              f"🛡️ <b>Общая Защита:</b> {total_deff} <tg-spoiler>(базовая {p[5]})</tg-spoiler>\n\n" \
              f"💰 <b>Золото:</b> {p[6]}\n💎 <b>Кристаллы:</b> {p[7]}\n"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔄 Сменит класс (10,000 💎)", callback_data="buy_class_change"))
        bot.send_message(m.chat.id, msg, reply_markup=markup, parse_mode="HTML")
    conn.close()
@bot.message_handler(func=lambda m: m.text == "🛒 Maгaзин / Донат")
def shop_menu(m):
    text = "🛒 <b>Игровой магазин & Донат TON</b>\n──────────────────────────\n💰 <b>Курс: 100 💎 = 1 TON</b>\n\n💎 <b>Доступные пакеты:</b>\n• 100 💎 — 1.0 TON\n• 500 💎 — 5.0 TON\n• 1,000 💎 — 10.0 TON\n\n<i>Выберите необходимый пакет для покупки:</i>"
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("💎 100 Кристаллов (1 TON)", callback_data="donate_100"),
        types.InlineKeyboardButton("💎 500 Кристаллов (5 TON)", callback_data="donate_500"),
        types.InlineKeyboardButton("💎 1,000 Кристаллов (10 TON)", callback_data="donate_1000")
    )
    bot.send_message(m.chat.id, text, reply_markup=markup, parse_mode="HTML")
@bot.message_handler(func=lambda m: m.text == "💎 Гача")
def gacha_menu(m):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT crystals FROM players WHERE uid=?", (m.chat.id,))
    crystals = c.fetchone()[0]
    text = f"💎 <b>Мистическая Гача Raven 2</b>\n──────────────────────────\nТвой баланс: <b>{crystals} 💎</b>\n\n🍀 <b>Шансы предметов (Гача):</b>\n🔴 Красный — 0.2%\n🟡 Золотой — 1.8%\n🟣 Фиолетовый — 5.0%\n🔵 Синий — 11.0%\n🟢 Зелёный — 32.0%\n⬜ Серый — 50.0%"
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🔮 1 Крутка (100 💎)", callback_data="gacha_1"), types.InlineKeyboardButton("🔥 11 Круток (1800 💎)", callback_data="gacha_11"))
    bot.send_message(m.chat.id, text, reply_markup=markup, parse_mode="HTML")
    conn.close()
@bot.callback_query_handler(func=lambda call: not call.data.startswith("starthunt_") and not call.data.startswith("startdg_"))
def inline_handler(call):
    uid = call.from_user.id
    conn = get_db(); c = conn.cursor()
    if call.data.startswith("setcls_"):
        cls_name = call.data.split("_")[1]
        stats = CLASSES[cls_name]
        c.execute("SELECT class FROM players WHERE uid=?", (uid,))
        user_exists = c.fetchone()
        if user_exists and user_exists[0] is not None:
            c.execute("SELECT crystals FROM players WHERE uid=?", (uid,))
            if c.fetchone()[0] < 10000:
                bot.answer_callback_query(call.id, "❌ Нужно 10,000 💎!")
                conn.close(); return
            c.execute("UPDATE players SET class=?, atk=?, deff=?, crystals=crystals-10000 WHERE uid=?", (cls_name, stats["atk"], stats["deff"], uid))
        else:
            c.execute("UPDATE players SET class=?, atk=?, deff=? WHERE uid=?", (cls_name, stats["atk"], stats["deff"], uid))
        conn.commit(); bot.delete_message(call.message.chat.id, call.message.message_id)
    elif call.data == "buy_class_change":
        markup = types.InlineKeyboardMarkup(row_width=2)
        for cls in CLASSES.keys(): markup.add(types.InlineKeyboardButton(f"{cls}", callback_data=f"setcls_{cls}"))
        bot.edit_message_text("🔄 Выберите новый класс (10,000 💎):", uid, call.message.message_id, reply_markup=markup)
    elif call.data.startswith("donate_"):
        amount = int(call.data.split("_")[1])
        ton_val = float(amount / 100)
        memo_comment = f"stope_{uid}_{random.randint(1000,9999)}"
        pay_text = f"💎 <b>Покупка {amount} Кристаллов</b>\nПереведите <b>{ton_val} TON</b> на:\n<code>{MY_WALLET}</code>\n\n⚠️ <b>КОММЕНТАРИЙ (ОБЯЗАТЕЛЬНО):</b>\n<code>{memo_comment}</code>"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("👛 Открыть Кошелёк", url=f"https://t.me/wallet?start=transfer_{MY_WALLET}_{int(ton_val*1e9)}_{memo_comment}"))
        markup.add(types.InlineKeyboardButton("✅ Проверить", callback_data=f"checkpay_{amount}_{memo_comment}"))
        bot.send_message(uid, pay_text, reply_markup=markup, parse_mode="HTML")
    elif call.data.startswith("checkpay_"):
        _, amount_str, memo = call.data.split("_")
        amount = int(amount_str)
        c.execute("SELECT memo FROM payments WHERE memo=?", (memo,))
        if c.fetchone(): bot.answer_callback_query(call.id, "❌ Уже зачислен!"); conn.close(); return
        try:
            url = f"https://toncenter.com/api/v2/getTransactions?address={MY_WALLET}&limit=15"
            res = requests.get(url).json()
            success = False
            if res.get("ok") and "result" in res:
                for tx in res["result"]:
                    if tx.get("in_msg", {}).get("message") == memo: success = True; break
            if success:
                c.execute("INSERT INTO payments (memo) VALUES (?)", (memo,))
                c.execute("UPDATE players SET crystals=crystals+? WHERE uid=?", (amount, uid))
                conn.commit(); bot.send_message(uid, f"🎉 Зачислено: <b>{amount} 💎</b>.", parse_mode="HTML")
            else: bot.send_message(uid, "⏳ Транзакция не найдена.")
        except Exception: bot.send_message(uid, "⚠️ Ошибка сети.")
    elif call.data.startswith("gacha_"):
        spins = int(call.data.split("_")[1])
        cost = 100 if spins == 1 else 1800
        c.execute("SELECT crystals FROM players WHERE uid=?", (uid,))
        if c.fetchone()[0] < cost: bot.answer_callback_query(call.id, "❌ Мало 💎"); conn.close(); return
        c.execute("UPDATE players SET crystals=crystals-? WHERE uid=?", (cost, uid))
        grades = ["Красный", "Золотой", "Фиолетовый", "Синий", "Зеленый", "Серый"]
        weights = [0.2, 1.8, 5.0, 11.0, 32.0, 50.0]
        result_text = f"🔮 <b>Призыв ({spins}x):</b>\n"
        for _ in range(spins):
            rg = random.choices(grades, weights=weights)[0]
            ri = random.choice(LOOT_POOL)
            it_atk, it_deff = generate_item_stats(ri["type"], rg)
            c.execute("INSERT INTO inventory (uid, item_name, item_type, grade, enhance, item_atk, item_deff) VALUES (?, ?, ?, ?, 0, ?, ?)", (uid, ri["name"], ri["type"], rg, it_atk, it_deff))
            result_text += f"{GRADES[rg]} {ri['name']} (⚔️+{it_atk} 🛡️+{it_deff})\n"
        conn.commit(); bot.send_message(call.message.chat.id, result_text, parse_mode="HTML")
    elif call.data.startswith("eq_"):
        item_id = int(call.data.split("_")[1])
        c.execute("SELECT item_type, item_name FROM inventory WHERE id=? AND uid=?", (item_id, uid))
        item = c.fetchone()
        if item: c.execute(f"UPDATE players SET eq_{item[0]}=? WHERE uid=?", (item_id, uid)); conn.commit()
        conn.close(); send_inventory(uid, call.message.message_id); return
    elif call.data.startswith("uneq_"):
        item_id = int(call.data.split("_")[1])
        c.execute("SELECT eq_weapon, eq_helm, eq_armor, eq_boots, eq_ring, eq_amulet, eq_shield FROM players WHERE uid=?", (uid,))
        eq_slots = c.fetchone(); slots_mapping = ["weapon", "helm", "armor", "boots", "ring", "amulet", "shield"]
        if eq_slots:
            for i, slot in enumerate(slots_mapping):
                if eq_slots[i] == item_id: c.execute(f"UPDATE players SET eq_{slot}=0 WHERE uid=?", (uid,)); conn.commit(); break
        conn.close(); send_inventory(uid, call.message.message_id); return
    conn.close()
@bot.message_handler(func=lambda m: m.text == "🎒 Инвентарь")
def inventory_menu(m): send_inventory(m.chat.id, None)
def send_inventory(uid, message_id=None):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT eq_weapon, eq_helm, eq_armor, eq_boots, eq_ring, eq_amulet, eq_shield FROM players WHERE uid=?", (uid,))
    eq_ids = c.fetchone() or (0,0,0,0,0,0,0)
    equipped = {}; slots_mapping = ["weapon", "helm", "armor", "boots", "ring", "amulet", "shield"]; equipped_set = set()
    for i, slot in enumerate(slots_mapping):
        if eq_ids[i] and eq_ids[i] != 0:
            c.execute("SELECT item_name, grade, item_atk, item_deff FROM inventory WHERE id=?", (eq_ids[i],))
            item = c.fetchone()
            if item: equipped[slot] = f"{GRADES[item[1]]} {item[0]} (⚔️{item[2]} 🛡️{item[3]})"; equipped_set.add(eq_ids[i])
    text = "🎒 <b>Инвентарь & Экипировка</b>\n─────────────────────\n" + "\n".join([f"{s.capitalize()}: {equipped.get(s, '❌')}" for s in slots_mapping])
    c.execute("SELECT id, item_name, item_type, grade, item_atk, item_deff FROM inventory WHERE uid=?", (uid,))
    bag_items = [it for it in c.fetchall() if it[0] not in equipped_set]
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, slot in enumerate(slots_mapping):
        if eq_ids[i] and eq_ids[i] != 0:
            c.execute("SELECT item_name, grade FROM inventory WHERE id=?", (eq_ids[i],))
            it = c.fetchone()
            if it: markup.add(types.InlineKeyboardButton(f"✅ {GRADES[it[1]]} {it[0]}", callback_data=f"uneq_{eq_ids[i]}"))
    for item in bag_items: markup.add(types.InlineKeyboardButton(f"{GRADES[item[3]]} {item[1]} (⚔️+{item[4]} 🛡️+{item[5]})", callback_data=f"eq_{item[0]}"))
    if message_id: bot.edit_message_text(text, uid, message_id, reply_markup=markup, parse_mode="HTML")
    else: bot.send_message(uid, text, reply_markup=markup, parse_mode="HTML")
    conn.close()
def calculate_loot(hours, afk_type, total_atk, total_deff):
    items_found, gold_found, exp_found, crystals_found = [], 0, 0, 0
    stat_mod = 1 + (total_atk + total_deff) / 100.0
    if afk_type == 'hunt':
        gold_found = int(hours * random.randint(150, 300) * stat_mod)
        exp_found = int(hours * random.randint(100, 200) * stat_mod)
        grade_chances = ["Красный", "Золотой", "Фиолетовый", "Синий", "Зеленый", "Серый"]
        grade_weights = [0.04, 0.36, 1.0, 2.2, 6.4, 90.0]
        for _ in range(hours * random.randint(1, 2)):
            if random.random() < 0.25:
                rg = random.choices(grade_chances, weights=grade_weights)[0]
                items_found.append((random.choice(LOOT_POOL)["name"], random.choice(LOOT_POOL)["type"], rg))
    elif afk_type == 'dg_exp': exp_found = int(hours * random.randint(1500, 3000) * stat_mod)
    elif afk_type == 'dg_gold': gold_found = int(hours * random.randint(2000, 4000) * stat_mod)
    elif afk_type == 'dg_crystals': crystals_found = hours * random.randint(1, 100)
    return gold_found, exp_found, crystals_found, items_found
@bot.message_handler(func=lambda m: m.text == "🤖 Охота (АФК)")
def hunt_menu(m):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT afk_start, afk_hours, afk_type FROM players WHERE uid=?", (m.chat.id,))
    p = c.fetchone(); now = int(time.time())
    if p and p[0] > 0:
        if now >= p[0]:
            total_atk, total_deff = get_total_stats(m.chat.id, c)
            gold, exp, crystals, items = calculate_loot(p[1], p[2], total_atk, total_deff)
            c.execute("UPDATE players SET gold=gold+?, exp=exp+?, crystals=crystals+?, afk_start=0, afk_hours=0 WHERE uid=?", (gold, exp, crystals, m.chat.id))
            loot_text = ""
            for name, itype, grade in items:
                ia, idf = generate_item_stats(itype, grade)
                c.execute("INSERT INTO inventory (uid, item_name, item_type, grade, enhance, item_atk, item_deff) VALUES (?, ?, ?, ?, 0, ?, ?)", (m.chat.id, name, itype, grade, ia, idf))
                loot_text += f"{GRADES[grade]} {name} (⚔️+{ia} 🛡️+{idf})\n"
            conn.commit()
            t_names = {'hunt': 'Охота', 'dg_exp': 'Данж Опыта', 'dg_gold': 'Данж Золота', 'dg_crystals': 'Данж Алмазов'}
            msg = f"🏁 <b>{t_names.get(p[2], 'Охота')} окончена!</b>\n"
            if gold > 0: msg += f"💰 Золото: +{gold}\n"
            if exp > 0: msg += f"✨ Опыт: +{exp}\n"
            if crystals > 0: msg += f"💎 Алмазы: +{crystals}\n"
            if loot_text: msg += f"\n🎒 Лут:\n{loot_text}"
            bot.send_message(m.chat.id, msg, parse_mode="HTML")
        else: bot.send_message(m.chat.id, f"⏳ Занят. Осталось: {int((p[0] - now) / 60)} мин.")
    else:
        text = "🗺️ <b>Выберите зону охоты:</b>\n\n🌍 <b>Обычная охота:</b> (Опыт, золото, шмотки)\n🏰 <b>Данжи (1 час в день):</b>\n• Данж опыта\n• Данж золота\n• Данж алмазов (1-100 💎)"
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("🌍 Обычная Охота", callback_data="starthunt_menu"))
        markup.add(types.InlineKeyboardButton("🏰 Подземелье Опыта (1 ч)", callback_data="startdg_exp"))
        markup.add(types.InlineKeyboardButton("🏰 Подземелье Золота (1 ч)", callback_data="startdg_gold"))
        markup.add(types.InlineKeyboardButton("🏰 Подземелье Алмазов (1 ч)", callback_data="startdg_crystals"))
        bot.send_message(m.chat.id, text, reply_markup=markup, parse_mode="HTML")
    conn.close()
@bot.callback_query_handler(func=lambda call: call.data == "starthunt_menu")
def start_hunt_menu_callback(call):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("1 ч", callback_data="starthunt_1"), types.InlineKeyboardButton("2 ч", callback_data="starthunt_2"))
    markup.add(types.InlineKeyboardButton("4 ч", callback_data="starthunt_4"), types.InlineKeyboardButton("8 ч", callback_data="starthunt_8"))
    bot.edit_message_text("🗺️ Выберите время:", call.from_user.id, call.message.message_id, reply_markup=markup)
@bot.callback_query_handler(func=lambda call: call.data.startswith("starthunt_") and call.data != "starthunt_menu")
def start_hunt_callback(call):
    uid = call.from_user.id
    hours = int(call.data.split("_")[1])
    thrun = int(time.time()) + (hours * 3600)
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE players SET afk_start=?, afk_hours=?, afk_type='hunt' WHERE uid=?", (thrun, hours, uid))
    conn.commit(); conn.close()
    bot.edit_message_text(f"🤖 Ушел на Охоту на {hours} ч.!", uid, call.message.message_id)
@bot.callback_query_handler(func=lambda call: call.data.startswith("startdg_"))
def start_dungeon_callback(call):
    uid = call.from_user.id
    dg_type = call.data.split("_")[1]
    now = int(time.time())
    conn = get_db(); c = conn.cursor()
    c.execute(f"SELECT dungeon_{dg_type}_limit FROM players WHERE uid=?", (uid,))
    limit_time = c.fetchone()[0]
    if now < limit_time:
        bot.answer_callback_query(call.id, f"❌ Доступно через {int((limit_time - now) / 60)} мин.", show_alert=True)
        conn.close(); return
    thrun = now + 3600
    next_access = now + 86400
    c.execute(f"UPDATE players SET afk_start=?, afk_hours=1, afk_type='dg_{dg_type}', dungeon_{dg_type}_limit=? WHERE uid=?", (thrun, next_access, uid))
    conn.commit(); conn.close()
    bot.edit_message_text(f"🏰 Вошел в подземелье на 1 час!", uid, call.message.message_id)
@bot.message_handler(func=lambda m: m.text == "🥊 Арена PvP")
def pvp_arena(m):
    conn = get_db(); c = conn.cursor()
    me_atk, me_deff = get_total_stats(m.chat.id, c)
    c.execute("SELECT uid, name FROM players WHERE uid != ? ORDER BY RANDOM() LIMIT 1", (m.chat.id,))
    opp = c.fetchone()
    if not opp: bot.send_message(m.chat.id, "📭 Арена пуста."); conn.close(); return
    opp_uid, opp_name = opp[0], opp[1]
    opp_atk, opp_deff = get_total_stats(opp_uid, c)
    my_damage = max(5, me_atk - opp_deff)
    opp_damage = max(5, opp_atk - me_deff)
    if my_damage >= opp_damage:
        c.execute("UPDATE players SET gold=gold+50 WHERE uid=?", (m.chat.id,))
        bot.send_message(m.chat.id, f"⚔️ PvP Победа над {opp_name}! Награда +50 💰")
    else:
        c.execute("UPDATE players SET gold=MAX(0, gold-30) WHERE uid=?", (m.chat.id,))
        bot.send_message(m.chat.id, f"💀 PvP Поражение от {opp_name}! Потеряно -30 💰")
    conn.commit(); conn.close()
while True:
    try: bot.polling(none_stop=True, interval=2, timeout=40)
    except Exception: time.sleep(5)
