import asyncio
import logging
import os
import aiohttp
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

# --- АВТОМАТИЧЕСКИЙ ТРЕКЕР ДОНАТОВ (DONATIONALERTS) ---
async def donationalerts_alerts_handler():
    """Фоновая задача, подключается к DonationAlerts и ждет новые оплаты"""
    uri = "wss://://donationalerts.com"
    token = config.DA_API_KEY 
    
    connect_payload = {
        "params": {"token": token},
        "id": 1
    }
    
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(uri) as ws:
                    await ws.send_json(connect_payload)
                    logging.info("Успешно подключились к DonationAlerts WebSocket!")
                    
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = msg.json()
                            
                            if "data" in data and "data" in data["data"]:
                                donation = data["data"]["data"]
                                amount = float(donation.get("amount", 0))
                                comment = donation.get("message", "")
                                
                                if "ЗАКАЗ #" in comment:
                                    try:
                                        parts = comment.split("ЗАКАЗ #")
                                        buyer_tg_id = int(parts[1].strip().split()[0])
                                        
                                        u_data = await db.get_profile(buyer_tg_id)
                                        pubg_id = u_data['pubg_id'] if u_data else 'Не указан'
                                        
                                        adm_kb = InlineKeyboardMarkup(inline_keyboard=[[
                                            InlineKeyboardButton(text="🚀 Выполнить", callback_data=f"adm_done_{buyer_tg_id}"),
                                            InlineKeyboardButton(text="❌ Отказ", callback_data=f"adm_no_{buyer_tg_id}")
                                        ]])
                                        
                                        await bot.send_message(
                                            config.ADMIN_ID,
                                            f"💰 **АВТО-ОПЛАТА ЧЕРЕЗ DA!**\n\n"
                                            f"💵 Сумма: {amount}₽\n"
                                            f"🎮 PUBG ID: `{pubg_id}`\n"
                                            f"👤 Юзер: {buyer_tg_id}\n"
                                            f"📝 Коммент: {comment}",
                                            reply_markup=adm_kb,
                                            parse_mode="Markdown"
                                        )
                                        
                                        await bot.send_message(
                                            buyer_tg_id,
                                            f"✅ **Оплата {amount}₽ успешно получена через сайт!**\n"
                                            f"Администратор уже переводит UC на ваш ID `{pubg_id}`. Ожидайте уведомления! 🕒",
                                            parse_mode="Markdown"
                                        )
                                    except Exception as e:
                                        logging.error(f"Ошибка обработки данных доната: {e}")
                                        
        except Exception as e:
            logging.error(f"Ошибка сокета DonationAlerts: {e}. Повтор через 10 сек...")
            await asyncio.sleep(10)

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
    if disc > 0: msg += f"\n🔥 Скидка: {disc}%"
    edit_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚙️ Изменить PUBG ID", callback_data="edit_id")]])
    await message.answer(msg, reply_markup=edit_kb, parse_mode="Markdown")

@dp.message(F.text == "🕒 График")
async def schedule(message: types.Message):
    await message.answer("🕒 **График (МСК):**\nБудни: 9:00 - 23:00 ✅\nВыходные:9:00 - 02:00 ✅\n\n*Может быть задержка до 30 минут!*", parse_mode="Markdown")

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
    
    comment_text = f"ЗАКАЗ #{uid}"
    da_link = f"{config.DA_DONATE_URL}?amount={total}&comment={comment_text}"
    
    pay_msg = (
        f"💳 **Оформление заказа**\n\n"
        f"💎 **Товар:** {cart['uc']} UC\n"
        f"💰 **К оплате:** {total}₽\n"
        f"🎮 **ID PUBG:** `{u_data['pubg_id']}`\n\n"
        f"🚀 **Способ 1 (Автоматический, БЕЗ ЧЕКОВ):**\n"
        f"Перейдите по кнопке ниже и оплатите картой. Бот сам увидит платеж!\n"
        f"⚠️ *ВАЖНО:* Не меняйте комментарий `ЗАКАЗ #{uid}` на сайте оплаты!\n\n"
        f"🏦 **Способ 2 (Вручную на карту):**\n"
        f"Переведите `{total}₽` на карту `4246 4100 8081 2321` (KERYMOVA NATALIA) и **пришлите скриншот чека** сюда в чат."
    )
    
    pay_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💳 Оплатить на сайте", url=da_link)
    ]])
    
    await callback.message.answer(pay_msg, reply_markup=pay_kb, parse_mode="Markdown", disable_web_page_preview=True)
    user_carts[uid] = {'uc': 0, 'price': 0, 'count': 0}

# --- АДМИНКА ---
@dp.message(F.photo)
async def handle_screenshot(message: types.Message):
    u_data = await db.get_profile(message.from_user.id)
    await message.answer("⏳ Чек получен! Ждем подтверждения.")
    adm_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Оплачено", callback_data=f"adm_ok_{message.from_user.id}"), 
        InlineKeyboardButton(text="❌ Отказ", callback_data=f"adm_no_{message.from_user.id}")
    ]])
    await bot.send_photo(
        config.ADMIN_ID, 
        message.photo[-1].file_id, 
        caption=f"💰 НОВЫЙ ЧЕК!\n🎮 ID: `{u_data['pubg_id'] if u_data else '???'}`\n👤 @{message.from_user.username}", 
        reply_markup=adm_kb
    )

@dp.callback_query(F.data.startswith("adm_"))
async def admin_decision(callback: types.CallbackQuery):
    await callback.answer()
    d = callback.data.split("_")
    action, uid = d[1], int(d[2])
    
    if action == "ok":
        await bot.send_message(
            uid, 
            "✅ **Ваша оплата подтверждена!**\n\nМожет быть задержка до 30 минут. Ожидайте уведомления! 🕒", 
            parse_mode="Markdown"
        )
        next_kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🚀 Выполнить", callback_data=f"adm_done_{uid}")
        ]])
        await callback.message.edit_caption(
            caption=f"{callback.message.caption}\n\n✅ ОПЛАТА ПРИНЯТА.", 
            reply_markup=next_kb
        )
        
    elif action == "done":
        await bot.send_message(
            uid, 
            "💎 UC зачислены на ваш аккаунт!\n\nПриятной игры! Пожалуйста, оставьте свой отзыв в нашем канале ⭐"
        )
        if callback.message.caption:
            await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n🏆 ВЫПОЛНЕНО")
        else:
            await callback.message.edit_text(text=f"{callback.message.text}\n\n🏆 ВЫПОЛНЕНО")
            
    elif action == "no":
        await bot.send_message(uid, "❌ Оплата отклонена. Свяжитесь с поддержкой.")
        if callback.message.caption:
            await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n❌ ОТКАЗАНО")
        else:
            await callback.message.edit_text(text=f"{callback.message.text}\n\n❌ ОТКАЗАНО")

# --- ВСЁ ОСТАЛЬНОЕ ---
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
    asyncio.create_task(donationalerts_alerts_handler())
    print("Запущено!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
