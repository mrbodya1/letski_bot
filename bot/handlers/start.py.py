from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.states.registration import RegistrationState
from bot.utils.supabase import get_profile, create_profile
from bot.keyboards.reply import get_gender_keyboard, get_main_menu_keyboard

router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username
    
    # Проверяем, зарегистрирован ли пользователь
    profile = await get_profile(user_id)
    
    if profile:
        # Уже зарегистрирован
        await message.answer(
            f"👋 С возвращением, {profile['full_name']}!\n\n"
            f"📊 Твоя статистика:\n"
            f"• Серия воскресений: {profile['sunday_streak']}\n"
            f"• Всего тренировок: {profile['total_sundays']}\n"
            f"• Общий км: {profile['total_km']} км\n\n"
            f"Жду твой отчет в это воскресенье! 🏃‍♂️",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        # Новый пользователь - начинаем регистрацию
        await message.answer(
            "👋 Привет! Добро пожаловать в Воскресный Клуб!\n\n"
            "Давай познакомимся. Как тебя зовут?\n"
            "Напиши Имя и Фамилию:"
        )
        await state.set_state(RegistrationState.waiting_for_full_name)


@router.message(RegistrationState.waiting_for_full_name)
async def process_full_name(message: types.Message, state: FSMContext):
    """Обработка ввода имени"""
    full_name = message.text.strip()
    
    # Простая валидация
    if len(full_name.split()) < 2:
        await message.answer("❌ Пожалуйста, введи Имя и Фамилию через пробел:")
        return
    
    await state.update_data(full_name=full_name)
    
    await message.answer(
        "Отлично! Теперь укажи свой пол:",
        reply_markup=get_gender_keyboard()
    )
    await state.set_state(RegistrationState.waiting_for_gender)


@router.message(RegistrationState.waiting_for_gender)
async def process_gender(message: types.Message, state: FSMContext):
    """Обработка выбора пола"""
    gender_text = message.text.strip()
    
    if gender_text not in ["👨 Мужской", "👩 Женский"]:
        await message.answer("❌ Пожалуйста, выбери пол из предложенных вариантов:")
        return
    
    gender = "М" if "Мужской" in gender_text else "Ж"
    data = await state.get_data()
    
    # Создаем профиль в БД
    profile = await create_profile(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=data['full_name'],
        gender=gender
    )
    
    if profile:
        await message.answer(
            f"✅ Регистрация завершена!\n\n"
            f"👤 {data['full_name']}\n"
            f"⚥ {gender_text}\n\n"
            f"Теперь ты участник Воскресного Клуба! 🎉\n"
            f"Жду твой первый отчет в воскресенье.",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await message.answer("❌ Произошла ошибка при регистрации. Попробуй позже или напиши администратору.")
    
    await state.clear()