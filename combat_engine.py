import random

def calculate_fight(p_stats, m_stats, zone):
    # Базовая логика расчета урона
    base_dmg = p_stats['strength'] + random.randint(1, 10)
    
    # Можно добавить проверку зоны (БК-стайл: попал или нет)
    # Если ты хочешь развивать систему зон, дописывай здесь
    
    return base_dmg
    
