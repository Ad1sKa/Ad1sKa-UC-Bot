import asyncio
import logging
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

# Объявляем переменную для крипто-платежей (инициализируем в main)
crypto = None

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
    # Разбираем callback: buy_60_80 -> ['buy', '60', '80']
    data = callback.data.split("_")
    uc_amount = data[1]
    price_rub = int(data[2])
    
    # Примерный курс RUB -> USDT (95)
    amount_usd = round(price_rub / 95, 2)
    
    # Создаем инвойс в CryptoBot
    invoice = await crypto.create_invoice(asset='USDT', amount=amount_usd)
    
    await callback.message.edit_text(
        f"🛒 Оформление заказа:\n"
        f"📦 Товар: {uc_amount} UC\n"
        f"💵 Сумма: {price_rub}₽ (~{amount_usd} USDT)\n\n"
        f"Оплатите по кнопке ниже и нажмите 'Проверить'",
        reply_markup=kb.payment_kb(invoice.bot_invoice_url, invoice.invoice_id)
    )

@dp.callback_query(F.data.startswith("check_"))
async def check_payment(callback: types.CallbackQuery):
    global crypto
    invoice_id = int(callback.data.split("_")[1])
    
    # Запрашиваем счета по ID
    invoices = await crypto.get_invoices(invoice_ids=invoice_id)
    
    # Проверяем статус (статус может быть в списке или объекте в зависимости от версии либы)
    if invoices and invoices.status == 'paid':
        await callback.message.edit_text("✅ Оплата получена! В ближайшее время UC будут зачислены.")
        # Уведомление тебе как админу
        await bot.send_message(config.ADMIN_ID, f"🔔 ЗАКАЗ ОПЛАЧЕН!\nЮзер: {callback.from_user.id}\nInvoice ID: {invoice_id}")
    else:
        await callback.answer("❌ Оплата еще не поступила. Попробуйте через минуту.", show_alert=True)

# --- ДОПОЛНИТЕЛЬНЫЕ КНОПКИ ---
@dp.message(F.text == "🎟 Промокоды и Скидки")
async def promos(message: types.Message):
    await message.answer("Раздел промокодов:", reply_markup=kb.social_kb)

@dp.message(F.text == "🎧 Поддержка")
async def support(message: types.Message):
    await message.answer(f"По всем вопросам пишите: @{config.SUPPORT_LINK}")

@dp.message(F.text == "🕒 График")
async def schedule(message: types.Message):
    await message.answer("🕒 Мы работаем ежедневно с 10:00 до 22:00 по МСК.")

# --- ЗАПУСК ---
async def main():
    global crypto
    # Инициализируем CryptoPay внутри асинхронного цикла
    crypto = AioCryptoPay(token=config.CRYPTO_PAY_TOKEN, network=Networks.MAIN_NET)
    
    # Запуск БД
    await db.db_start()
    
    # Запуск поллинга
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен")
