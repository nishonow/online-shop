import asyncio
from datetime import datetime
import pytz
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message, \
    ReplyKeyboardMarkup, KeyboardButton
from config import ADMINS
from loader import dp, bot
from core.db import add_product, get_user_ids, count_users, \
    count_new_users_last_24_hours, get_all_users, get_smartphones, get_accessories, \
    delete_product  # Added delete_product


# ============================
# Admin Product States
# ============================
class AdminProductState(StatesGroup):
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_price = State()
    waiting_for_category = State()
    waiting_for_image = State()
    waiting_for_confirmation = State()


class AdminRemoveProductState(StatesGroup):  # New states for removal
    waiting_for_category = State()
    waiting_for_product_selection = State()


# ============================
# Inline Keyboards
# ============================
confirm_keyboard = InlineKeyboardMarkup(row_width=2)
confirm_keyboard.add(
    InlineKeyboardButton("✅ Подтвердить", callback_data="admin_confirm_product"),
    InlineKeyboardButton("❌ Отмена", callback_data="admin_cancel_product")
)

category_keyboard = InlineKeyboardMarkup(row_width=2)
category_keyboard.add(
    InlineKeyboardButton("📱 Smartphone", callback_data="cat_smartphone"),
    InlineKeyboardButton("🎧 Accessories", callback_data="cat_accessories")
)
category_keyboard.add(
    InlineKeyboardButton("❌ Отмена", callback_data="admin_cancel")
)

cancel_keyboard = InlineKeyboardMarkup()
cancel_keyboard.add(InlineKeyboardButton("❌ Отмена", callback_data="admin_cancel"))

menu = ReplyKeyboardMarkup(resize_keyboard=True)
menu.add(KeyboardButton(text='👥 Пользователи'))
menu.add(KeyboardButton(text='📢 Отправить сообщение'), KeyboardButton(text='🆔 Отправить по ID'))
menu.add(KeyboardButton(text='⭐ Добавить продукт'), KeyboardButton(text='🗑 Удалить продукт'))  # New button

cancel = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data='no')]
    ]
)

ratings_button = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="👀 Показать оценки", callback_data="see_ratings:0")]
    ]
)

users_button = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="👀 Показать пользователи", callback_data="see_users:0")]
    ]
)

confirm_broadcast = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="confirm_broadcast"),
         InlineKeyboardButton(text="❌ Нет", callback_data="cancel_broadcast")]
    ]
)

USERS_PER_PAGE = 20


# ============================
# Admin Menu Handlers
# ============================
@dp.message_handler(user_id=ADMINS, text='/admin')
async def welcome_admin(message: Message):
    await message.answer("👋 Привет, администратор! Чем могу помочь?", reply_markup=menu)


