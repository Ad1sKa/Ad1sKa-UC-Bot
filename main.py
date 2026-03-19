import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, LabeledPrice, PreCheckoutQuery
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
@dp.message(F.text == "💎 Купить UC")
async def shop_menu(message: types.Message):
    await message.answer("🛒 Добавляйте паки в корзину:", reply_markup=kb.buy_tokens)

@dp.message(F.text == "👤 Профиль")
async def profile_menu(message: types.Message):
    user_data = await db.get_profile(message.from_user.id)
    if not user_data: return await message.answer("Нажми /start")
    
    bal, pid, disc = user_data["balance"], user_data["pubg_id"], user_data["discount"]
    msg = (f"👤 **Мой профиль**\n\n🆔 Твой ID: `{message.from_user.id}`\n🎮 PUBG ID: `{pid}`\n💰 Баланс: {bal}₽\n🔥 Скидка: {disc}%")
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⚙️ Изменить PUBG ID", callback_data="edit_id"))
    builder.row(InlineKeyboardButton(text="🎟 Активировать промокод", callback_data="act_promo"))
    
    await message.answer(msg, reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.message(F.text == "📜 Правила")
async def rules_menu(message: types.Message):
    rules_text = (
        "📜 **Правила нашего магазина:**\n\n"
        "1️⃣ **Сроки зачисления:** UC приходят после 15:00 МСК.\n"
        "2️⃣ **Верный ID:** Вы несете ответственность за PUBG ID. Ошиблись — UC ушли другому.\n"
        "3️⃣ **Возврат:** После оплаты возврат средств невозможен.\n"
        "4️⃣ **Оплата:** Через безопасный шлюз Telegram Payments."
    )
    await message.answer(rules_text, parse_mode="Markdown")

# --- КОРЗИНА И ПЛАТЕЖИ ---
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
        return await callback.message.answer("🛒 Ваша корзина пуста!")
    
    if not u_data or u_data["pubg_id"] == "Не указан": 
        return await callback.message.answer("⚠️ Пожалуйста, укажи свой PUBG ID в профиле перед оплатой!")
    
    cart = user_carts[uid]
    total_price = cart['price']
    if u_data["discount"] > 0:
        total_price = int(total_price * (1 - u_data["discount"] / 100))

    # Отправка инвойса Telegram Payments
    await bot.send_invoice(
        chat_id=uid,
        title=f"Заказ {cart['uc']} UC",
        description=f"Пополнение для PUBG ID: {u_data['pubg_id']}",
        payload=f"order_{uid}_{cart['uc']}",
        provider_token=config.PAYMENTS_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(label="Покупка UC", amount=total_price * 100)], # Сумма в копейках
        start_parameter="uc_topup"
    )

# Подтверждение готовности принять платеж (экран "Сохранить реквизиты")
@dp.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_q: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)

# Обработка успешной оплаты
@dp.message(F.successful_payment)
async def successful_payment(message: types.Message):
    uid = message.from_user.id
    payment_info = message.successful_payment
    u_data = await db.get_profile(uid)
    
    # Очищаем корзину после оплаты
    user_carts[uid] = {'uc': 0, 'price': 0, 'count': 0}
    
    await message.answer(f"✅ **Оплата прошла успешно!**\nСумма: {payment_info.total_amount // 100}₽\n\n💎 UC будут зачислены на ID `{u_data['pubg_id']}` после 15:00 МСК.")
    
    # Уведомление админу
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🚀 Выполнить", callback_data=f"adm_done_{uid}"))
    
    await bot.send_message(
        config.ADMIN_ID, 
        f"💰 **НОВАЯ ОПЛАТА (Payments)!**\n👤 Юзер: @{message.from_user.username}\n🎮 ID: `{u_data['pubg_id']}`\n💵 Сумма: {payment_info.total_amount // 100}₽",
        reply_markup=builder.as_markup()
    )

# --- АДМИНКА И СОСТОЯНИЯ ---
@dp.callback_query(F.data.startswith("adm_done_"))
async def admin_done(callback: types.CallbackQuery):
    uid = int(callback.data.split("_")[2])
    await bot.send_message(uid, "💎 **UC зачислены!** Приятной игры и ждем вас снова ⭐")
    await callback.message.edit_text(f"{callback.message.text}\n\n✅ ВЫПОЛНЕНО")
    await callback.answer("Готово!")

@dp.callback_query(F.data == "act_promo")
async def start_promo(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer(); await callback.message.answer("🎁 Введите промокод:"); await state.set_state(Form.waiting_for_promo)

@dp.message(Form.waiting_for_promo)
async def process_promo(message: types.Message, state: FSMContext):
    res = await db.activate_promo_db(message.from_user.id, message.text); await message.answer(res); await state.clear()

@dp.callback_query(F.data == "edit_id")
async def edit_id(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer(); await callback.message.answer("⌨️ Введи свой PUBG ID:"); await state.set_state(Form.waiting_for_pubg_id)

@dp.message(Form.waiting_for_pubg_id)
async def save_id(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        await db.update_pubg_id(message.from_user.id, message.text)
        await state.clear()
        await message.answer("✅ ID сохранен!", reply_markup=kb.main_menu)

# --- ОСТАЛЬНОЕ ---
@dp.message(F.text == "🕒 График")
async def schedule(message: types.Message):
    await message.answer("🕒 **График (МСК):**\nБудни: 15:00 - 23:00 ✅\nВыходные: 10:00 - 00:00 ✅")

@dp.message(F.text == "🎧 Поддержка")
async def support_h(message: types.Message):
    await message.answer(f"🎧 Менеджер: @{config.SUPPORT_LINK}")

@dp.message(F.text.in_(["🎟 Промокоды и Скидки", "⭐ Отзывы", "🎁 Розыгрыши"]))
async def social_links(message: types.Message):
    await message.answer("🔗 Все новости и отзывы в нашем канале:", reply_markup=kb.social_kb)

async def main():
    await db.db_start(); asyncio.create_task(start_webserver())
    print("Бот запущен на Telegram Payments!"); await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
