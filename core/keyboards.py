from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

start = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📚 Продукты", callback_data="products")],
        [InlineKeyboardButton(text="🔍 Поиск", callback_data="search")],
        [InlineKeyboardButton(text="🛒 Корзина", callback_data="view_cart")],
        [InlineKeyboardButton(text="ℹ️ О нас", callback_data="about")],
    ]
)
products = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Телефоны", callback_data="category_phones")],
        [InlineKeyboardButton(text="🎧 Аксессуары", callback_data="category_accessories")]
])