import re
from typing import Optional, Tuple


def parse_workout_caption(caption: str) -> dict:
    """Парсит подпись вида #dayX #kmX #tX"""
    result = {
        "day": None,
        "km": None,
        "min": None,
        "error": None
    }
    
    # Ищем #dayX
    day_match = re.search(r'#day(\d+)', caption, re.IGNORECASE)
    if day_match:
        result["day"] = int(day_match.group(1))
    else:
        result["error"] = "❌ Не найден тег #dayX"
        return result
    
    # Ищем #kmX (может быть дробным)
    km_match = re.search(r'#km(\d+(?:[.,]\d+)?)', caption, re.IGNORECASE)
    if km_match:
        km_str = km_match.group(1).replace(',', '.')
        result["km"] = float(km_str)
    else:
        result["error"] = "❌ Не найден тег #kmX"
        return result
    
    # Ищем #tX (минуты)
    min_match = re.search(r'#t(\d+)', caption, re.IGNORECASE)
    if min_match:
        result["min"] = int(min_match.group(1))
    else:
        result["error"] = "❌ Не найден тег #tX"
        return result
    
    return result


def validate_workout(km: float, min_: int) -> Optional[str]:
    """Валидация данных тренировки"""
    if km < 5:
        return "❌ Минимальная дистанция — 5 км"
    
    if km > 100:
        return "❌ Максимальная дистанция — 100 км"
    
    if min_ < 30:
        return "❌ Минимальное время — 30 минут"
    
    if min_ > 600:
        return "❌ Максимальное время — 600 минут (10 часов)"
    
    # Проверка на реалистичный темп (от 2:30 до 12:00 мин/км)
    pace = min_ / km
    if pace < 2.5:
        return "❌ Слишком быстрый темп (меньше 2:30 мин/км)"
    
    if pace > 12:
        return "❌ Слишком медленный темп (больше 12:00 мин/км)"
    
    return None


def validate_full_name(full_name: str) -> Optional[str]:
    """Валидация имени"""
    full_name = full_name.strip()
    
    if len(full_name) < 3:
        return "❌ Слишком короткое имя"
    
    if len(full_name) > 100:
        return "❌ Слишком длинное имя"
    
    parts = full_name.split()
    if len(parts) < 2:
        return "❌ Введи Имя и Фамилию через пробел"
    
    # Проверка на буквы и дефисы
    for part in parts:
        if not re.match(r'^[а-яА-ЯёЁa-zA-Z\-]+$', part):
            return "❌ Имя должно содержать только буквы и дефис"
    
    return None
