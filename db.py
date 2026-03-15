iimport aiosqlite
import os

# Путь к базе данных
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

async def db_start():
    async with aiosqlite.connect(DB_PATH) as db:
        # Создаем таблицу пользователей
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
        
        # Сразу создаем счетчик для лимитированного промокода
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
    p = promo_name.upper().strip()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # 1. Проверка: не использовал ли юзер ЭТОТ промокод раньше
        if await check_promo_used(user_id, p):
            return "❌ Вы уже активировали этот промокод!"

        # --- ЛОГИКА ПРОМОКОДОВ ---

        # AD1SKAUCBOT — Скидка 5% (одноразовая для всех)
        if p == "AD1SKAUCBOT":
            await db.execute('UPDATE users SET discount = 5 WHERE user_id = ?', (user_id,))
            await db.execute('INSERT INTO promo_history (user_id, promo_name) VALUES (?, ?)', (user_id, p))
            await db.commit()
            return "✅ Активирована постоянная скидка 5% для новых пользователей!"

        # LUXURY — 20 рублей (только первым 5-ти)
        if p == "LUXURY":
            async with db.execute('SELECT used_count FROM promo_limits WHERE promo_name = "LUXURY"') as cursor:
                row = await cursor.fetchone()
                if row and row['used_count'] >= 5:
                    return "❌ Лимит активаций промокода LUXURY (5 чел.) исчерпан!"
            
            # Начисляем 20 руб и обновляем счетчик лимита
            await db.execute('UPDATE users SET balance = balance + 20 WHERE user_id = ?', (user_id,))
            await db.execute('UPDATE promo_limits SET used_count = used_count + 1 WHERE promo_name = "LUXURY"')
            await db.execute('INSERT INTO promo_history (user_id, promo_name) VALUES (?, ?)', (user_id, p))
            await db.commit()
            return "🔥 Успех! Вам начислено 20₽ (вы в пятерке первых)!"

        return "❌ Такого промокода не существует."

async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT user_id FROM users') as cursor:
            rows = await cursor.fetchall()
            return [row for row in rows]