@dp.callback_query_handler(text="admin_cancel", state='*')
async def process_admin_cancel(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await call.message.delete()
    await call.message.answer("Операция отменена.")
    await call.answer()


# ============================
# Admin Product Adding Handlers
# ============================
@dp.message_handler(text="⭐ Добавить продукт")
async def admin_add_product(message: Message):
    await message.answer("Введите название продукта:", reply_markup=cancel_keyboard)
    await AdminProductState.waiting_for_name.set()


@dp.message_handler(state=AdminProductState.waiting_for_name, content_types=types.ContentTypes.TEXT)
async def process_product_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите описание продукта:", reply_markup=cancel_keyboard)
    await AdminProductState.waiting_for_description.set()


@dp.message_handler(state=AdminProductState.waiting_for_description, content_types=types.ContentTypes.TEXT)
async def process_product_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("Введите цену продукта:", reply_markup=cancel_keyboard)
    await AdminProductState.waiting_for_price.set()


@dp.message_handler(state=AdminProductState.waiting_for_price, content_types=types.ContentTypes.TEXT)
async def process_product_price(message: types.Message, state: FSMContext):
    price = message.text
    await state.update_data(price=price)
    await message.answer("Выберите категорию продукта:", reply_markup=category_keyboard)
    await AdminProductState.waiting_for_category.set()


@dp.callback_query_handler(lambda c: c.data in ["cat_smartphone", "cat_accessories"],
                           state=AdminProductState.waiting_for_category)
async def process_product_category(call: types.CallbackQuery, state: FSMContext):
    category = "Smartphones" if call.data == "cat_smartphone" else "Accessories"
    await state.update_data(category=category)
    await call.message.edit_text("Отправьте фотографию продукта:", reply_markup=cancel_keyboard)
    await AdminProductState.waiting_for_image.set()
    await call.answer()


@dp.message_handler(state=AdminProductState.waiting_for_image, content_types=types.ContentTypes.PHOTO)
async def process_product_image(message: types.Message, state: FSMContext):
    photo = message.photo[-1]  # Take the last photo (highest resolution)
    file_id = photo.file_id

    await state.update_data(image_file_id=file_id)
    data = await state.get_data()

    text = (
        f"*Предварительный просмотр продукта:*\n\n"
        f"*Название:* {data['name']}\n"
        f"*Описание:* {data['description']}\n"
        f"*Цена:* {data['price']}\n"
        f"*Категория:* {data['category']}\n"
    )
    await message.answer_photo(
        photo=file_id,
        caption=text,
        parse_mode="Markdown",
        reply_markup=confirm_keyboard
    )
    await AdminProductState.waiting_for_confirmation.set()


@dp.message_handler(state=AdminProductState.waiting_for_image, content_types=types.ContentTypes.TEXT)
async def process_invalid_image(message: types.Message, state: FSMContext):
    await message.answer("Пожалуйста, отправьте фотографию продукта (не текст или ссылку):",
                         reply_markup=cancel_keyboard)


@dp.callback_query_handler(lambda c: c.data in ["admin_confirm_product", "admin_cancel_product"],
                           state=AdminProductState.waiting_for_confirmation)
async def process_confirmation(call: types.CallbackQuery, state: FSMContext):
    if call.data == "admin_confirm_product":
        data = await state.get_data()
        await add_product(
            data['name'],
            data['description'],
            data['price'],
            data['category'],
            data['image_file_id']
        )
        await call.message.edit_caption(caption="✅ Продукт успешно добавлен!")
    else:
        await call.message.edit_caption(caption="❌ Добавление продукта отменено.")
    await state.finish()
    await call.answer()


# ============================
# Admin Product Removal Handlers
# ============================
@dp.message_handler(text="🗑 Удалить продукт")
async def admin_remove_product(message: Message):
    await message.answer("Выберите категорию продукта для удаления:", reply_markup=category_keyboard)
    await AdminRemoveProductState.waiting_for_category.set()


@dp.callback_query_handler(lambda c: c.data in ["cat_smartphone", "cat_accessories"],
                           state=AdminRemoveProductState.waiting_for_category)
async def process_remove_category(call: CallbackQuery, state: FSMContext):
    category = "Smartphones" if call.data == "cat_smartphone" else "Accessories"
    await state.update_data(category=category)

    # Fetch products based on category
    products = await get_smartphones() if category == "Smartphones" else await get_accessories()

    if not products:
        await call.message.edit_text("В этой категории нет продуктов.")
        await state.finish()
        await call.answer()
        return

    # Build product list with numbers
    product_list = []
    for idx, product in enumerate(products, 1):
        product_list.append(f"{idx}. {product[1]} - {product[2]} - {product[3]} сом")

    # Create inline buttons for each product
    keyboard = InlineKeyboardMarkup(row_width=3)
    for idx, product in enumerate(products, 1):
        keyboard.insert(InlineKeyboardButton(str(idx), callback_data=f"remove_product_{product[0]}"))
    keyboard.add(InlineKeyboardButton("❌ Отмена", callback_data="admin_cancel"))

    # Send message with product list
    await call.message.edit_text(
        f"Продукты в категории {category}:\n\n" + "\n".join(product_list) + "\n\nВыберите номер продукта для удаления:",
        reply_markup=keyboard
    )
    await AdminRemoveProductState.waiting_for_product_selection.set()
    await call.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("remove_product_"),
                           state=AdminRemoveProductState.waiting_for_product_selection)
