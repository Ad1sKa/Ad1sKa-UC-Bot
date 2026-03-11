import asyncio
import logging
import os
from datetime import datetime
import pytz
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web # Важно для Render

import config
import kb
import db

logging.basicConfig(level=logging.INFO)
bot = Bot(token=config.TOKEN)
dp = Dispatcher()

# Временное хранилище корзин
user_carts = {}

class Form(StatesGroup):
    waiting_for_pubg_id = State()
    waiting_for_promo = State()

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER (ЧТОБЫ НЕ ВЫКЛЮЧАЛСЯ) ---
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

# --- АДМИН КОМАНДЫ ---
@dp.message(Command("stats"))
async def stats_cmd(message: types.Message):
    if message.from_user.id != config.ADMIN_ID: return
    users = await db.get_all_users()
    await message.answer(f"📊 Всего пользователей в базе: {len(users)}")

@dp.message(Command("send"))
async def cmd_send_all(message: types.Message, command: CommandObject):
    if message.from_user.id != config.ADMIN_ID: return
    if not command.args: return await message.answer("Пример: /send Текст")
    users = await db.get_all_users()
    count = 0
    for uid in users:
        try:
            target = uid[0] if isinstance(uid, tuple) else uid
            await bot.send_message(target, command.args)
            count += 1
            await asyncio.sleep(0.05)
        except: pass
    await message.answer(f"✅ Рассылка завершена! Получили: {count} чел.")

# --- ГЛАВНОЕ МЕНЮ ---
@dp.message(Command("start"))
async def start_command(message: types.Message):
    await db.register_user(message.from_user.id)
    await message.answer(f"Привет! 🏆 Магазин Ad1sKa UC готов к работе.", reply_markup=kb.main_menu)

@dp.message(F.text == "💎 Купить UC")
async def shop_menu(message: types.Message):
    await message.answer("🛒 Добавляйте паки в корзину (до 10 шт):", reply_markup=kb.buy_tokens)

@dp.message(F.text == "👤 Профиль")
async def profile_menu(message: types.Message):
    user_data = await db.get_profile(message.from_user.id)
    if not user_data: return await message.answer("Жми /start")
    bal, pid, disc = user_data["balance"], user_data["pubg_id"], user_data["discount"]
    msg = f"👤 Профиль:\n\n🆔 TG ID: {message.from_user.id}\n🎮 PUBG ID: {pid}\n💰 Баланс: {bal}₽"
    if disc > 0: msg += f"\n🔥 Твоя скидка: {disc}%"
    edit_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚙️ Изменить PUBG ID", callback_data="edit_id")]])
    await message.answer(msg, reply_markup=edit_kb)

@dp.message(F.text == "🕒 График")
async def schedule(message: types.Message):
    await message.answer("🕒 График (МСК):\nБудни: 15:00 - 23:00 ✅\nВыходные: 10:00 - 00:00 ✅\n\n*Админ на учебе до 15:00!*")

@dp.message(F.text == "🎧 Поддержка")
async def support_handler(message: types.Message):
    await message.answer(f"🎧 По всем вопросам пишите менеджеру: @{config.SUPPORT_LINK}")

@dp.message(F.text.in_(["🎟 Промокоды и Скидки", "⭐ Отзывы", "🎁 Розыгрыши"]))
async def social_links(message: types.Message):
    kb_p = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Ввести промокод", callback_data="act_promo")],
        [InlineKeyboardButton(text="🔗 Наш канал", url="https://t.me/ad1skauc")]
    ])
    await message.answer("🔗 Все новости, ссылка на группу с отзывами и бонусы в нашем канале:", reply_markup=kb_p)

# --- ЛОГИКА КОРЗИНЫ ---
@dp.callback_query(F.data.startswith("cart_add_"))
async def add_to_cart(callback: types.CallbackQuery):
    uid = callback.from_user.id
    data = callback.data.split("_")
    uc_val, price_val = int(data[2]), int(data[3])

    if uid not in user_carts: user_carts[uid] = {'uc': 0, 'price': 0, 'count': 0}
    if user_carts[uid]['count'] >= 10: return await callback.answer("❌ Максимум 10 товаров!", show_alert=True)

    user_carts[uid]['uc'] += uc_val
    user_carts[uid]['price'] += price_val
    user_carts[uid]['count'] += 1
    await callback.answer(f"➕ Добавлено: {uc_val} UC")
    await callback.message.edit_text(
        f"🛒 Корзина ({user_carts[uid]['count']}/10):\n💎 Всего: {user_carts[uid]['uc']} UC\n💰 Сумма: {user_carts[uid]['price']}₽",
        reply_markup=kb.buy_tokens
    )

