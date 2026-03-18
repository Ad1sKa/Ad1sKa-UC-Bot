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

# Витрина UC
buy_tokens = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📦 60 UC — 80₽", callback_data="buy_60_80")],
        [InlineKeyboardButton(text="📦 325 UC — 400₽", callback_data="buy_325_400")],
        [InlineKeyboardButton(text="📦 660 UC — 750₽", callback_data="buy_660_750")],
        [InlineKeyboardButton(text="📦 1800 UC — 1920₽", callback_data="buy_1800_1920")],
        [InlineKeyboardButton(text="📦 3850 UC — 3800₽", callback_data="buy_3850_3800")],
        [InlineKeyboardButton(text="📦 8100 UC — 7400₽", callback_data="buy_8100_7400")]
    ]
)

# Динамическая кнопка оплаты
def payment_kb(url, invoice_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить (CryptoBot)", url=url)],
            [InlineKeyboardButton(text="✅ Проверить оплату", callback_data=f"check_{invoice_id}")]
        ]
    )

social_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Ввести промокод", callback_data="act_promo")],
        [InlineKeyboardButton(text="🔗 Перейти в канал", url="https://t.me")]
    ]
)
