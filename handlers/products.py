from aiogram import types
from aiogram.types import (
    InputMediaPhoto,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

from config import ADMINS
from core.keyboards import start
from loader import dp, bot
from core.db import get_smartphones, get_accessories, add_to_cart, get_cart, clear_cart

# ---------------- State Definitions ----------------
class PurchaseState(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()

class QuantityState(StatesGroup):
    waiting_for_quantity = State()

class SearchState(StatesGroup):
    waiting_for_query = State()  # Only used for initial query input

# ---------------- Main Menu Handler ----------------
@dp.callback_query_handler(lambda c: c.data == "menu")
async def show_main_menu(call: CallbackQuery):
    await call.message.edit_reply_markup()
    await call.message.answer(
        "📢 Вы вернулись в главное меню!",
        reply_markup=start
    )
    await call.answer()

# ---------------- Stop Handler ----------------
@dp.message_handler(commands=["stop"], state="*")
async def stop_handler(message: types.Message, state: FSMContext):
    await state.finish()  # Reset any active state
    await message.answer("Действие остановлено.", reply_markup=start)

# ---------------- About Handler ----------------
@dp.callback_query_handler(lambda c: c.data == "about")
async def show_about(call: CallbackQuery):
    await call.message.edit_reply_markup()
    await call.message.answer(
        "ℹ️ О нас:\n\n"
        "Мы - ваш надежный магазин электроники! 📱🎧\n"
        "Предлагаем лучшие смартфоны и аксессуары по доступным ценам.\n\n"
        "Instagram: <a href='https://www.instagram.com/ideal_mobile_kg/'>IDEAL_MOBILE_KG</a>\n",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("🏠 Главное меню", callback_data="menu")
        ),
        parse_mode=types.ParseMode.HTML
    )
    await call.answer()

# ---------------- Products Category Handler ----------------
@dp.callback_query_handler(lambda c: c.data == "products")
async def show_products_category(callback_query: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Телефоны", callback_data="category_phones")],
        [InlineKeyboardButton(text="🎧 Аксессуары", callback_data="category_accessories")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu")]
    ])
    await callback_query.message.edit_reply_markup()
    await callback_query.message.answer("Выберите категорию товаров:", reply_markup=keyboard)
    await callback_query.answer()

# ---------------- Search Handlers ----------------
@dp.callback_query_handler(lambda c: c.data == "search")
async def initiate_search(call: CallbackQuery, state: FSMContext):
    await call.message.edit_reply_markup()
    await call.message.answer("🔍 Введите название товара для поиска:\nВведите /stop чтобы остановить действие")
    await SearchState.waiting_for_query.set()
    await call.answer()

@dp.message_handler(state=SearchState.waiting_for_query, content_types=types.ContentTypes.TEXT)
async def process_search_query(message: types.Message, state: FSMContext):
    query = message.text.lower()
    all_products = await get_smartphones() + await get_accessories()
    search_results = [p for p in all_products if query in p[1].lower()]

    if not search_results:
        await message.answer(
            "❌ Товары не найдены",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("🏠 Главное меню", callback_data="menu")
            )
        )
        await state.finish()
        return

    await state.update_data(search_results=search_results)  # Store results in state temporarily
    await show_search_results(message, query, 0)  # Pass query and initial index
    await state.finish()  # Finish state after showing first result

async def show_search_results(message: types.Message, query: str, current_index: int):
    all_products = await get_smartphones() + await get_accessories()
    search_results = [p for p in all_products if query.lower() in p[1].lower()]

    if not 0 <= current_index < len(search_results):
        await message.answer("Результат не найден.", reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("🏠 Главное меню", callback_data="menu")
        ))
        return

    product = search_results[current_index]
    keyboard = InlineKeyboardMarkup(row_width=2)
    if current_index > 0:
        keyboard.insert(InlineKeyboardButton("⬅️", callback_data=f"search_{query}_{current_index - 1}"))
    if current_index < len(search_results) - 1:
        keyboard.insert(InlineKeyboardButton("➡️", callback_data=f"search_{query}_{current_index + 1}"))
    keyboard.add(
        InlineKeyboardButton("➕ В корзину", callback_data=f"add_to_cart_{product[0]}"),
        InlineKeyboardButton("🏠 Главное меню", callback_data="menu")  # Removed "📚 Меню" button
    )

    await message.answer_photo(
        photo=product[5],
        caption=f"🔍 Результат поиска:\n📱 {product[1]}\n📝 {product[2]}\n💵 {product[3]} сом",
        reply_markup=keyboard
    )

@dp.callback_query_handler(lambda c: c.data.startswith("search_"))
async def process_search_action(call: CallbackQuery):
    await call.message.delete()
    try:
        _, query, index = call.data.split("_")
        current_index = int(index)
        await show_search_results(call.message, query, current_index)
    except (ValueError, IndexError):
        await call.answer("Ошибка при обработке запроса.", show_alert=True)
    await call.answer()

