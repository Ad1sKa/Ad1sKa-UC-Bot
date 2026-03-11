from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Главное меню
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💎 Купить UC"), KeyboardButton(text="👤 Профиль")],
        [KeyboardButton(text="🕒 График"), KeyboardButton(text="🎟 Промокоды и Скидки")],
        [KeyboardButton(text="⭐ Отзывы"), KeyboardButton(text="🎁 Розыгрыши")],
        [KeyboardButton(text="🎧 Поддержка")]
    ],
    resize_keyboard=True
)

# Витрина корзины
buy_tokens = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📦 325 UC — 380₽", callback_data="cart_add_325_380")],
        [InlineKeyboardButton(text="📦 660 UC — 790₽", callback_data="cart_add_660_790")],
        [InlineKeyboardButton(text="📦 1800 UC — 1990₽", callback_data="cart_add_1800_1990")],
        [InlineKeyboardButton(text="📦 3850 UC — 3825₽", callback_data="cart_add_3850_3825")],
        [InlineKeyboardButton(text="📦 8100 UC — 7600₽", callback_data="cart_add_8100_7600")],
        [InlineKeyboardButton(text="📦 12610 UC — 11390₽", callback_data="cart_add_12610_11390")],
        [InlineKeyboardButton(text="🛒 Оформить заказ", callback_data="cart_checkout")],
        [InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="cart_clear")]
    ]
)

# Кнопки со ссылкой на твой канал
social_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Ввести промокод", callback_data="act_promo")],
        [InlineKeyboardButton(text="🔗 Перейти в канал", url="https://t.me/ad1skauc")]
    ]
)
