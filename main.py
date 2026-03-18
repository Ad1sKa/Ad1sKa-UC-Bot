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

bot = Bot(token=config.TOKEN)
dp = Dispatcher()

# Инициализация оплаты (используем тестовую сеть или основную)
crypto = AioCryptoPay(token=config.CRYPTO_PAY_TOKEN, network=Networks.MAIN_NET)

@dp.message(Command("start"))
async def start(message: types.Message):
    await db.register_user(message.from_user.id)
    await message.answer(f"Привет! Добро пожаловать в магазин UC.", reply_markup=kb.main_menu)

@dp.message(F.text == "💎 Купить UC")
async def shop(message: types.Message):
    await message.answer("Выберите нужное количество UC:", reply_markup=kb.buy_tokens)

# Обработка выбора товара
@dp.callback_query(F.data.startswith("buy_"))
async def create_invoice(callback: types.CallbackQuery):
    data = callback.data.split("_")
    uc_amount = data[1]
    price_rub = int(data[2])
    
    # Конвертируем рубли в доллары (примерный курс 95, CryptoBot любит USD/USDT)
    amount_usd = round(price_rub / 95, 2)
    
    # Создаем счет в CryptoBot
    invoice = await crypto.create_invoice(asset='USDT', amount=amount_usd)
    
    await callback.message.edit_text(
        f"🛒 Заказ: {uc_amount} UC\n"
        f"💵 Сумма: {price_rub}₽ (~{amount_usd} USDT)\n\n"
        f"Оплата принимается через CryptoBot. Нажмите кнопку ниже:",
        reply_markup=kb.payment_kb(invoice.bot_invoice_url, invoice.invoice_id)
    )

# Проверка оплаты
@dp.callback_query(F.data.startswith("check_"))
async def check_pay(callback: types.CallbackQuery):
    invoice_id = int(callback.data.split("_")[1])
    
    # Получаем данные о счете
    invoices = await crypto.get_invoices(invoice_ids=invoice_id)
    
    # Если список не пуст и статус 'paid'
    if invoices and invoices.status == 'paid':
        await callback.message.delete()
        await callback.message.answer(f"✅ Оплата подтверждена! Спасибо за покупку.\n"
                                     f"Администратор @{config.SUPPORT_LINK} свяжется с вами для начисления UC.")
        
        # Уведомление админу
        await bot.send_message(config.ADMIN_ID, f"🔔 Новый заказ оплачен!\nID: {callback.from_user.id}\nInvoice ID: {invoice_id}")
    else:
        await callback.answer("❌ Оплата еще не найдена. Попробуйте через минуту.", show_alert=True)

async def on_startup():
    await db.db_start()

async def main():
    dp.startup.register(on_startup)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот выключен")
