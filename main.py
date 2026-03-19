import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery
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

@dp.message(Command("stats"))
async def stats_cmd(message: types.Message):
    if message.from_user.id != config.ADMIN_ID: return
    users = await db.get_all_users()
    await message.answer(f"📊 Юзеров в базе: {len(users)}")

# --- МЕНЮ ---
@dp.message(F.text == "💎 Купить UC")
async def shop_menu(message: types.Message):
    await message.answer("🛒 Добавляйте паки в корзину:", reply_markup=kb.buy_tokens)

@dp.message(F.text == "👤 Профиль")
async def profile_menu(message: types.Message):
    user_data = await db.get_profile(message.from_user.id)
    if not user_data: return await message.answer("Нажми /start")
    bal, pid, disc = user_data["balance"], user_data["pubg_id"], user_data["discount"]
    msg = f"👤 **Профиль:**\n\n🆔 TG ID: `{message.from_user.id}`\n🎮 PUBG ID: `{pid}`\n💰 Баланс: {bal}₽"
    if disc > 0: msg += f"\n🔥 Твоя скидка: {disc}%"
    
    # Кнопка профиля (ИСПРАВЛЕНО: чистая структура без лишних скобок)
    btns =]
    edit_kb = InlineKeyboardMarkup(inline_keyboard=btns)
    await message.answer(msg, reply_markup=edit_kb, parse_mode="Markdown")

# --- КОРЗИНА ---
@dp.callback_query(F.data.startswith("cart_add_"))
async def add_to_cart(callback: types.CallbackQuery):
    uid = callback.from_user.id
    d = callback.data.split("_")
    # Индексы: 2 - UC, 3 - Цена
    uc, pr = int(d[2]), int(d[3])
    if uid not in user_carts: user_carts[uid] = {'uc': 0, 'price': 0, 'count': 0}
    user_carts[uid]['uc'] += uc
    user_carts[uid]['price'] += pr
    user_carts[uid]['count'] += 1
    await callback.answer(f"+ {uc} UC")
    await callback.message.edit_text(f"🛒 Корзина:\n💎 {user_carts[uid]['uc']} UC\n💰 {user_carts[uid]['price']}₽", reply_markup=kb.buy_tokens)

@dp.callback_query(F.data == "cart_clear")
async def clear_cart(callback: types.CallbackQuery):
    user_carts[callback.from_user.id] = {'uc': 0, 'price': 0, 'count': 0}
    await callback.answer("🗑 Очищено")
    await callback.message.edit_text("🛒 Корзина пуста.", reply_markup=kb.buy_tokens)

# --- ОФОРМЛЕНИЕ ЗАКАЗА (PAYMENTS) ---
@dp.callback_query(F.data == "cart_checkout")
async def checkout(callback: types.CallbackQuery):
    await callback.answer()
    uid = callback.from_user.id
    if uid not in user_carts or user_carts[uid]['count'] == 0: 
        return await callback.message.answer("🛒 Пусто!")
    
    u_data = await db.get_profile(uid)
    if not u_data or u_data["pubg_id"] == "Не указан": 
        return await callback.message.answer("⚠️ Укажи ID в профиле!")
    
    cart = user_carts[uid]
    total = cart['price']
    if u_data["discount"] > 0: 
        total = int(total * (1 - u_data["discount"] / 100))
    
    # Отправляем "шторку" оплаты
    await bot.send_invoice(
        chat_id=uid,
        title=f"Покупка {cart['uc']} UC",
        description=f"Для PUBG ID: {u_data['pubg_id']}",
        payload=f"order_{uid}",
        provider_token=config.PAYMENTS_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(label="Заказ в Ad1sKa Shop", amount=total * 100)],
        start_parameter="uc_topup"
    )
    user_carts[uid] = {'uc': 0, 'price': 0, 'count': 0}

@dp.pre_checkout_query(lambda query: True)
async def pre_checkout_query(pre_checkout_q: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: types.Message):
    await message.answer(f"✅ Оплата принята! UC будут зачислены после 15:00 МСК.")
    await bot.send_message(config.ADMIN_ID, f"💰 **НОВАЯ ОПЛАТА!**\nЮзер: @{message.from_user.username}\nСумма: {message.successful_payment.total_amount // 100} RUB")

# --- ОСТАЛЬНОЕ ---
@dp.message(F.text == "🕒 График")
async def schedule(message: types.Message):
    await message.answer("🕒 Будни: 15:00-23:00\nВыходные: 10:00-00:00")

@dp.message(F.text == "🎧 Поддержка")
async def support_h(message: types.Message):
    await message.answer(f"🎧 Менеджер: @{config.SUPPORT_LINK}")

@dp.message(F.text.in_(["🎟 Промокоды и Скидки", "⭐ Отзывы", "🎁 Розыгрыши"]))
async def social_links(message: types.Message):
    await message.answer("🔗 Новости в канале:", reply_markup=kb.social_kb)

@dp.callback_query(F.data == "act_promo")
async def start_promo(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("🎁 Введите промокод:")
    await state.set_state(Form.waiting_for_promo)

@dp.message(Form.waiting_for_promo)
async def process_promo(message: types.Message, state: FSMContext):
    res = await db.activate_promo_db(message.from_user.id, message.text)
    await message.answer(res)
    await state.clear()

@dp.callback_query(F.data == "edit_id")
async def edit_id(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("⌨️ Введи ID:")
    await state.set_state(Form.waiting_for_pubg_id)

@dp.message(Form.waiting_for_pubg_id)
async def save_id(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        await db.update_pubg_id(message.from_user.id, message.text)
        await state.clear()
        await message.answer("✅ Сохранено!", reply_markup=kb.main_menu)

async def main():
    await db.db_start()
    asyncio.create_task(start_webserver())
    print("Запущено!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
