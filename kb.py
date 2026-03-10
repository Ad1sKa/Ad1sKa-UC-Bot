from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💎 Купить UC"), KeyboardButton(text="👤 Профиль")],
        [KeyboardButton(text="🕒 График"), KeyboardButton(text="📜 Инструкция")],
        [KeyboardButton(text="🎧 Поддержка"), KeyboardButton(text="⭐ Отзывы")],
        [KeyboardButton(text="🎁 Розыгрыши")]
    ],
    resize_keyboard=True
)

buy_tokens = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📦 325 UC — 380₽", callback_data="buy_325")],
        [InlineKeyboardButton(text="📦 660 UC — 790₽", callback_data="buy_660")],
        [InlineKeyboardButton(text="📦 1800 UC — 1990₽", callback_data="buy_1800")],
        [InlineKeyboardButton(text="📦 3850 UC — 3825₽", callback_data="buy_3850")],
        [InlineKeyboardButton(text="📦 8100 UC — 7600₽", callback_data="buy_8100")],
        [InlineKeyboardButton(text="📦 12610 UC — 11390₽", callback_data="buy_12610")],
        [InlineKeyboardButton(text="⚙️ Изменить PUBG ID", callback_data="edit_id")]
    ]
)

social_kb = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="🔗 Перейти в канал", url="https://t.me/ad1skauc")]]
)
