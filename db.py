import aiosqlite
import os

# Путь к базе данных
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

async def db_start():
    async with aiosqlite.connect(DB_PATH) as db:
        # Создаем таблицу пользователей с колонкой discount
        await db.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            pubg_id TEXT DEFAULT "Не указан",
            discount INTEGER DEFAULT 0)''')
        
        # Таблица истории промокодов
        await db.execute('''CREATE TABLE IF NOT EXISTS promo_history (
            user_id INTEGER,
            promo_name TEXT)''')
        
        # Таблица лимитов промокодов
        await db.execute('''CREATE TABLE IF NOT EXISTS promo_limits (
            promo_name TEXT PRIMARY KEY,
            used_count INTEGER DEFAULT 0)''')
        
        await db.execute('INSERT OR IGNORE INTO promo_limits (promo_name, used_count) VALUES ("LUXURY", 0)')
        await db.commit()

async def register_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)) as cursor:
            if not await cursor.fetchone():
                await db.execute('INSERT INTO users (user_id) VALUES (?)', (user_id,))
                await db.commit()

async def get_profile(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT balance, pubg_id, discount FROM users WHERE user_id = ?', (user_id,)) as cursor:
            return await cursor.fetchone()

async def update_pubg_id(user_id, pubg_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('UPDATE users SET pubg_id = ? WHERE user_id = ?', (pubg_id, user_id))
        await db.commit()

async def check_promo_used(user_id, promo_name):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT * FROM promo_history WHERE user_id = ? AND promo_name = ?', (user_id, promo_name)) as cursor:
            return await cursor.fetchone() is not None

async def activate_promo_db(user_id, promo_name):
    promo_name = promo_name.upper()
    async with aiosqlite.connect(DB_PATH) as db:
        if promo_name == "NEWBRO1":
            await db.execute('UPDATE users SET balance = balance + 30 WHERE user_id = ?', (user_id,))
            await db.execute('INSERT INTO promo_history (user_id, promo_name) VALUES (?, ?)', (user_id, promo_name))
            await db.commit()
            return "✅ Начислено 30₽ на баланс!"
        if promo_name == "AD1SKAUC":
            await db.execute('UPDATE users SET discount = 5 WHERE user_id = ?', (user_id,))
            await db.execute('INSERT INTO promo_history (user_id, promo_name) VALUES (?, ?)', (user_id, promo_name))
            await db.commit()
            return "✅ Активирована постоянная скидка 5%!"
        if promo_name == "LUXURY":
            async with db.execute('SELECT used_count FROM promo_limits WHERE promo_name = "LUXURY"') as cursor:
                row = await cursor.fetchone()
                if row and row['used_count'] >= 5:
                    return "❌ Лимит этого промокода исчерпан!"
            await db.execute('UPDATE users SET balance = balance + 50 WHERE user_id = ?', (user_id,))
            await db.execute('UPDATE promo_limits SET used_count = used_count + 1 WHERE promo_name = "LUXURY"')
            await db.execute('INSERT INTO promo_history (user_id, promo_name) VALUES (?, ?)', (user_id, promo_name))
            await db.commit()
            return "✅ Начислено 50₽!"
        return "❌ Неверный промокод"

async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT user_id FROM users') as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
