from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_rating_keyboard(workout_id: str) -> InlineKeyboardMarkup:
    """Клавиатура для оценки тренера"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="⭐️ Оценить тренера",
                callback_data=f"rate_start:{workout_id}"
            )]
        ]
    )


def get_rating_stars(category: str, workout_id: str, current: int = 0) -> InlineKeyboardMarkup:
    """Клавиатура со звездами 1-5"""
    stars = []
    for i in range(1, 6):
        star = "★" if i <= current else "☆"
        stars.append(InlineKeyboardButton(
            text=star,
            callback_data=f"rate_{category}:{workout_id}:{i}"
        ))
    
    return InlineKeyboardMarkup(
        inline_keyboard=[stars] + [
            [InlineKeyboardButton(
                text="✅ Подтвердить" if current > 0 else "⏳ Выбери оценку",
                callback_data=f"rate_confirm:{workout_id}" if current > 0 else "rate_none"
            )],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="rate_cancel")]
        ]
    )


def get_coaches_keyboard(coaches: list, sunday_date: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора тренера (для админа)"""
    buttons = []
    for coach in coaches:
        buttons.append([InlineKeyboardButton(
            text=coach["full_name"],
            callback_data=f"set_coach:{sunday_date}:{coach['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
