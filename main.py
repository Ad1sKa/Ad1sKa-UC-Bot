import asyncio
import logging
from datetime import datetime
import pytz
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import config
import kb
import db

logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.TOKEN)
dp = Dispatcher()

class Form(StatesGroup):
    waiting_for_pubg_id = State()

# --- КОМАНДА /START ---
@dp.message(Command("start"))
async def start_command(message: types.Message):
    await db.register_user(message.from_user.id)
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\nМагазин UC запущен.",
        reply_markup=kb.main_menu
    )

# --- ОБРАБОТКА КНОПОК МЕНЮ (ЖЕСТКОЕ СОВПАДЕНИЕ) ---

@dp.message(F.text == "💎 Купить UC")
async def shop_menu(message: types.Message):
    await message.answer("🛒 **Выберите необходимое количество UC:**", reply_markup=kb.buy_tokens, parse_mode="Markdown")

@dp.message(F.text == "👤 Профиль")
async def profile_menu(message: types.Message):
    user_data = await db.get_profile(message.from_user.id)
    balance, pubg_id = user_data
    edit_id_inline = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚙️ Изменить PUBG ID", callback_data="edit_id")]])
    await message.answer(f"👤 **Профиль:**\n\n🆔 TG ID: `{message.from_user.id}`\n🎮 PUBG ID: `{pubg_id}`\n💰 Баланс: {balance}₽", parse_mode="Markdown", reply_markup=edit_id_inline)

@dp.message(F.text == "📜 Инструкция")
async def manual_menu(message: types.Message):
    await message.answer("📖 **Инструкция:**\n1. Введи PUBG ID в профиле.\n2. Выбери пак.\n3. Оплати и пришли чек.")

@dp.message(F.text == "🎧 Поддержка")
async def support_menu(message: types.Message):
    await message.answer(f"🎧 **Поддержка:** @{config.SUPPORT_LINK}")

@dp.message(F.text == "⭐ Отзывы")
async def reviews_menu(message: types.Message):
    await message.answer("⭐ **Наши отзывы:**", reply_markup=kb.social_kb)

@dp.message(F.text == "🎁 Розыгрыши")
async def giveaway_menu(message: types.Message):
    await message.answer("🎁 **Розыгрыши:**", reply_markup=kb.social_kb)

# --- ЛОГИКА ПОКУПКИ (С КАРТОЙ И ШКОЛОЙ) ---

@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: types.CallbackQuery):
    uc_amount = callback.data.split("_")[-1]
    user_data = await db.get_profile(callback.from_user.id)
    _, pubg_id = user_data

    if pubg_id == "Не указан":
        return await callback.message.answer("⚠️ Сначала укажите свой **PUBG ID** в профиле!")

    # Проверка времени (МСК)
    tz_moscow = pytz.timezone('Europe/Moscow')
    now_moscow = datetime.now(tz_moscow)
    
    school_warning = ""
    if 8 <= now_moscow.hour < 15:
        school_warning = "\n\n🏫 **Внимание:** Сейчас админ на учебе. Подтверждение будет после 15:00 МСК."

    await callback.message.answer(
        f"💳 **Оплата: {uc_amount} UC**\n\n"
        f"🏦 Карта (Беларусбанк): `9112 3801 0161 5120`\n"
        f"👤 Владелец карты: KAMIL KERYMAU\n"
        f"{school_warning}\n\n"
        "‼️ Пришли скриншот чека в этот чат.",
        parse_mode="Markdown"
    )
    await callback.answer()

# --- ПРИЕМ ЧЕКА И АДМИНКА ---

@dp.message(F.photo)
async def handle_screenshot(message: types.Message):
    await message.answer("⏳ Чек получен! Ждите подтверждения.")
    admin_confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Оплачено", callback_data=f"adm_done_{message.from_user.id}")],
        [InlineKeyboardButton(text="❌ Отказ", callback_data=f"adm_bad_{message.from_user.id}")]
    ])
    await bot.send_photo(config.ADMIN_ID, message.photo[-1].file_id, caption=f"💰 Чек от @{message.from_user.username}", reply_markup=admin_confirm_kb)

@dp.callback_query(F.data.startswith("adm_"))
async def admin_decision(callback: types.CallbackQuery):
    if callback.from_user.id != config.ADMIN_ID: return
    data = callback.data.split("_")
    action, user_id = data[1], int(data[2])

    if action == "done":
        await bot.send_message(user_id, "✅ Оплата подтверждена! UC зачисляются.")
    else:
        await bot.send_message(user_id, "❌ Оплата отклонена.")
    await callback.answer()

# --- ВВОД ID ---
@dp.callback_query(F.data == "edit_id")
async def edit_pubg_id(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("⌨️ Введите ваш **PUBG ID**:")
    await state.set_state(Form.waiting_for_pubg_id)
    await callback.answer()

@dp.message(Form.waiting_for_pubg_id)
async def process_pubg_id(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        await db.update_pubg_id(message.from_user.id, message.text)
        await state.clear()
        await message.answer(f"✅ ID `{message.text}` сохранен!", reply_markup=kb.main_menu)
    else:
        await message.answer("❌ Введите цифры.")

async def main():
    await db.db_start()
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
