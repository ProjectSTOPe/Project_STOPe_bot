import random
import time
import db_manager

# Словарь для хранения времени последнего боя: {uid: timestamp}
last_fight_time = {}

def can_fight(uid):
    current_time = time.time()
    last_time = last_fight_time.get(uid, 0)
    # Кулдаун 10 секунд
    if current_time - last_time < 10:
        return False
    last_fight_time[uid] = current_time
    return True

def run_battle(uid, dungeon_level):
    # Берем силу с учетом вещей через db_manager
    total_str = db_manager.get_total_str(uid)
    
    # Расчет урона
    damage = total_str + random.randint(1, 15)
    monster_hp = 20 + (dungeon_level * 10)
    
    # Крит (теперь учитываем Luck)
    # Нужно будет добавить получение удачи из БД, если нужно
    is_crit = random.randint(1, 100) < 20 # Базовый шанс 20%
    if is_crit: 
        damage *= 2

    # Итог боя
    if damage >= monster_hp:
        reward = 50 * dungeon_level
        exp = 10 * dungeon_level
        
        conn = db_manager.get_db()
        c = conn.cursor()
        c.execute("UPDATE players SET gold = gold + ?, exp = exp + ? WHERE uid=?", (reward, exp, uid))
        conn.commit()
        conn.close()
        
        # Проверка уровня
        is_lvl_up = db_manager.check_level_up(uid)
        
        result = f"⚔️ Победа! Урон: {damage} {'(КРИТ!)' if is_crit else ''}\n💰 +{reward} золота, 📈 +{exp} опыта."
        if is_lvl_up:
            result += "\n🎉 ПОЗДРАВЛЯЕМ! Ты получил новый УРОВЕНЬ!"
    else:
        result = f"❌ Поражение. Монстр выжил (HP: {monster_hp}). Ты нанес {damage} урона."
    
    return result

def run_pvp(attacker_uid, defender_uid):
    str_atk = db_manager.get_total_str(attacker_uid)
    str_def = db_manager.get_total_str(defender_uid)
    
    # Побеждает тот, у кого больше силы с небольшим рандомом
    if (str_atk + random.randint(0, 10)) > (str_def + random.randint(0, 10)):
        return True # Победа атакующего
    return False
    