# ---------------- Smartphone Buying Handlers ----------------
@dp.callback_query_handler(lambda c: c.data == "category_phones")
async def show_phones(call: CallbackQuery):
    await show_phone_products(call, 0)

async def show_phone_products(call: CallbackQuery, current_index: int):
    products = await get_smartphones()
    if not 0 <= current_index < len(products):
        await call.answer("Продукт не найден.", show_alert=True)
        return

    product = products[current_index]
    keyboard = InlineKeyboardMarkup(row_width=2)
    if current_index > 0:
        keyboard.insert(InlineKeyboardButton("⬅️", callback_data=f"phone_prev_{current_index}"))
    if current_index < len(products) - 1:
        keyboard.insert(InlineKeyboardButton("➡️", callback_data=f"phone_next_{current_index}"))
    keyboard.add(
        InlineKeyboardButton("➕ В корзину", callback_data=f"add_to_cart_{product[0]}"),
        InlineKeyboardButton("🏠 Главное меню", callback_data="menu")  # Removed "📚 Меню" button
    )

    await call.message.edit_media(
        media=InputMediaPhoto(
            media=product[5],
            caption=f"📱 {product[1]}\n📝 {product[2]}\n💵 {product[3]} сом"
        ),
        reply_markup=keyboard
    )
    await call.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("phone_next_"))
async def phone_next(call: CallbackQuery):
    current_index = int(call.data.split("_")[-1]) + 1
    await show_phone_products(call, current_index)

@dp.callback_query_handler(lambda c: c.data.startswith("phone_prev_"))
async def phone_prev(call: CallbackQuery):
    current_index = int(call.data.split("_")[-1]) - 1
    await show_phone_products(call, current_index)

# ---------------- Accessories Buying Handlers ----------------
@dp.callback_query_handler(lambda c: c.data == "category_accessories")
async def show_accessories(call: CallbackQuery):
    await show_accessories_products(call, 0)

async def show_accessories_products(call: CallbackQuery, current_index: int):
    products = await get_accessories()
    if not 0 <= current_index < len(products):
        await call.answer("Продукт не найден.", show_alert=True)
        return

    product = products[current_index]
    keyboard = InlineKeyboardMarkup(row_width=2)
    if current_index > 0:
        keyboard.insert(InlineKeyboardButton("⬅️", callback_data=f"accessory_prev_{current_index}"))
    if current_index < len(products) - 1:
        keyboard.insert(InlineKeyboardButton("➡️", callback_data=f"accessory_next_{current_index}"))
    keyboard.add(
        InlineKeyboardButton("➕ В корзину", callback_data=f"add_to_cart_{product[0]}"),
        InlineKeyboardButton("🏠 Главное меню", callback_data="menu")  # Removed "📚 Меню" button
    )

    await call.message.edit_media(
        media=InputMediaPhoto(
            media=product[5],
            caption=f"🎧 {product[1]}\n📝 {product[2]}\n💵 {product[3]} сом"
        ),
        reply_markup=keyboard
    )
    await call.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("accessory_next_"))
async def accessory_next(call: CallbackQuery):
    current_index = int(call.data.split("_")[-1]) + 1
    await show_accessories_products(call, current_index)

@dp.callback_query_handler(lambda c: c.data.startswith("accessory_prev_"))
async def accessory_prev(call: CallbackQuery):
    current_index = int(call.data.split("_")[-1]) - 1
    await show_accessories_products(call, current_index)

# ---------------- Cart Management Handlers ----------------
@dp.callback_query_handler(lambda c: c.data.startswith("add_to_cart_"))
async def add_to_cart_handler(call: CallbackQuery, state: FSMContext):
    product_id = int(call.data.split("_")[-1])
    user_id = call.from_user.id

    all_products = await get_smartphones() + await get_accessories()
    product = next((p for p in all_products if p[0] == product_id), None)
    if not product:
        await call.answer("Продукт не найден.", show_alert=True)
        return

    await state.update_data(product_id=product_id, product=product)
    await call.message.edit_reply_markup()
    await call.message.answer("Введите количество товара:\nВведите /stop чтобы остановить действие")
    await QuantityState.waiting_for_quantity.set()
    await call.answer()

@dp.message_handler(state=SearchState.waiting_for_query, content_types=types.ContentTypes.ANY)
async def invalid_search_input(message: types.Message):
    await message.answer("Пожалуйста, отправьте поисковый запрос в текстовом формате:\nВведите /stop чтобы остановить действие")

