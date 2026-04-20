from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_rating_keyboard(workout_id: str) -> InlineKeyboardMarkup:
    """Клавиатура для начала оценки тренера"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="⭐️ Оценить тренера",
                callback_data=f"rate_start:{workout_id}"
            )]
        ]
    )


def get_rating_stars(category: str, workout_id: str, current: int = 0, previous_category: str = None) -> InlineKeyboardMarkup:
    """Клавиатура со звездами 1-5 и кнопкой Назад"""
    stars = []
    for i in range(1, 6):
        star = "★" if i <= current else "☆"
        stars.append(InlineKeyboardButton(
            text=star,
            callback_data=f"rate_{category}:{workout_id}:{i}"
        ))
    
    keyboard = [stars]
    
    # Кнопка "Назад" если есть предыдущая категория
    if previous_category:
        back_data = f"rate_back:{workout_id}:{previous_category}"
        keyboard.append([InlineKeyboardButton(text="← Назад", callback_data=back_data)])
    else:
        keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="rate_cancel")])
    
    # Кнопка подтверждения (только если выбрана оценка)
    if current > 0:
        keyboard.append([InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"rate_confirm:{workout_id}")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


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
