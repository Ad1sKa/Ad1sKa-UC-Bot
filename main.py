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
    await message.answer(f"📊 Юзеров: {len(users)}")

# --- МЕНЮ ---
@dp.message(F.text == "💎 Купить UC")
async def shop_menu(message: types.Message):
    await message.answer("🛒 Добавляйте паки в корзину:", reply_markup=kb.buy_tokens)

@dp.message(F.text == "👤 Профиль")
async def profile_menu(message: types.Message):
    user_data = await db.get_profile(message.from_user.id)
    if not user_data: return await message.answer("Жми /start")
    bal, pid, disc = user_data["balance"], user_data["pubg_id"], user_data["discount"]
    msg = f"👤 Профиль:\n🆔 TG: {message.from_user.id}\n🎮 ID: {pid}\n💰 Баланс: {bal}₽"
    edit_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚙️ Изменить PUBG ID", callback_data="edit_id")]])
    await message.answer(msg, reply_markup=edit_kb)

@dp.message(F.text == "🕒 График")
async def schedule(message: types.Message):
    await message.answer("🕒 Будни: 15:00 - 23:00\nВыходные: 10:00 - 00:00")

@dp.message(F.text == "🎧 Поддержка")
async def support_handler(message: types.Message):
    await message.answer(f"🎧 Менеджер: @{config.SUPPORT_LINK}")

@dp.message(F.text.in_(["🎟 Промокоды и Скидки", "⭐ Отзывы", "🎁 Розыгрыши"]))
async def social_links(message: types.Message):
    await message.answer("🔗 Новости в канале:", reply_markup=kb.social_kb)

# --- ЛОГИКА ПРОМОКОДОВ ---
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

# --- КОРЗИНА ---
@dp.callback_query(F.data.startswith("cart_add_"))
async def add_to_cart(callback: types.CallbackQuery):
    uid = callback.from_user.id
    d = callback.data.split("_")
    # Формат cart_add_UC_PRICE
    uc, pr = int(d[2]), int(d[3])
    if uid not in user_carts: user_carts[uid] = {'uc': 0, 'price': 0, 'count': 0}
    user_carts[uid]['uc'] += uc; user_carts[uid]['price'] += pr; user_carts[uid]['count'] += 1
    await callback.answer(f"+ {uc} UC")
    await callback.message.edit_text(f"🛒 Корзина ({user_carts[uid]['count']}/10):\n💎 {user_carts[uid]['uc']} UC\n💰 {user_carts[uid]['price']}₽", reply_markup=kb.buy_tokens)

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
    c = user_carts[uid]
    await callback.message.answer(f"💳 К оплате: {c['price']}₽ за {c['uc']} UC\n🎮 ID: {u_data['pubg_id']}\n🏦 Карта: `НОМЕР`\n✅ Пришли скрин чека!")
    user_carts[uid] = {'uc': 0, 'price': 0, 'count': 0}

# --- ПОДТВЕРЖДЕНИЕ ЧЕКА (ПРИДЕТ АДМИНУ) ---
@dp.message(F.photo)
async def handle_screenshot(message: types.Message):
    u_data = await db.get_profile(message.from_user.id)
    await message.answer("⏳ Чек получен! Ждем подтверждения.")
    
    # Кнопки для админа
    adm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Оплачено", callback_data=f"adm_ok_{message.from_user.id}")],
        [InlineKeyboardButton(text="❌ Отказ", callback_data=f"adm_no_{message.from_user.id}")]
    ])
    
    # Прямая отправка на ADMIN_ID из конфига
    await bot.send_photo(
        chat_id=config.ADMIN_ID, 
        photo=message.photo[-1].file_id, 
        caption=f"💰 НОВЫЙ ЧЕК!\n🎮 ID: {u_data['pubg_id']}\n👤 Юзер: @{message.from_user.username}",
        reply_markup=adm_kb
    )

@dp.callback_query(F.data.startswith("adm_"))
async def admin_decision(callback: types.CallbackQuery):
    await callback.answer()
    if callback.from_user.id != config.ADMIN_ID: return
    
    # Разбираем данные: adm | действие | айди
    d = callback.data.split("_")
    action, user_id = d[1], int(d[2])
    
    if action == "ok":
        await bot.send_message(user_id, "💎 **UC зачислены!** Оставьте отзыв в канале! ⭐")
        await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n✅ ОДОБРЕНО")
    else:
        await bot.send_message(user_id, "❌ **Оплата отклонена.** Свяжитесь с поддержкой.")
        await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n❌ ОТКЛОНЕНО")

# --- ВВОД ID ---
@dp.callback_query(F.data == "edit_id")
async def edit_id(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer(); await callback.message.answer("⌨️ Введите цифровой PUBG ID:")
    await state.set_state(Form.waiting_for_pubg_id)

@dp.message(Form.waiting_for_pubg_id)
async def save_id(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        await db.update_pubg_id(message.from_user.id, message.text); await state.clear()
        await message.answer(f"✅ ID {message.text} сохранен!", reply_markup=kb.main_menu)

async def main():
    await db.db_start()
    asyncio.create_task(start_webserver())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
