import asyncio
import logging
import os
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
    await message.answer(f"Привет! 🏆 Магазин Ad1sKa UC готов к работе.", reply_markup=kb.main_menu)

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
    
    # Использование Builder исключает ошибки со скобками
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✏️ Изменить PUBG ID", callback_data="edit_id"))
    builder.row(InlineKeyboardButton(text="🎟 Активировать промокод", callback_data="act_promo"))
    
    await message.answer(msg, reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("cart_add_"))
async def add_to_cart(callback: types.CallbackQuery):
    uid = callback.from_user.id
    d = callback.data.split("_")
    uc, pr = int(d[2]), int(d[3])
    if uid not in user_carts: user_carts[uid] = {'uc': 0, 'price': 0, 'count': 0}
    user_carts[uid]['uc'] += uc
    user_carts[uid]['price'] += pr
    user_carts[uid]['count'] += 1
    await callback.answer(f"+ {uc} UC")
    await callback.message.edit_text(f"🛒 Корзина:\n💎 {user_carts[uid]['uc']} UC\n💰 {user_carts[uid]['price']}₽", reply_markup=kb.buy_tokens)

@dp.callback_query(F.data == "cart_checkout")
async def checkout(callback: types.CallbackQuery):
    uid = callback.from_user.id
    u_data = await db.get_profile(uid)
    if not u_data or u_data["pubg_id"] == "Не указан": 
        return await callback.message.answer("⚠️ Укажи ID в профиле!")
    
    cart = user_carts.get(uid, {'price': 0, 'uc': 0, 'count': 0})
    if cart['count'] == 0: return await callback.answer("Корзина пуста")
    
    total = int(cart['price'] * (1 - u_data["discount"] / 100)) if u_data["discount"] > 0 else cart['price']
    
    await bot.send_invoice(
        chat_id=uid,
        title=f"Покупка {cart['uc']} UC",
        description=f"Для PUBG ID: {u_data['pubg_id']}",
        payload=f"order_{uid}",
        provider_token=config.PAYMENTS_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(label="Заказ", amount=total * 100)],
        start_parameter="uc_topup"
    )

@dp.pre_checkout_query()
async def pre_checkout_query_handler(pre_checkout_q: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: types.Message):
    await message.answer(f"✅ Оплата принята! Ожидайте зачисления.")
    await bot.send_message(config.ADMIN_ID, f"💰 ОПЛАТА: @{message.from_user.username} | {message.successful_payment.total_amount // 100}₽")

@dp.message(F.photo)
async def handle_screenshot(message: types.Message):
    u_data = await db.get_profile(message.from_user.id)
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✅ Ок", callback_data=f"adm_ok_{message.from_user.id}"))
    builder.add(InlineKeyboardButton(text="❌ Нет", callback_data=f"adm_no_{message.from_user.id}"))
    
    await bot.send_photo(
        config.ADMIN_ID, 
        message.photo[-1].file_id, 
        caption=f"Чек от {message.from_user.id}\nID: {u_data['pubg_id'] if u_data else '?'}",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data.startswith("adm_"))
async def admin_decision(callback: types.CallbackQuery):
    d = callback.data.split("_")
    action, uid = d[1], int(d[2])
    
    if action == "ok":
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(text="🏆 Готово", callback_data=f"adm_done_{uid}"))
        await bot.send_message(uid, "✅ Ваша оплата подтверждена!")
        await callback.message.edit_caption(caption="✅ Подтверждено", reply_markup=builder.as_markup())
    elif action == "done":
        await bot.send_message(uid, "💎 UC зачислены!")
        await callback.message.edit_caption(caption="🏆 Выполнено")

@dp.callback_query(F.data == "edit_id")
async def edit_id(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("⌨️ Введи свой PUBG ID:")
    await state.set_state(Form.waiting_for_pubg_id)

@dp.message(Form.waiting_for_pubg_id)
async def save_id(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        await db.update_pubg_id(message.from_user.id, message.text)
        await state.clear()
        await message.answer("✅ ID сохранен!", reply_markup=kb.main_menu)

async def main():
    await db.db_start()
    asyncio.create_task(start_webserver())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
