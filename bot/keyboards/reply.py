from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_gender_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура выбора пола"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👨 Мужской")],
            [KeyboardButton(text="👩 Женский")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Мой профиль")],
            [KeyboardButton(text="ℹ️ Помощь")]
        ],
        resize_keyboard=True
    )
