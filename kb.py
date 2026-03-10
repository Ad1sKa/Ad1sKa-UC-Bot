from aiogram.types import (
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton
)

# Файл kb.py
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💎 Купить UC"), KeyboardButton(text="👤 Профиль")],
        [KeyboardButton(text="🕒 График"), KeyboardButton(text="📜 Инструкция")], # Добавили График
        [KeyboardButton(text="🎧 Поддержка"), KeyboardButton(text="⭐ Отзывы")],
        [KeyboardButton(text="🎁 Розыгрыши")]
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите нужный раздел..."
)

# 2. ВИТРИНА ТОВАРОВ (Инлайн-кнопки с паками UC)
buy_tokens = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📦 325 UC — 380₽", callback_data="buy_325")],
        [InlineKeyboardButton(text="📦 660 UC — 790₽", callback_data="buy_660")],
        [InlineKeyboardButton(text="📦 1800 UC — 1990₽", callback_data="buy_1800")],
        [InlineKeyboardButton(text="📦 3850 UC — 3825₽", callback_data="buy_3850")],
        [InlineKeyboardButton(text="📦 8100 UC — 7600₽", callback_data="buy_8100")],
        [InlineKeyboardButton(text="📦 12610 UC — 11390₽", callback_data="buy_12610")],
        [InlineKeyboardButton(text="⚙️ Изменить мой PUBG ID", callback_data="edit_id")]
    ]
)

# 3. КНОПКИ ВНУТРИ ПРОФИЛЯ
profile_inline = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="💳 Пополнить баланс", callback_data="deposit")],
        [InlineKeyboardButton(text="📝 История заказов", callback_data="history")],
        [InlineKeyboardButton(text="⚙️ Настроить ID", callback_data="edit_id")]
    ]
)

# 4. КНОПКА ОТМЕНЫ (Для выхода из состояний ввода)
cancel = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="❌ Отмена")]
    ],
    resize_keyboard=True
)

# 5. КНОПКА ПЕРЕХОДА В КАНАЛ (Для "Отзывы" или "Розыгрыши")
social_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Перейти в канал", url="https://t.me/ad1skauc")]
    ]
)

# 6. ПОДТВЕРЖДЕНИЕ ЗАКАЗА (Появляется перед оплатой)
confirm_order = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить и оплатить", callback_data="pay_confirm")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="pay_cancel")]
    ]
)
# Добавь это в конец файла kb.py
reviews_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="💬 Читать отзывы", url="https://t.me/ad1skauc")],
        [InlineKeyboardButton(text="✍️ Оставить отзыв", url="https://t.me/ad1skauc")]
    ]
)
# Добавь это в конец kb.py
def admin_payment_kb(user_id, amount):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Оплачено", callback_data=f"pay_done_{user_id}_{amount}")],
        [InlineKeyboardButton(text="❌ Отказ", callback_data=f"pay_bad_{user_id}")]
    ]
)