@dp.callback_query(F.data == "cart_clear")
async def clear_cart(callback: types.CallbackQuery):
    user_carts[callback.from_user.id] = {'uc': 0, 'price': 0, 'count': 0}
    await callback.answer("🗑 Корзина очищена")
    await callback.message.edit_text("🛒 Корзина пуста. Выберите паки:", reply_markup=kb.buy_tokens)

@dp.callback_query(F.data == "cart_checkout")
async def checkout(callback: types.CallbackQuery):
    await callback.answer()
    uid = callback.from_user.id
    if uid not in user_carts or user_carts[uid]['count'] == 0:
        return await callback.message.answer("🛒 Ваша корзина пуста!")

    user_data = await db.get_profile(uid)
    if not user_data or user_data["pubg_id"] == "Не указан":
        return await callback.message.answer("⚠️ Сначала укажите PUBG ID в профиле!")

    cart = user_carts[uid]
    total_price = cart['price']
    if user_data["discount"] > 0:
        total_price = int(total_price * (1 - user_data["discount"] / 100))

    await callback.message.answer(
        f"💳 Оформление заказа:\n\n"
        f"💎 Товар: {cart['uc']} UC\n"
        f"💰 К оплате: {total_price}₽\n"
        f"🎮 PUBG ID: {user_data['pubg_id']}\n\n"
        f"🏦 Карта: 4246 4100 8081 2321\n"
        f"👤 Владелец: KERYMOVA NATALIA\n\n"
        "✅ Пришли скриншот чека сюда."
    )
    user_carts[uid] = {'uc': 0, 'price': 0, 'count': 0}

# --- ПОДТВЕРЖДЕНИЕ ЧЕКА ---
@dp.message(F.photo)
async def handle_screenshot(message: types.Message):
    user_data = await db.get_profile(message.from_user.id)
    await message.answer("⏳ Чек получен! Ждем подтверждения администратором.")
    adm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Оплачено", callback_data=f"adm_done_{message.from_user.id}")],
        [InlineKeyboardButton(text="❌ Отказ", callback_data=f"adm_bad_{message.from_user.id}")]
    ])
    await bot.send_photo(config.ADMIN_ID, message.photo[-1].file_id, 
                         caption=f"💰 Чек!\n🎮 ID: {user_data['pubg_id']}\n👤 @{message.from_user.username}", reply_markup=adm_kb)

@dp.callback_query(F.data.startswith("adm_"))
async def admin_decision(callback: types.CallbackQuery):
    await callback.answer()
    data = callback.data.split("_")
    action, uid = data[1], int(data[2])
    if action == "done":
        await bot.send_message(uid, "✅ Оплата подтверждена! UC скоро будут зачислены.")
    else:
        await bot.send_message(uid, "❌ Оплата отклонена.")
    await callback.message.delete()

# --- ВВОД ID И ПРОМО ---
@dp.callback_query(F.data == "act_promo")
async def start_promo(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("⌨️ Введите промокод:")
    await state.set_state(Form.waiting_for_promo)

@dp.message(Form.waiting_for_promo)
async def process_promo(message: types.Message, state: FSMContext):
    res = await db.activate_promo_db(message.from_user.id, message.text)
    await message.answer(res)
    await state.clear()

@dp.callback_query(F.data == "edit_id")
async def edit_id(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer(); await callback.message.answer("⌨️ Введите цифровой PUBG ID:")
    await state.set_state(Form.waiting_for_pubg_id)

@dp.message(Form.waiting_for_pubg_id)
async def save_id(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        await db.update_pubg_id(message.from_user.id, message.text); await state.clear()
        await message.answer(f"✅ ID {message.text} сохранен!", reply_markup=kb.main_menu)

# --- ЗАПУСК ---
async def main():
    await db.db_start()
    asyncio.create_task(start_webserver()) # Запуск сервера для Render
    print("Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
