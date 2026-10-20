
import aiosqlite
from config import DB_NAME


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                price INTEGER NOT NULL,
                status TEXT DEFAULT 'open',
                worker_id INTEGER
            )
        """)

        await db.commit()


async def add_order(student_id, description, price):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """
            INSERT INTO orders
            (student_id, description, price)
            VALUES (?, ?, ?)
            """,
            (student_id, description, price),
        )

        await db.commit()
        return cursor.lastrowid


async def get_open_orders():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT * FROM orders
            WHERE status = 'open'
            ORDER BY id DESC
            """
        )

        return await cursor.fetchall()


async def take_order(order_id, worker_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """
            UPDATE orders
            SET status = 'assigned', worker_id = ?
            WHERE id = ? AND status = 'open'
            """,
            (worker_id, order_id),
        )

        await db.commit()
        return cursor.rowcount > 0


async def get_all_orders():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT * FROM orders
            ORDER BY id DESC
            LIMIT 50
            """
        )

        return await cursor.fetchall()