@dp.message_handler(state=QuantityState.waiting_for_quantity, content_types=types.ContentTypes.TEXT)
async def process_quantity(message: types.Message, state: FSMContext):
    try:
        quantity = int(message.text)
        if quantity <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите положительное число:\nВведите /stop чтобы остановить действие")
        return

    data = await state.get_data()
    product_id = data["product_id"]
    product = data["product"]
    user_id = message.from_user.id

    await add_to_cart(user_id, product_id, quantity)
    keyboard = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("🛒 Посмотреть корзину", callback_data="view_cart"),
        InlineKeyboardButton("🏠 Главное меню", callback_data="menu")
    )
    await message.answer(
        f"Добавлено в корзину: {product[1]} - {quantity} шт.",
        reply_markup=keyboard
    )
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == "view_cart")
async def view_cart(call: CallbackQuery):
    user_id = call.from_user.id
    cart_items = await get_cart(user_id)
    await call.message.delete()

    if not cart_items:
        await call.message.answer(
            "🛒 Ваша корзина пуста!",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("🏠 Главное меню", callback_data="menu")
            )
        )
        await call.answer()
        return

    text = "🛒 Ваша корзина:\n\n"
    for idx, item in enumerate(cart_items, 1):
        text += f"{idx}. {item[1]} - {item[3]} сом x {item[6]} шт.\n"

    keyboard = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("✅ Оформить заказ", callback_data="checkout"),
        InlineKeyboardButton("🗑 Очистить корзину", callback_data="clear_cart"),
        InlineKeyboardButton("🏠 Главное меню", callback_data="menu")
    )
    await call.message.answer(text, reply_markup=keyboard)
    await call.answer()

@dp.callback_query_handler(lambda c: c.data == "clear_cart")
async def clear_cart_handler(call: CallbackQuery):
    user_id = call.from_user.id
    await clear_cart(user_id)
    await call.message.delete()
    await call.message.answer(
        "🛒 Корзина очищена!",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("🏠 Главное меню", callback_data="menu")
        )
    )
    await call.answer()

# ---------------- Purchase Process Handlers ----------------
@dp.callback_query_handler(lambda c: c.data == "checkout")
async def checkout(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    cart_items = await get_cart(user_id)
    if not cart_items:
        await call.message.delete()
        await call.message.answer(
            "🛒 Корзина пуста!",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("🏠 Главное меню", callback_data="menu")
            )
        )
        await call.answer()
        return

    await state.update_data(cart_items=cart_items)
    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("❌ Отмена", callback_data="cancel_purchase")
    )
    await call.message.delete()
    new_message = await call.message.answer("Пожалуйста, укажите ваше имя:", reply_markup=keyboard)
    await PurchaseState.waiting_for_name.set()
    await state.update_data(msg1=new_message.message_id)
    await call.answer()

@dp.message_handler(state=PurchaseState.waiting_for_name, content_types=types.ContentTypes.TEXT)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    data = await state.get_data()
    msg1 = data["msg1"]
    await bot.edit_message_reply_markup(chat_id=message.chat.id, message_id=msg1, reply_markup=None)
    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("❌ Отмена", callback_data="cancel_purchase")
    )
    new_message = await message.answer("Пожалуйста, укажите ваш номер телефона:", reply_markup=keyboard)
    await PurchaseState.waiting_for_phone.set()
    await state.update_data(msg2=new_message.message_id)

@dp.message_handler(state=PurchaseState.waiting_for_phone, content_types=types.ContentTypes.TEXT)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.text
    if not phone.replace("+", "").replace(" ", "").isdigit():
        await message.answer("Номер телефона должен содержать только цифры. Попробуйте снова:")
        return

    await state.update_data(phone=phone)
    data = await state.get_data()
    cart_items = data["cart_items"]
    msg2 = data["msg2"]
    await bot.edit_message_reply_markup(chat_id=message.chat.id, message_id=msg2)

    order_message = "📩 *Новый заказ!*\n\n"
    for idx, item in enumerate(cart_items, 1):
        order_message += f"{idx}. *Товар:* {item[1]} - {item[3]} сом x {item[6]} шт.\n"
    order_message += (
        f"👤 *Имя:* {data['name']}\n"
        f"📞 *Телефон:* {phone}\n"
        f"🏷 *Username:* @{message.from_user.username or 'Не указан'}\n"
        f"🆔 *ID:* {message.from_user.id}"
    )

    for admin in ADMINS:
        try:
            await bot.send_message(admin, order_message, parse_mode=types.ParseMode.MARKDOWN)
        except:
            pass

    await clear_cart(message.from_user.id)
    await message.answer(
        "Спасибо за заказ! Мы свяжемся с вами в ближайшее время.",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("🏠 Главное меню", callback_data="menu")
        )
    )
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == "cancel_purchase", state='*')
async def cancel_purchase(call: CallbackQuery, state: FSMContext):
    await state.finish()
    await call.message.edit_reply_markup()
    await call.message.answer(
        "Операция отменена.",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("🏠 Главное меню", callback_data="menu")
        )
    )
    await call.answer()

# ---------------- Input Validation Handlers ----------------
@dp.message_handler(state=QuantityState.waiting_for_quantity, content_types=types.ContentTypes.ANY)
async def invalid_quantity_input(message: types.Message):
    await message.answer("Пожалуйста, отправьте количество в числовом формате:")

@dp.message_handler(state=PurchaseState.waiting_for_phone, content_types=types.ContentTypes.ANY)
async def invalid_phone_input(message: types.Message):
    await message.answer("Пожалуйста, отправьте номер телефона в текстовом формате:")