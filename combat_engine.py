import random

def calculate_fight(p_stats, m_stats):
    """
    p_stats: {'strength': int, 'luck': int, 'class': str}
    m_stats: {'hp': int}
    """
    # Базовый урон от силы
    base_dmg = p_stats.get('strength', 10) + random.randint(1, 10)
    
    # Шанс крита от удачи (0.5% за очко удачи)
    crit_chance = p_stats.get('luck', 10) * 0.5
    is_crit = random.randint(0, 100) < crit_chance
    
    final_dmg = base_dmg * 1.5 if is_crit else base_dmg
    
    # Бонус класса (например, Ассасин наносит на 8% больше)
    if p_stats.get('class') == "Ассасин":
        final_dmg = int(final_dmg * 1.08)
        
    return int(final_dmg), is_crit
    
