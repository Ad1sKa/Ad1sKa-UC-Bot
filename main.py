import asyncio
import logging
import os
import time
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import LabeledPrice, PreCheckoutQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
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

# --- ВЕБ-СЕРВЕР ---
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

# --- ПРАВИЛА ---
@dp.message(F.text == "📜 Правила")
async def rules_menu(message: types.Message):
    rules_text = (
        "📜 **Правила Ad1sKa Shop:**\n\n"
        "1️⃣ **Зачисление:** Все заказы обрабатываются после 15:00 МСК в порядке очереди.\n"
        "2️⃣ **PUBG ID:** Тщательно проверяйте свой ID. При ошибке в одну цифру UC уйдут другому игроку, возврат в этом случае невозможен.\n"
        "3️⃣ **Оплата:** Мы используем официальный шлюз Telegram. Ваши данные защищены.\n"
        "4️⃣ **Поддержка:** Если UC не пришли в течение 24 часов — пишите менеджеру.\n\n"
        "Покупая товар, вы соглашаетесь с данными условиями. Приятной игры! 🎮"
    )
    await message.answer(rules_text, parse_mode="Markdown")

# --- ПРОФИЛЬ ---
@dp.message(F.text == "👤 Профиль")
async def profile_menu(message: types.Message):
    user_data = await db.get_profile(message.from_user.id)
    if not user_data: return await message.answer("Нажми /start")
    
    bal, pid, disc = user_data["balance"], user_data["pubg_id"], user_data["discount"]
    msg = (f"👤 **Мой профиль**\n\n🆔 TG ID: `{message.from_user.id}`\n"
           f"🎮 PUBG ID: `{pid}`\n💰 Баланс: {bal}₽\n🔥 Скидка: {disc}%")
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⚙️ Изменить PUBG ID", callback_data="edit_id"))
    builder.row(InlineKeyboardButton(text="🎟 Активировать промокод", callback_data="act_promo"))
    await message.answer(msg, reply_markup=builder.as_markup(), parse_mode="Markdown")

# --- КОРЗИНА И ПЛАТЕЖИ (TELEGRAM PAYMENTS) ---
@dp.callback_query(F.data.startswith("cart_add_"))
async def add_to_cart(callback: types.CallbackQuery):
    uid = callback.from_user.id
    d = callback.data.split("_")
    uc, pr = int(d[2]), int(d[3])
    if uid not in user_carts: user_carts[uid] = {'uc': 0, 'price': 0, 'count': 0}
    user_carts[uid]['uc'] += uc; user_carts[uid]['price'] += pr; user_carts[uid]['count'] += 1
    await callback.answer(f"+ {uc} UC")
    await callback.message.edit_text(f"🛒 Корзина:\n💎 {user_carts[uid]['uc']} UC\n💰 {user_carts[uid]['price']}₽", reply_markup=kb.buy_tokens)

@dp.callback_query(F.data == "cart_checkout")
async def checkout(callback: types.CallbackQuery):
    await callback.answer()
    uid = callback.from_user.id
    u_data = await db.get_profile(uid)
    
    if uid not in user_carts or user_carts[uid]['count'] == 0:
        return await callback.message.answer("🛒 Пусто!")
    if not u_data or u_data["pubg_id"] == "Не указан":
        return await callback.message.answer("⚠️ Сначала укажи PUBG ID в профиле!")

    cart = user_carts[uid]
    total = int(cart['price'] * (1 - u_data["discount"] / 100)) if u_data["discount"] > 0 else cart['price']

    await bot.send_invoice(
        chat_id=uid,
        title=f"Заказ {cart['uc']} UC",
        description=f"Для аккаунта: {u_data['pubg_id']}",
        payload=f"order_{uid}_{int(time.time())}", # Уникальный ID заказа
        provider_token=config.PAYMENTS_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(label="Пополнение UC", amount=total * 100)],
        start_parameter="uc_topup"
    )

@dp.pre_checkout_query()
async def pre_checkout_query_handler(pre_checkout_q: PreCheckoutQuery):
    # Убирает зависание на экране "Сохранить реквизиты"
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: types.Message):
    uid = message.from_user.id
    user_carts[uid] = {'uc': 0, 'price': 0, 'count': 0}
    u_data = await db.get_profile(uid)
    
    await message.answer("✅ **Оплата принята!**\nUC будут зачислены после 15:00 МСК. Ожидайте уведомления.")
    
    # Кнопка для админа
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🚀 Выполнено", callback_data=f"adm_done_{uid}"))
    
    await bot.send_message(
        config.ADMIN_ID, 
        f"💰 **НОВАЯ ОПЛАТА!**\n👤 @{message.from_user.username}\n🎮 ID: `{u_data['pubg_id']}`\n💵 Сумма: {message.successful_payment.total_amount // 100}₽",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data.startswith("adm_done_"))
async def admin_done(callback: types.CallbackQuery):
    uid = int(callback.data.split("_")[2])
    await bot.send_message(uid, "💎 **UC зачислены!** Приятной игры ⭐")
    await callback.message.edit_text(f"{callback.message.text}\n\n🏆 ВЫПОЛНЕНО")

# --- ВСЁ ОСТАЛЬНОЕ ---
@dp.message(F.text == "💎 Купить UC")
async def shop_menu(message: types.Message):
    await message.answer("🛒 Выбирайте паки:", reply_markup=kb.buy_tokens)

@dp.callback_query(F.data == "edit_id")
async def edit_id(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("⌨️ Введи свой PUBG ID:"); await state.set_state(Form.waiting_for_pubg_id)

@dp.message(Form.waiting_for_pubg_id)
async def save_id(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        await db.update_pubg_id(message.from_user.id, message.text)
        await state.clear()
        await message.answer("✅ ID сохранен!", reply_markup=kb.main_menu)

async def main():
    await db.db_start(); asyncio.create_task(start_webserver())
    print("Бот запущен!"); await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
