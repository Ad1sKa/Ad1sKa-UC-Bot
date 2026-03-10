import asyncio
import logging
import os
from datetime import datetime
import pytz
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

import config
import kb
import db

logging.basicConfig(level=logging.INFO)
bot = Bot(token=config.TOKEN)
dp = Dispatcher()

class Form(StatesGroup):
    waiting_for_pubg_id = State()

async def handle(request):
    return web.Response(text="Bot is Live!")

async def start_webserver():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

@dp.message(Command("start"))
async def start_command(message: types.Message):
    await db.register_user(message.from_user.id)
    await message.answer(f"Привет, {message.from_user.first_name}! 👋\nМагазин Ad1sKa UC запущен.", reply_markup=kb.main_menu)

@dp.message(F.text == "💎 Купить UC")
async def shop_menu(message: types.Message):
    await message.answer("🛒 **Выберите пак UC!**\n\n❗ **ВАЖНО!** Начисление **ПОСЛЕ 15:00 МСК**!", reply_markup=kb.buy_tokens, parse_mode="Markdown")

@dp.message(F.text == "👤 Профиль")
async def profile_menu(message: types.Message):
    user_data = await db.get_profile(message.from_user.id)
    if user_data:
        bal, pid = user_data["balance"], user_data["pubg_id"]
        edit_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚙️ Изменить PUBG ID", callback_data="edit_id")]])
        await message.answer(f"👤 **Профиль:**\n\n🆔 TG ID: `{message.from_user.id}`\n🎮 PUBG ID: `{pid}`\n💰 Баланс: {bal}₽", parse_mode="Markdown", reply_markup=edit_kb)

@dp.message(F.text == "🕒 График")
async def schedule(message: types.Message):
    await message.answer("🕒 **График (МСК):**\nПн-Пт: 15:00 - 23:00 ✅\nСб-Вс: 10:00 - 00:00 ✅\n\n*Заказы принимаются 24/7!*", parse_mode="Markdown")

@dp.message(F.text == "📜 Инструкция")
async def manual(message: types.Message):
    await message.answer("📖 **Инструкция:**\n1. Введи ID в профиле.\n2. Выбери пак.\n3. Оплати на карту.\n4. Пришли скриншот чека сюда.", parse_mode="Markdown")

@dp.message(F.text == "⭐ Отзывы")
@dp.message(F.text == "🎁 Розыгрыши")
async def social(message: types.Message):
    await message.answer("🔗 **Официальный канал:**", reply_markup=kb.social_kb, parse_mode="Markdown")

@dp.message(F.text == "🎧 Поддержка")
async def support(message: types.Message):
    await message.answer(f"🎧 Поддержка: @{config.SUPPORT_LINK}")

@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: types.CallbackQuery):
    await callback.answer()
    amount = callback.data.split("_")[-1]
    user_data = await db.get_profile(callback.from_user.id)
    if user_data["pubg_id"] == "Не указан":
        return await callback.message.answer("⚠️ Сначала укажите PUBG ID в профиле!")
    await callback.message.answer(f"💳 **Оплата: {amount} UC**\n\n🏦 Карта: `4246 4100 8081 2321`\n👤 Владелец: Наталья К.\n\n✅ Пришли скрин чека сюда.", parse_mode="Markdown")

@dp.message(F.photo)
async def handle_screenshot(message: types.Message):
    if message.chat.type != 'private': return
    user_data = await db.get_profile(message.from_user.id)
    p_id = user_data["pubg_id"]
    await message.answer("⏳ Чек получен! Ждите подтверждения.")
    adm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Оплачено", callback_data=f"adm_done_{message.from_user.id}")],
        [InlineKeyboardButton(text="❌ Отказ", callback_data=f"adm_bad_{message.from_user.id}")]
    ])
    await bot.send_photo(config.ADMIN_ID, message.photo[-1].file_id, caption=f"💰 Чек!\n🎮 ID: `{p_id}`\n👤 @{message.from_user.username}", reply_markup=adm_kb)

@dp.callback_query(F.data.startswith("adm_"))
async def admin_decision(callback: types.CallbackQuery):
    if callback.from_user.id != config.ADMIN_ID: return
    data = callback.data.split("_")
    action, user_id = data[1], int(data[2])
    if action == "done":
        await bot.send_message(user_id, "✅ Оплата подтверждена! UC зачисляются.")
    else:
        await bot.send_message(user_id, "❌ Оплата отклонена.")
    await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n✅ СТАТУС ОБРАБОТАН")
    await callback.answer()

@dp.callback_query(F.data == "edit_id")
async def edit_id(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer(); await callback.message.answer("⌨️ Введите цифровой **PUBG ID**:")
    await state.set_state(Form.waiting_for_pubg_id)

@dp.message(Form.waiting_for_pubg_id)
async def save_id(message: types.Message, state: FSMContext):
    if message.text.isdigit() and 7 <= len(message.text) <= 11:
        await db.update_pubg_id(message.from_user.id, message.text)
        await state.clear()
        await message.answer(f"✅ ID `{message.text}` сохранен!", reply_markup=kb.main_menu)
    else: await message.answer("❌ Введите корректный ID (7-11 цифр).")

async def main():
    await db.db_start()
    asyncio.create_task(start_webserver())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