async def process_product_removal(call: CallbackQuery, state: FSMContext):
    product_id = int(call.data.split("_")[-1])

    await delete_product(product_id)

    await call.message.edit_text("✅ Продукт успешно удален!")
    await state.finish()
    await call.answer()


# ============================
# User Statistics and Messaging Handlers
# ============================
@dp.callback_query_handler(lambda c: c.data.startswith("see_users"))
async def handle_see_users(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])
    all_users = await get_all_users(page=page, per_page=USERS_PER_PAGE)
    total_users = await count_users()
    timestamp = datetime.now(pytz.timezone('Asia/Bishkek')).strftime('%H:%M:%S %d.%m.%Y')

    if not all_users:
        await callback.message.edit_text("😕 Нет пользователей.")
        return

    total_pages = (total_users + USERS_PER_PAGE - 1) // USERS_PER_PAGE
    response_lines = [f"👥 Все пользователи (Страница {page + 1}/{total_pages}):", ""]
    for user_id, name in all_users:
        name1 = f"<a href='tg://user?id={user_id}'>{name}</a>"
        response_lines.append(f"👤 {name1} - {user_id}")
    response = "\n".join(response_lines)

    nav_buttons = [
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"see_users:{page - 1}") if page > 0 else None,
        InlineKeyboardButton(text="➡️ Вперед",
                             callback_data=f"see_users:{page + 1}") if page < total_pages - 1 else None
    ]
    nav_buttons = [btn for btn in nav_buttons if btn]
    back_button = [InlineKeyboardButton(text="🔙 Вернуться", callback_data="back_to_users")]

    pagination_keyboard = InlineKeyboardMarkup(inline_keyboard=[nav_buttons, back_button])
    await callback.message.edit_text(response, reply_markup=pagination_keyboard, parse_mode="HTML")


@dp.callback_query_handler(text="back_to_users")
async def handle_back_to_users(callback: CallbackQuery):
    total_users = await count_users()
    last_24h_users = await count_new_users_last_24_hours()
    timestamp = datetime.now(pytz.timezone('Asia/Bishkek')).strftime('%H:%M:%S %d.%m.%Y')
    await callback.message.edit_text(f"📊 Статистика пользователей:\n"
                                     f"👥 Всего: {total_users}\n"
                                     f"🆕 Новых за 24 часа: {last_24h_users}\n"
                                     f"⏰ Обновлено: {timestamp}",
                                     reply_markup=users_button)


@dp.message_handler(user_id=ADMINS, text='👥 Пользователи')
async def get_users_count(message: types.Message):
    total_users = await count_users()
    last_24h_users = await count_new_users_last_24_hours()
    timestamp = datetime.now(pytz.timezone('Asia/Bishkek')).strftime('%H:%M:%S %d.%m.%Y')
    await message.answer(f"📊 Статистика пользователей:\n"
                         f"👥 Всего: {total_users}\n"
                         f"🆕 Новых за 24 часа: {last_24h_users}\n"
                         f"⏰ Обновлено: {timestamp}",
                         reply_markup=users_button)


@dp.message_handler(user_id=ADMINS, text="📢 Отправить сообщение")
async def msg_all(message: types.Message, state: FSMContext):
    message_send = await message.answer(
        "✍️ Введите сообщение для рассылки всем пользователям.\n\nНажмите «❌ Отмена», чтобы отменить.",
        reply_markup=cancel)
    await state.set_state('msg_all')
    await state.update_data(prompt_msg_id=message_send.message_id)


