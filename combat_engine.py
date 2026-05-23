import random

def calculate_fight(p_stats):
    base_dmg = p_stats.get('strength', 10) + random.randint(1, 10)
    crit_chance = p_stats.get('luck', 10) * 0.5
    is_crit = random.randint(0, 100) < crit_chance
    
    final_dmg = base_dmg * 1.5 if is_crit else base_dmg
    
    if p_stats.get('class') == "Ассасин":
        final_dmg = int(final_dmg * 1.08)
        
    return int(final_dmg), is_crit
    
