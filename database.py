import aiosqlite
import logging

DB_NAME = 'leads.db'

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                email TEXT,
                niche TEXT,
                location TEXT,
                status TEXT DEFAULT 'pending'  -- 'pending', 'sent'
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        await db.commit()
        logging.info("Database initialized.")

async def insert_lead(name, email, niche, location):
    async with aiosqlite.connect(DB_NAME) as db:
        # Check if email already exists
        cursor = await db.execute('SELECT 1 FROM leads WHERE email = ?', (email,))
        if await cursor.fetchone():
            return False

        await db.execute(
            'INSERT INTO leads (name, email, niche, location) VALUES (?, ?, ?, ?)',
            (name, email, niche, location)
        )
        await db.commit()
        return True

async def get_pending_leads(limit=5):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM leads WHERE status = 'pending' LIMIT ?", (limit,))
        return await cursor.fetchall()

async def mark_lead_sent(lead_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE leads SET status = 'sent' WHERE id = ?", (lead_id,))
        await db.commit()

async def save_setting(key, value):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        ''', (key, value))
        await db.commit()

async def get_setting(key):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute('SELECT value FROM settings WHERE key = ?', (key,))
        row = await cursor.fetchone()
        return row[0] if row else None