@dp.callback_query_handler(text='no', state=['msg_all', 'get_user_id', 'msg_by_id'])
async def no_msg_all(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("🚫 Рассылка отменена.")
    await state.finish()


@dp.message_handler(state='msg_all', content_types=types.ContentTypes.ANY)
async def msg_to_all(message: types.Message, state: FSMContext):
    state_data = await state.get_data()
    prompt_msg_id = state_data['prompt_msg_id']
    await bot.edit_message_reply_markup(chat_id=message.from_user.id, message_id=prompt_msg_id, reply_markup=None)
    await state.update_data(msg_id=message.message_id, from_chat=message.chat.id)

    await bot.copy_message(
        chat_id=message.chat.id,
        from_chat_id=message.chat.id,
        message_id=message.message_id
    )
    await message.answer("👀 Это предварительный просмотр.\nОтправить всем пользователям?",
                         reply_markup=confirm_broadcast)


@dp.callback_query_handler(text="confirm_broadcast", state='msg_all')
async def confirm_broadcast_handler(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    data = await state.get_data()
    msg_id = data['msg_id']
    from_chat = data['from_chat']

    total_users_id = await get_user_ids()
    total = len(total_users_id)
    success = 0
    error = 0

    progress_msg = await callback.message.answer(f"📤 Отправка сообщения...\n📊 Прогресс: 0/{total}")
    await state.finish()
    for i, user_id in enumerate(total_users_id, 1):
        try:
            await bot.copy_message(chat_id=user_id, from_chat_id=from_chat, message_id=msg_id)
            success += 1
        except Exception:
            error += 1

        if i % 10 == 0 or i == total:
            await bot.edit_message_text(
                f"📤 Отправка сообщения...\n📊 Прогресс: {success + error}/{total}",
                chat_id=callback.message.chat.id,
                message_id=progress_msg.message_id
            )
        await asyncio.sleep(0.04)

    await callback.message.answer(
        f"✅ Рассылка завершена!\n\n📬 Отправлено: {success}\n❌ Не отправлено: {error}")


@dp.callback_query_handler(text="cancel_broadcast", state='msg_all')
async def cancel_broadcast_handler(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("🚫 Рассылка отменена.")
    await state.finish()


@dp.message_handler(user_id=ADMINS, text="🆔 Отправить по ID")
async def get_user_id(message: types.Message, state: FSMContext):
    await message.answer("✍️ Введите ID пользователя.\n\nНажмите «❌ Отмена», чтобы отменить.", reply_markup=cancel)
    await state.set_state('get_user_id')


@dp.message_handler(state='get_user_id')
async def get_message_for_user(message: types.Message, state: FSMContext):
    try:
        user_id = int(message.text)
        await state.update_data(user_id=user_id)
        await message.answer("✍️ Введите сообщение для отправки пользователю.\n\nНажмите «❌ Отмена», чтобы отменить.",
                             reply_markup=cancel)
        await state.set_state('msg_by_id')
    except ValueError:
        await message.answer("❌ Неверный формат ID. Пожалуйста, введите числовой ID.")


@dp.message_handler(state='msg_by_id', content_types=types.ContentTypes.ANY)
async def preview_message_for_user(message: types.Message, state: FSMContext):
    state_data = await state.get_data()
    user_id = state_data['user_id']
    await state.update_data(msg_id=message.message_id, from_chat=message.chat.id)
    await bot.copy_message(chat_id=message.chat.id, from_chat_id=message.chat.id, message_id=message.message_id)
    await message.answer("👀 Это предварительный просмотр.\nОтправить пользователю?", reply_markup=confirm_broadcast)


@dp.callback_query_handler(text="confirm_broadcast", state='msg_by_id')
async def confirm_send_to_user(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    data = await state.get_data()
    user_id = data['user_id']
    msg_id = data['msg_id']
    from_chat = data['from_chat']
    try:
        await bot.copy_message(chat_id=user_id, from_chat_id=from_chat, message_id=msg_id)
        await callback.message.answer("✅ Сообщение отправлено.")
    except Exception:
        await callback.message.answer("❌ Ошибка при отправке сообщения.")
    await state.finish()


@dp.callback_query_handler(text="cancel_broadcast", state='msg_by_id')
async def cancel_send_to_user(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("🚫 Отправка сообщения отменена.")
    await state.finish()
