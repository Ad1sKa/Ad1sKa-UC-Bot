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
        [InlineKeyboardButton(text="📦 60 UC — 80₽", callback_data="cart_add_60_80")],
        [InlineKeyboardButton(text="📦 325 UC — 405₽", callback_data="cart_add_325_405")],
        [InlineKeyboardButton(text="📦 660 UC — 800₽", callback_data="cart_add_660_800")],
        [InlineKeyboardButton(text="📦 1800 UC — 2000₽", callback_data="cart_add_1800_2000")],
        [InlineKeyboardButton(text="📦 3850 UC — 3925₽", callback_data="cart_add_3925")],
        [InlineKeyboardButton(text="📦 8100 UC — 8000₽", callback_data="cart_add_8100_8000")],
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
