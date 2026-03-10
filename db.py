import aiosqlite
import os

# Автоматический выбор пути: /tmp для Render, локально для Windows
if os.path.exists('/tmp'):
    DB_PATH = "/tmp/database.db"
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, "database.db")

async def db_start():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER DEFAULT 0,
                pubg_id TEXT DEFAULT "Не указан"
            )
        ''')
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
        async with db.execute('SELECT balance, pubg_id FROM users WHERE user_id = ?', (user_id,)) as cursor:
            return await cursor.fetchone()

async def update_pubg_id(user_id, pubg_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('UPDATE users SET pubg_id = ? WHERE user_id = ?', (pubg_id, user_id))
        await db.commit()

async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT user_id FROM users') as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
