import random

# Зоны удара/блока
ZONES = ["Голова", "Грудь", "Пояс", "Ноги"]

def calculate_fight(p_stats, m_stats, p_zone, m_zone):
    """
    p_stats: {'atk': ..., 'dex': ..., 'luck': ..., 'class': ...}
    m_stats: {'atk': ..., 'dex': ..., 'hp': ...}
    p_zone, m_zone: выбранные зоны
    """
    log = []

    # 1. Расчет попадания (Ловкость игрока vs Ловкость монстра)
    hit_chance = 50 + (p_stats['dex'] - m_stats['dex']) * 2
    if random.randint(0, 100) > hit_chance:
        return "Промах!", 0

    # 2. Проверка блока (совпала зона удара и блока)
    if p_zone == m_zone:
        return "Блок!", 0

    # 3. Расчет урона
    damage = p_stats['atk'] + random.randint(1, 10)

    # 4. Критический удар (Зависит от Удачи)
    crit_chance = 5 + (p_stats['luck'] * 0.5)
    if random.randint(0, 100) < crit_chance:
        damage *= 1.5
        log.append("КРИТ!")

    # 5. Бонус класса
    if p_stats['class'] == "Ассасин":
        damage = int(damage * 1.08)
    elif p_stats['class'] == "Маг":
        damage = int(damage * 1.10)

    return f"{damage} урона ({' '.join(log)})", damage
