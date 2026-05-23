import random
import db_manager

def run_battle(uid, dungeon_level):
    conn = db_manager.get_db()
    c = conn.cursor()
    # Достаем статы
    c.execute("SELECT str, dex, luk, lvl FROM players WHERE uid=?", (uid,))
    stats = c.fetchone()
    if not stats: return "Ошибка: персонаж не найден."

    str_val, dex_val, luk_val, lvl_val = stats

    # Логика БК: сила + рандом + бонусы
    damage = str_val + random.randint(1, 15)
    monster_hp = 20 + (dungeon_level * 10)

    # Крит
    is_crit = random.randint(1, 100) < (luk_val * 2)
    if is_crit: damage *= 2
 
    # Итог боя
    if damage >= monster_hp:
        reward = 50 * dungeon_level
        exp = 10 * dungeon_level
        c.execute("UPDATE players SET gold = gold + ?, exp = exp + ? WHERE uid=?", (reward, exp, uid))
        conn.commit()
        result = f"⚔️ Победа! Урон: {damage} {'(КРИТ!)' if is_crit else ''}\n💰 +{reward} золота, 📈 +{exp} опыта."
    else:
        result = f"❌ Поражение. Монстр выжил (HP: {monster_hp}). Ты нанес {damage} урона."

    conn.close()
    return result
# Внутри run_battle, там где начисление награды:
if damage >= monster_hp:
    reward = 50 * dungeon_level
    exp = 10 * dungeon_level
    c.execute("UPDATE players SET gold = gold + ?, exp = exp + ? WHERE uid=?", (reward, exp, uid))
    conn.commit()
    
    # ПРОВЕРКА УРОВНЯ
    is_lvl_up = db_manager.check_level_up(uid)
    result = f"⚔️ Победа! +{reward} золота, +{exp} опыта."
    if is_lvl_up:
        result += "\n🎉 ПОЗДРАВЛЯЕМ! Ты получил новый УРОВЕНЬ!"
    # ... дальше возврат result

import db_manager
import random

def run_battle(uid, dungeon_level):
    # Теперь берем силу через новую функцию с учетом вещей
    total_str = db_manager.get_total_str(uid)
    
    # ... (логика боя та же, но используем total_str вместо простого str_val)
    damage = total_str + random.randint(1, 15)
    # ...

def run_pvp(attacker_uid, defender_uid):
    str_atk = db_manager.get_total_str(attacker_uid)
    str_def = db_manager.get_total_str(defender_uid)
    
    # Побеждает тот, у кого больше силы с небольшим рандомом
    if (str_atk + random.randint(0, 10)) > (str_def + random.randint(0, 10)):
        return True # Победа атакующего
    return False
    

