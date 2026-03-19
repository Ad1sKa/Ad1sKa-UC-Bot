import asyncio
import logging
import os
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

user_carts = {}

class Form(StatesGroup):
    waiting_for_pubg_id = State()
    waiting_for_promo = State()

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ---
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

# --- КОМАНДЫ ---
@dp.message(Command("start"))
async def start_command(message: types.Message):
    await db.register_user(message.from_user.id)
    await message.answer(f"Привет! 🏆 Магазин Ad1sKa UC готов к работе.", reply_markup=kb.main_menu)

# --- МЕНЮ ---
@dp.message(F.text.contains("Правила"))
async def rules_menu(message: types.Message):
    rules_text = (
        "📜 **Правила нашего магазина:**\n\n"
        "1. **Оплата:** Перевод по реквизитам. Обязательно присылайте скриншот чека в чат.\n"
        "2. **Сроки:** Зачисление UC происходит в рабочее время (см. График).\n"
        "3. **Данные:** Проверяйте свой PUBG ID. Ошибка в ID — ответственность покупателя.\n"
        "4. **Возврат:** После начала обработки заказа возврат средств невозможен.\n\n"
        f"По всем вопросам: @{config.SUPPORT_LINK}"
    )
    await message.answer(rules_text, parse_mode="Markdown")

@dp.message(F.text == "💎 Купить UC")
async def shop_menu(message: types.Message):
    await message.answer("🛒 Добавляйте паки в корзину:", reply_markup=kb.buy_tokens)

@dp.message(F.text == "👤 Профиль")
async def profile_menu(message: types.Message):
    user_data = await db.get_profile(message.from_user.id)
    if not user_data: return await message.answer("Нажми /start")
    bal, pid, disc = user_data["balance"], user_data["pubg_id"], user_data["discount"]
    msg = f"👤 **Профиль:**\n\n🆔 TG ID: `{message.from_user.id}`\n🎮 PUBG ID: `{pid}`\n💰 Баланс: {bal}₽"
    if disc > 0: msg += f"\n🔥 Скидка: {disc}%"
    edit_kb = InlineKeyboardMarkup(inline_keyboard=])
    await message.answer(msg, reply_markup=edit_kb, parse_mode="Markdown")

@dp.message(F.text == "🕒 График")
async def schedule(message: types.Message):
    await message.answer("🕒 **График (МСК):**\nБудни: 15:00 - 23:00 ✅\nВыходные: 10:00 - 00:00 ✅", parse_mode="Markdown")

@dp.message(F.text == "🎧 Поддержка")
async def support_h(message: types.Message):
    await message.answer(f"🎧 Менеджер: @{config.SUPPORT_LINK}")

@dp.message(F.text.in_(["🎟 Промокоды и Скидки", "⭐ Отзывы", "🎁 Розыгрыши"]))
async def social_links(message: types.Message):
    await message.answer("🔗 **Все новости и бонусы в нашем канале:**", reply_markup=kb.social_kb, parse_mode="Markdown")

# --- КОРЗИНА ---
@dp.callback_query(F.data.startswith("cart_add_"))
async def add_to_cart(callback: types.CallbackQuery):
    uid = callback.from_user.id
    d = callback.data.split("_")
    uc, pr = int(d[2]), int(d[3])
    if uid not in user_carts: user_carts[uid] = {'uc': 0, 'price': 0, 'count': 0}
    user_carts[uid]['uc'] += uc; user_carts[uid]['price'] += pr; user_carts[uid]['count'] += 1
    await callback.answer(f"+ {uc} UC")
    await callback.message.edit_text(f"🛒 Корзина:\n💎 {user_carts[uid]['uc']} UC\n💰 {user_carts[uid]['price']}₽", reply_markup=kb.buy_tokens)

@dp.callback_query(F.data == "cart_clear")
async def clear_cart(callback: types.CallbackQuery):
    user_carts[callback.from_user.id] = {'uc': 0, 'price': 0, 'count': 0}
    await callback.answer("🗑 Очищено"); await callback.message.edit_text("🛒 Корзина пуста.", reply_markup=kb.buy_tokens)

@dp.callback_query(F.data == "cart_checkout")
async def checkout(callback: types.CallbackQuery):
    await callback.answer(); uid = callback.from_user.id
    if uid not in user_carts or user_carts[uid]['count'] == 0: return await callback.message.answer("🛒 Пусто!")
    u_data = await db.get_profile(uid)
    if not u_data or u_data["pubg_id"] == "Не указан": return await callback.message.answer("⚠️ Укажи ID в профиле!")
    cart = user_carts[uid]; total = cart['price']
    if u_data["discount"] > 0: total = int(total * (1 - u_data["discount"] / 100))
    pay_msg = f"💳 **Оформление заказа**\n\n💎 {cart['uc']} UC\n💰 {total}₽\n🎮 ID: `{u_data['pubg_id']}`\n\n✅ Пришли скрин чека сюда!"
    await callback.message.answer(pay_msg, parse_mode="Markdown")
    user_carts[uid] = {'uc': 0, 'price': 0, 'count': 0}

# --- АДМИНКА ---
@dp.message(F.photo)
async def handle_screenshot(message: types.Message):
    u_data = await db.get_profile(message.from_user.id)
    adm_kb = InlineKeyboardMarkup(inline_keyboard=])
    await bot.send_photo(config.ADMIN_ID, message.photo[-1].file_id, caption=f"💰 ЧЕК!\n🎮 ID: `{u_data['pubg_id'] if u_data else '???'}`", reply_markup=adm_kb)

@dp.callback_query(F.data.startswith("adm_"))
async def admin_decision(callback: types.CallbackQuery):
    await callback.answer(); d = callback.data.split("_")
    action, uid = d[1], int(d[2])
    if action == "ok":
        await bot.send_message(uid, "✅ Оплата подтверждена!"); await callback.message.edit_caption(caption="✅ ПРИНЯТО")
    elif action == "no":
        await bot.send_message(uid, "❌ Отказ."); await callback.message.edit_caption(caption="❌ ОТКАЗАНО")

@dp.callback_query(F.data == "edit_id")
async def edit_id(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer(); await callback.message.answer("⌨️ Введи ID:"); await state.set_state(Form.waiting_for_pubg_id)

@dp.message(Form.waiting_for_pubg_id)
async def save_id(message: types.Message, state: FSMContext):
    if message.text.isdigit(): await db.update_pubg_id(message.from_user.id, message.text); await state.clear(); await message.answer("✅ Сохранено!", reply_markup=kb.main_menu)

async def main():
    await db.db_start(); asyncio.create_task(start_webserver())
    print("Запущено!"); await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
