import asyncio
import logging
from datetime import datetime
import pytz
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import config
import kb
import db

logging.basicConfig(level=logging.INFO)
bot = Bot(token=config.TOKEN)
dp = Dispatcher()

class Form(StatesGroup):
    waiting_for_pubg_id = State()

@dp.message(Command("start"))
async def start_command(message: types.Message):
    await db.register_user(message.from_user.id)
    await message.answer(f"Привет, {message.from_user.first_name}! 👋\nМагазин UC запущен.", reply_markup=kb.main_menu)

@dp.message(Command("send"))
async def cmd_send_all(message: types.Message, command: CommandObject):
    if message.from_user.id != config.ADMIN_ID: return 
    if not command.args: return await message.answer("Пример: `/send Текст`")
    users = await db.get_all_users()
    for uid in users:
        try:
            target = uid[0] if isinstance(uid, tuple) else uid
            await bot.send_message(target, command.args)
            await asyncio.sleep(0.05)
        except: pass
    await message.answer("✅ Рассылка завершена!")

@dp.message(F.text == "💎 Купить UC")
async def shop_menu(message: types.Message):
    await message.answer(
        "🛒 **Выберите необходимое количество UC!**\n\n"
        "❗ **ВАЖНО!** Начисление UC будет производиться **ПОСЛЕ 15:00 по МСК**!", 
        reply_markup=kb.buy_tokens, 
        parse_mode="Markdown"
    )

@dp.message(F.text == "👤 Профиль")
async def profile_menu(message: types.Message):
    user_data = await db.get_profile(message.from_user.id)
    if user_data:
        bal, pid = user_data["balance"], user_data["pubg_id"]
        edit_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚙️ Изменить PUBG ID", callback_data="edit_id")]])
        await message.answer(f"👤 **Профиль:**\n\n🆔 TG ID: `{message.from_user.id}`\n🎮 PUBG ID: `{pid}`\n💰 Баланс: {bal}₽", parse_mode="Markdown", reply_markup=edit_kb)

@dp.message(F.text == "🕒 График")
async def schedule(message: types.Message):
    await message.answer("🕒 **График (МСК):**\nПн-Пт: 15:00 - 23:00 ✅\nСб-Вс: 10:00 - 00:00 ✅\n\n*В школе с 08:00 до 15:00!*", parse_mode="Markdown")

@dp.message(F.text == "🎧 Поддержка")
async def support(message: types.Message):
    await message.answer(f"🎧 Связь: @{config.SUPPORT_LINK}")

@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: types.CallbackQuery):
    await callback.answer()
    # ИСПРАВЛЕНО: берем конкретное число, а не список
    amount = callback.data.split("_")[-1]
    user_data = await db.get_profile(callback.from_user.id)
    if user_data["pubg_id"] == "Не указан":
        return await callback.message.answer("⚠️ Сначала укажите PUBG ID в профиле!")

    now = datetime.now(pytz.timezone('Europe/Moscow')).hour
    warn = "\n\n⚠️ **Админ на учебе до 15:00 МСК!**" if 8 <= now < 15 else ""
    await callback.message.answer(
        f"💳 **Оплата: {amount} UC**\n\n"
        f"🏦 Карта (Беларусбанк): `4246 4100 8081 2321`\n"
        f"👤 Владелец: Наталья К.{warn}\n\n"
        "✅ Пришли скриншот чека сюда.", 
        parse_mode="Markdown"
    )

@dp.message(F.photo)
async def handle_screenshot(message: types.Message):
    user_data = await db.get_profile(message.from_user.id)
    p_id = user_data["pubg_id"]
    await message.answer("⏳ Чек получен! Ждите подтверждения.")
    
    # Кнопки: adm | действие | ID
    adm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Оплачено", callback_data=f"adm_yes_{message.from_user.id}")],
        [InlineKeyboardButton(text="❌ Отказ", callback_data=f"adm_no_{message.from_user.id}")]
    ])
    
    # ИСПРАВЛЕНО: Убран parse_mode, чтобы символы в username или ID не ломали отправку
    await bot.send_photo(
        config.ADMIN_ID, 
        message.photo[-1].file_id, 
        caption=f"💰 НОВЫЙ ЧЕК!\n🎮 PUBG ID: {p_id}\n👤 От: @{message.from_user.username}\n🆔 ID: {message.from_user.id}", 
        reply_markup=adm_kb
    )

@dp.callback_query(F.data.startswith("adm_"))
async def admin_decision(callback: types.CallbackQuery):
    if callback.from_user.id != config.ADMIN_ID: return
    
    data = callback.data.split("_")
    action = data[1]  # yes или no
    user_id = int(data[2])  # ID юзера

    if action == "yes":
        await bot.send_message(user_id, "✅ **Ваша оплата подтверждена!**\nUC скоро будут зачислены.")
        await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n✅ СТАТУС: ОДОБРЕНО")
    else:
        await bot.send_message(user_id, "❌ **Оплата отклонена.**\nСвяжитесь с поддержкой.")
        await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n❌ СТАТУС: ОТКЛОНЕНО")
    
    await callback.answer()

@dp.callback_query(F.data == "edit_id")
async def edit_id(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("⌨️ Введите цифровой **PUBG ID**:")
    await state.set_state(Form.waiting_for_pubg_id)

@dp.message(Form.waiting_for_pubg_id)
async def save_id(message: types.Message, state: FSMContext):
    if message.text.isdigit() and 7 <= len(message.text) <= 11:
        await db.update_pubg_id(message.from_user.id, message.text)
        await state.clear()
        await message.answer(f"✅ ID `{message.text}` сохранен!", reply_markup=kb.main_menu)
    else: 
        await message.answer("❌ Введите корректный ID (7-11 цифр).")

async def main():
    await db.db_start()
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
