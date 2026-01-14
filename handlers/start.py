from aiogram import types
from aiogram.dispatcher import FSMContext
from core.db import add_user, user_exists
from core.keyboards import start
from loader import dp, bot


@dp.message_handler(text='/start', state='*')
async def start_command(message: types.Message, state: FSMContext):
    await state.finish()
    user_id = message.from_user.id
    name = message.from_user.full_name
    username = message.from_user.username

    if not await user_exists(user_id):
        await add_user(user_id, name, username)

    await message.answer("Добро пожаловать в бот! Нажмите кнопку ниже, чтобы увидеть наши доступные продукты.", reply_markup=start)

