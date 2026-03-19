from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Главное меню
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💎 Купить UC"), KeyboardButton(text="👤 Профиль")],
        [KeyboardButton(text="🕒 График"), KeyboardButton(text="🎟 Промокоды и Скидки")],
        [KeyboardButton(text="⭐ Отзывы"), KeyboardButton(text="🎁 Розыгрыши")],
        [KeyboardButton(text="🎧 Поддержка")], [KeyboardButton(text="📜 Правила")]
    ],
    resize_keyboard=True
)

# Витрина корзины
buy_tokens = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📦 60 UC — 80₽", callback_data="cart_add_60_80")],
        [InlineKeyboardButton(text="📦 325 UC — 400₽", callback_data="cart_add_325_400")],
        [InlineKeyboardButton(text="📦 660 UC — 750₽", callback_data="cart_add_660_750")],
        [InlineKeyboardButton(text="📦 1800 UC — 1920₽", callback_data="cart_add_1800_1920")],
        [InlineKeyboardButton(text="📦 3850 UC — 3800₽", callback_data="cart_add_3850_3800")],
        [InlineKeyboardButton(text="📦 8100 UC — 7400₽", callback_data="cart_add_8100_7400")],
        [InlineKeyboardButton(text="📦 16200 UC — 15200₽", callback_data="cart_add_16200_15200")],
        [InlineKeyboardButton(text="📦 24300 UC — 22700₽", callback_data="cart_add_24300_22700")],
        [InlineKeyboardButton(text="📦 32400 UC — 30000₽", callback_data="cart_add_32400_30000")],
        [InlineKeyboardButton(text="📦 40500 UC — 38000₽", callback_data="cart_add_40500_38000")],
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
