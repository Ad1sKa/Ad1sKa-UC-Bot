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

# Настройка логирования
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
        f"Привет, {message.from_user.first_name}! 👋\n"
        "Добро пожаловать в магазин UC. Пополняй свой аккаунт PUBG Mobile быстро и надежно.",
        reply_markup=kb.main_menu
    )

# --- АДМИН-РАССЫЛКА (/send Текст) ---
@dp.message(Command("send"))
async def cmd_send_all(message: types.Message, command: CommandObject):
    if message.from_user.id != config.ADMIN_ID:
        return
    if not command.args:
        return await message.answer("Используй: `/send Текст сообщения`", parse_mode="Markdown")

    users = await db.get_all_users()
    count = 0
    for user in users:
        try:
            await bot.send_message(user[0], command.args)
            count += 1
            await asyncio.sleep(0.05)
        except:
            pass
    await message.answer(f"✅ Рассылка завершена! Получили: {count} чел.")

# --- ГЛАВНОЕ МЕНЮ (Reply кнопки) ---

@dp.message(F.text == "💎 Купить UC")
async def shop_menu(message: types.Message):
    await message.answer(
        "🛒 **Выберите необходимое количество UC!**\n\n"
        "❗ **ВАЖНО!** Начисление UC будет производиться **ПОСЛЕ 15:00 по МСК** (в будние дни)!\n\n"
        "Выбирайте нужный пак:", 
        reply_markup=kb.buy_tokens, 
        parse_mode="Markdown"
    )

@dp.message(F.text == "👤 Профиль")
async def profile_menu(message: types.Message):
    user_data = await db.get_profile(message.from_user.id)
    balance, pubg_id = user_data
    edit_id_inline = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚙️ Изменить PUBG ID", callback_data="edit_id")]])
    await message.answer(
        f"👤 **Ваш профиль:**\n\n🆔 TG ID: `{message.from_user.id}`\n🎮 PUBG ID: `{pubg_id}`\n💰 Баланс: {balance}₽", 
        parse_mode="Markdown", 
        reply_markup=edit_id_inline
    )

@dp.message(F.text == "🕒 График")
async def schedule_handler(message: types.Message):
    await message.answer(
        "🕒 **График обработки заказов (МСК):**\n\n"
        "📅 **Будние дни (Пн-Пт):**\n"
        "• 08:00 - 15:00 — 🏫 На учебе (заказы принимаются)\n"
        "• 15:00 - 23:00 — ✅ В сети (зачисление UC)\n\n"
        "📅 **Выходные (Сб-Вс):**\n"
        "• 10:00 - 00:00 — ⚡️ Быстрая обработка\n\n"
        "*Оплачивать можно 24/7, чеки проверяю сразу, как приду со школы!*",
        parse_mode="Markdown"
    )

@dp.message(F.text == "📜 Инструкция")
async def manual_menu(message: types.Message):
    await message.answer("📖 **Инструкция:**\n1. Укажи PUBG ID в профиле.\n2. Выбери пак UC.\n3. Оплати по реквизитам.\n4. Пришли скриншот чека в этот чат.")

@dp.message(F.text == "🎧 Поддержка")
async def support_menu(message: types.Message):
    await message.answer(f"🎧 **Поддержка:** @{config.SUPPORT_LINK}")

@dp.message(F.text == "⭐ Отзывы")
async def reviews_menu(message: types.Message):
    await message.answer("⭐ **Наши отзывы:**", reply_markup=kb.social_kb)

@dp.message(F.text == "🎁 Розыгрыши")
async def giveaway_menu(message: types.Message):
    await message.answer("🎁 **Розыгрыши:**", reply_markup=kb.social_kb)

# --- ЛОГИКА ПОКУПКИ И ЧЕКОВ ---

@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: types.CallbackQuery):
    amount = callback.data.split("_")[-1]
    user_data = await db.get_profile(callback.from_user.id)
    _, pubg_id = user_data

    if pubg_id == "Не указан":
        return await callback.message.answer("⚠️ Сначала укажите ваш **PUBG ID** в профиле!")

    # Проверка школьного времени для текста
    tz_moscow = pytz.timezone('Europe/Moscow')
    now_moscow = datetime.now(tz_moscow)
    
    school_info = ""
    if 8 <= now_moscow.hour < 15:
        school_info = "\n\n⚠️ **Сейчас админ на учебе!** Подтверждение будет после 15:00 МСК."

    await callback.message.answer(
        f"💳 **Оплата заказа: {amount} UC**\n\n"
        f"🏦 Карта (Беларусбанк): `ТВОЙ_НОМЕР_КАРТЫ`\n"
        f"👤 Владелец: ИМЯ_МАМЫ\n"
        f"{school_info}\n\n"
        "✅ После оплаты **пришли скриншот чека** сюда в чат.",
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.message(F.photo)
async def handle_screenshot(message: types.Message):
    await message.answer("⏳ Чек получен! Ожидайте подтверждения администратором.")
    admin_confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Оплачено", callback_data=f"adm_done_{message.from_user.id}")],
        [InlineKeyboardButton(text="❌ Отказ", callback_data=f"adm_bad_{message.from_user.id}")]
    ])
    await bot.send_photo(
        config.ADMIN_ID, 
        message.photo[-1].file_id, 
        caption=f"💰 **Новый чек!**\nЮзер: @{message.from_user.username}\nID: `{message.from_user.id}`", 
        reply_markup=admin_confirm_kb
    )

@dp.callback_query(F.data.startswith("adm_"))
async def admin_decision(callback: types.CallbackQuery):
    if callback.from_user.id != config.ADMIN_ID: return
    data = callback.data.split("_")
    action, user_id = data[1], int(data[2])

    if action == "done":
        await bot.send_message(user_id, "✅ **Ваша оплата подтверждена!**\nUC будут зачислены в ближайшее время.")
        await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n✅ СТАТУС: ОДОБРЕНО")
    else:
        await bot.send_message(user_id, "❌ **Оплата отклонена.**\nПроверьте данные или свяжитесь с поддержкой.")
        await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n❌ СТАТУС: ОТКЛОНЕНО")
    await callback.answer()

# --- ВВОД ID ---
@dp.callback_query(F.data == "edit_id")
async def edit_pubg_id(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("⌨️ Введите ваш **PUBG ID** (только цифры):")
    await state.set_state(Form.waiting_for_pubg_id)
    await callback.answer()

@dp.message(Form.waiting_for_pubg_id)
async def process_pubg_id(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        await db.update_pubg_id(message.from_user.id, message.text)
        await state.clear()
        await message.answer(f"✅ ID `{message.text}` успешно сохранен!", reply_markup=kb.main_menu)
    else:
        await message.answer("❌ Ошибка! Введите корректный ID (только цифры).")

async def main():
    await db.db_start()
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
