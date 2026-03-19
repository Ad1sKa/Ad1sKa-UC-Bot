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
@dp.message(F.text == "💎 Купить UC")
async def shop_menu(message: types.Message):
    await message.answer("🛒 Добавляйте паки в корзину:", reply_markup=kb.buy_tokens)

@dp.message(F.text == "👤 Профиль")
async def profile_menu(message: types.Message):
    user_data = await db.get_profile(message.from_user.id)
    if not user_data: return await message.answer("Нажми /start")
    
    bal, pid, disc = user_data["balance"], user_data["pubg_id"], user_data["discount"]
    msg = (f"👤 **Мой профиль**\n\n"
           f"🆔 Твой ID: `{message.from_user.id}`\n"
           f"🎮 PUBG ID: `{pid}`\n"
           f"💰 Баланс: {bal}₽\n"
           f"🔥 Скидка: {disc}%")
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⚙️ Изменить PUBG ID", callback_data="edit_id"))
    builder.row(InlineKeyboardButton(text="🎟 Активировать промокод", callback_data="act_promo"))
    
    await message.answer(msg, reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.message(F.text == "📜 Правила")
async def rules_menu(message: types.Message):
    rules_text = (
        "📜 **Правила нашего магазина:**\n\n"
        "1️⃣ **Сроки зачисления:** UC приходят после 15:00 МСК (в будни) или в течение дня (в выходные).\n"
        "2️⃣ **Верный ID:** Вы несете полную ответственность за указанный PUBG ID. Если ID неверный, возврат невозможен.\n"
        "3️⃣ **Оплата:** Принимаем чеки только из официальных банковских приложений.\n"
        "4️⃣ **Возврат:** Возврат средств после зачисления товара не осуществляется.\n\n"
        "Покупая у нас, вы автоматически соглашаетесь с данными правилами. Приятных покупок! 🍀"
    )
    await message.answer(rules_text, parse_mode="Markdown")

@dp.message(F.text == "🕒 График")
async def schedule(message: types.Message):
    await message.answer("🕒 **График (МСК):**\nБудни: 15:00 - 23:00 ✅\nВыходные: 10:00 - 00:00 ✅\n\n*Админ на учебе до 15:00 МСК!*", parse_mode="Markdown")

@dp.message(F.text == "🎧 Поддержка")
async def support_h(message: types.Message):
    await message.answer(f"🎧 Менеджер: @{config.SUPPORT_LINK}")

@dp.message(F.text.in_(["🎟 Промокоды и Скидки", "⭐ Отзывы", "🎁 Розыгрыши"]))
async def social_links(message: types.Message):
    await message.answer("🔗 **Все новости, отзывы и бонусы в нашем канале:**", reply_markup=kb.social_kb, parse_mode="Markdown")

# --- КОРЗИНА И ОФОРМЛЕНИЕ ---
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
    await callback.answer(); uid = callback.from_user.id
    if uid not in user_carts or user_carts[uid]['count'] == 0: return await callback.message.answer("🛒 Пусто!")
    u_data = await db.get_profile(uid)
    if not u_data or u_data["pubg_id"] == "Не указан": return await callback.message.answer("⚠️ Укажи ID в профиле!")
    
    cart = user_carts[uid]; total = cart['price']
    if u_data["discount"] > 0: total = int(total * (1 - u_data["discount"] / 100))
    
    pay_msg = (
        f"💳 **Оформление заказа**\n\n💎 **Товар:** {cart['uc']} UC\n💰 **К оплате:** {total}₽\n🎮 **ID:** `{u_data['pubg_id']}`\n\n"
        f"🏦 **Карта (Беларусбанк):**\n`4246 4100 8081 2321`\n👤 **Владелец:** `KERYMOVA NATALIA`\n\n✅ Пришли скрин чека сюда!"
    )
    await callback.message.answer(pay_msg, parse_mode="Markdown")
    user_carts[uid] = {'uc': 0, 'price': 0, 'count': 0}

# --- АДМИНКА И СОСТОЯНИЯ ---
@dp.message(F.photo)
async def handle_screenshot(message: types.Message):
    u_data = await db.get_profile(message.from_user.id)
    await message.answer("⏳ Чек получен! Ждем подтверждения.")
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✅ Оплачено", callback_data=f"adm_ok_{message.from_user.id}"))
    builder.add(InlineKeyboardButton(text="❌ Отказ", callback_data=f"adm_no_{message.from_user.id}"))
    await bot.send_photo(config.ADMIN_ID, message.photo[-1].file_id, caption=f"💰 ЧЕК!\n🎮 ID: `{u_data['pubg_id'] if u_data else '???'}`\n👤 @{message.from_user.username}", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("adm_"))
async def admin_decision(callback: types.CallbackQuery):
    await callback.answer(); d = callback.data.split("_"); action, uid = d[1], int(d[2])
    if action == "ok":
        await bot.send_message(uid, "✅ **Оплата подтверждена!**\nЗачисление после 15:00 МСК.", parse_mode="Markdown")
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(text="🚀 Выполнить", callback_data=f"adm_done_{uid}"))
        await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n✅ ПРИНЯТА.", reply_markup=builder.as_markup())
    elif action == "done":
        await bot.send_message(uid, "💎 **UC зачислены!** Оставь отзыв в канале ⭐")
        await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n🏆 ВЫПОЛНЕНО")
    elif action == "no":
        await bot.send_message(uid, "❌ Оплата отклонена.")

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

async def main():
    await db.db_start(); asyncio.create_task(start_webserver())
    print("Бот запущен!"); await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
