import asyncio
import logging
import os
from aiohttp import web  # Нужно добавить в requirements.txt
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiocryptopay import AioCryptoPay, Networks

import config
import kb
import db

# Настройка логов
logging.basicConfig(level=logging.INFO)

# Инициализируем бота и диспетчер
bot = Bot(token=config.TOKEN)
dp = Dispatcher()

# Глобальная переменная для оплаты
crypto = None

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER (чтобы не было ошибки портов) ---
async def handle(request):
    return web.Response(text="Bot is alive!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    # Render дает порт 10000 по умолчанию
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Web server started on port {port}")

# --- БАЗОВЫЕ КОМАНДЫ ---
@dp.message(Command("start"))
async def start(message: types.Message):
    await db.register_user(message.from_user.id)
    await message.answer(f"Привет! Добро пожаловать в магазин UC.", reply_markup=kb.main_menu)

@dp.message(F.text == "👤 Профиль")
async def profile(message: types.Message):
    user_data = await db.get_profile(message.from_user.id)
    if user_data:
        text = (f"👤 Ваш профиль:\n"
                f"🆔 ID: {message.from_user.id}\n"
                f"💰 Баланс: {user_data['balance']}₽\n"
                f"🎮 PUBG ID: {user_data['pubg_id']}")
    else:
        text = "Ошибка загрузки профиля. Попробуйте /start"
    await message.answer(text)

@dp.message(F.text == "💎 Купить UC")
async def shop(message: types.Message):
    await message.answer("Выберите пакет UC для покупки:", reply_markup=kb.buy_tokens)

# --- ЛОГИКА ОПЛАТЫ ---
@dp.callback_query(F.data.startswith("buy_"))
async def create_order(callback: types.CallbackQuery):
    global crypto
    data = callback.data.split("_")
    uc_amount = data[1]
    price_rub = int(data[2])
    
    # Курс RUB -> USDT
    amount_usd = round(price_rub / 95, 2)
    
    # Создаем инвойс
    invoice = await crypto.create_invoice(asset='USDT', amount=amount_usd)
    
    await callback.message.edit_text(
        f"🛒 Оформление заказа:\n"
        f"📦 Товар: {uc_amount} UC\n"
        f"💵 Сумма: {price_rub}₽ (~{amount_usd} USDT)\n\n"
        f"Оплатите и нажмите 'Проверить'",
        reply_markup=kb.payment_kb(invoice.bot_invoice_url, invoice.invoice_id)
    )

@dp.callback_query(F.data.startswith("check_"))
async def check_payment(callback: types.CallbackQuery):
    global crypto
    invoice_id = int(callback.data.split("_")[1])
    
    invoices = await crypto.get_invoices(invoice_ids=invoice_id)
    
    if invoices and invoices.status == 'paid':
        await callback.message.edit_text("✅ Оплата получена! Ожидайте начисления.")
        await bot.send_message(config.ADMIN_ID, f"🔔 ОПЛАЧЕНО!\nЮзер: {callback.from_user.id}\nИнвойс: {invoice_id}")
    else:
        await callback.answer("❌ Оплата не найдена.", show_alert=True)

# --- ПРОЧИЕ КНОПКИ ---
@dp.message(F.text == "🎟 Промокоды и Скидки")
async def promos(message: types.Message):
    await message.answer("Раздел промокодов:", reply_markup=kb.social_kb)

@dp.message(F.text == "🎧 Поддержка")
async def support(message: types.Message):
    await message.answer(f"По всем вопросам пишите: @{config.SUPPORT_LINK}")

# --- ЗАПУСК ---
async def main():
    global crypto
    # 1. Запускаем "затычку" для Render
    asyncio.create_task(start_web_server())
    
    # 2. Инициализируем оплату
    crypto = AioCryptoPay(token=config.CRYPTO_PAY_TOKEN, network=Networks.MAIN_NET)
    
    # 3. База и Бот
    await db.db_start()
    print("Бот запущен и порт открыт!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен")
