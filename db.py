import aiosqlite

async def db_start():
    async with aiosqlite.connect('database.db') as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER DEFAULT 0,
                pubg_id TEXT DEFAULT "Не указан"
            )
        ''')
        await db.commit()

async def register_user(user_id):
    async with aiosqlite.connect('database.db') as db:
        async with db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)) as cursor:
            user = await cursor.fetchone()
            if not user:
                await db.execute('INSERT INTO users (user_id) VALUES (?)', (user_id,))
                await db.commit()

async def get_profile(user_id):
    async with aiosqlite.connect('database.db') as db:
        async with db.execute('SELECT balance, pubg_id FROM users WHERE user_id = ?', (user_id,)) as cursor:
            return await cursor.fetchone()

async def update_pubg_id(user_id, pubg_id):
    async with aiosqlite.connect('database.db') as db:
        await db.execute('UPDATE users SET pubg_id = ? WHERE user_id = ?', (pubg_id, user_id))
        await db.commit()
