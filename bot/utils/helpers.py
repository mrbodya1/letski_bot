from datetime import datetime, date, timedelta


def is_sunday(check_date: date = None) -> bool:
    """Проверяет, воскресенье ли сегодня или указанная дата"""
    if check_date is None:
        check_date = date.today()
    return check_date.weekday() == 6


def get_current_sunday() -> date:
    """Возвращает дату ближайшего воскресенья (сегодня если воскресенье, иначе прошлое)"""
    today = date.today()
    if today.weekday() == 6:
        return today
    return today - timedelta(days=today.weekday() + 1)


def get_next_sunday() -> date:
    """Возвращает дату следующего воскресенья"""
    today = date.today()
    days_until_sunday = (6 - today.weekday()) % 7
    if days_until_sunday == 0:
        days_until_sunday = 7
    return today + timedelta(days=days_until_sunday)


def calculate_pace(distance_km: float, duration_min: int) -> float:
    """Вычисляет темп (мин/км)"""
    if distance_km == 0:
        return 0
    return round(duration_min / distance_km, 2)


def format_pace(pace: float) -> str:
    """Форматирует темп в читаемый вид (MM:SS)"""
    minutes = int(pace)
    seconds = int((pace - minutes) * 60)
    return f"{minutes}:{seconds:02d}"


def get_streak_emoji(streak: int) -> str:
    """Возвращает эмодзи для серии"""
    if streak >= 12:
        return "🔥🔥🔥"
    elif streak >= 8:
        return "🔥🔥"
    elif streak >= 4:
        return "🔥"
    return "⚡️"
