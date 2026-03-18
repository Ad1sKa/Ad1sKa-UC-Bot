import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiocryptopay import AioCryptoPay, Networks

import config
import kb
import db

# Логи для контроля работы в панели Render
logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.TOKEN)
dp = Dispatcher()

# Глобальный объект для Crypto Pay
crypto = None

# --- КОМАНДЫ ---
@dp.message(Command("start"))
async def start(message: types.Message):
    await db.register_user(message.from_user.id)
    await message.answer(f"Привет! Это магазин UC. Выбирай пакет в меню.", reply_markup=kb.main_menu)

@dp.message(F.text == "👤 Профиль")
async def profile(message: types.Message):
    user_data = await db.get_profile(message.from_user.id)
    if user_data:
        text = (f"👤 Ваш профиль:\n"
                f"🆔 ID: {message.from_user.id}\n"
                f"💰 Баланс: {user_data['balance']}₽\n"
                f"🎮 PUBG ID: {user_data['pubg_id']}")
    else:
        text = "Ошибка профиля. Нажми /start"
    await message.answer(text)

@dp.message(F.text == "💎 Купить UC")
async def shop(message: types.Message):
    await message.answer("Выберите количество UC:", reply_markup=kb.buy_tokens)

# --- ПЛАТЕЖИ ---
@dp.callback_query(F.data.startswith("buy_"))
async def create_order(callback: types.CallbackQuery):
    global crypto
    data = callback.data.split("_")
    uc_amount = data[1]
    price_rub = int(data[2])
    
    # Конвертация (курс ~95)
    amount_usd = round(price_rub / 95, 2)
    
    # Создаем инвойс в CryptoBot
    invoice = await crypto.create_invoice(asset='USDT', amount=amount_usd)
    
    await callback.message.edit_text(
        f"🛒 Заказ: {uc_amount} UC\n"
        f"💵 Цена: {price_rub}₽ (~{amount_usd} USDT)\n\n"
        f"Оплатите по кнопке ниже:",
        reply_markup=kb.payment_kb(invoice.bot_invoice_url, invoice.invoice_id)
    )

@dp.callback_query(F.data.startswith("check_"))
async def check_payment(callback: types.CallbackQuery):
    global crypto
    invoice_id = int(callback.data.split("_")[1])
    
    invoices = await crypto.get_invoices(invoice_ids=invoice_id)
    
    if invoices and invoices.status == 'paid':
        await callback.message.edit_text("✅ Оплата прошла! Админ скоро свяжется с вами.")
        await bot.send_message(config.ADMIN_ID, f"💰 Оплачен заказ {invoice_id} от юзера {callback.from_user.id}")
    else:
        await callback.answer("❌ Оплата не найдена.", show_alert=True)

# --- ОСТАЛЬНОЕ ---
@dp.message(F.text == "🎟 Промокоды и Скидки")
async def promos(message: types.Message):
    await message.answer("Тут ваши скидки:", reply_markup=kb.social_kb)

@dp.message(F.text == "🎧 Поддержка")
async def support(message: types.Message):
    await message.answer(f"Связь: @{config.SUPPORT_LINK}")

# --- ЗАПУСК ---
async def main():
    global crypto
    # Инициализация внутри цикла событий
    crypto = AioCryptoPay(token=config.CRYPTO_PAY_TOKEN, network=Networks.MAIN_NET)
    
    await db.db_start()
    logging.info("Бот успешно запущен в режиме Background Worker")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
