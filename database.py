
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

        await db.execute("""
            CREATE TABLE IF NOT EXISTS workers (
                user_id INTEGER PRIMARY KEY,
                active INTEGER NOT NULL DEFAULT 0
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS payment_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                transaction_id TEXT NOT NULL UNIQUE,
                receipt_file_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.commit()


async def add_order(student_id, description, price):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            INSERT INTO orders (student_id, description, price)
            VALUES (?, ?, ?)
        """, (student_id, description, price))

        await db.commit()
        return cursor.lastrowid


async def get_open_orders():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM orders
            WHERE status = 'open'
            ORDER BY id DESC
        """)
        return await cursor.fetchall()


async def take_order(order_id, worker_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            UPDATE orders
            SET status = 'assigned', worker_id = ?
            WHERE id = ? AND status = 'open'
        """, (worker_id, order_id))

        await db.commit()
        return cursor.rowcount > 0


async def get_all_orders():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM orders
            ORDER BY id DESC
            LIMIT 50
        """)
        return await cursor.fetchall()


async def is_worker_active(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT active FROM workers WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        return row is not None and row[0] == 1



async def create_payment_request(user_id, transaction_id, receipt_file_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """
            INSERT OR IGNORE INTO payment_requests
            (user_id, transaction_id, receipt_file_id)
            VALUES (?, ?, ?)
            """,
            (user_id, transaction_id, receipt_file_id),
        )

        if cursor.rowcount == 0:
            await db.commit()
            return None

        request_id = cursor.lastrowid

        await db.execute(
            """
            INSERT OR IGNORE INTO workers (user_id, active)
            VALUES (?, 0)
            """,
            (user_id,),
        )

        await db.commit()
        return request_id



async def get_pending_payment_requests():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM payment_requests
            WHERE status = 'pending'
            ORDER BY id ASC
        """)
        return await cursor.fetchall()


async def approve_payment_request(request_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("BEGIN IMMEDIATE")

        cursor = await db.execute("""
            SELECT user_id FROM payment_requests
            WHERE id = ? AND status = 'pending'
        """, (request_id,))
        row = await cursor.fetchone()

        if row is None:
            await db.rollback()
            return None

        user_id = row[0]

        await db.execute("""
            UPDATE payment_requests
            SET status = 'approved'
            WHERE id = ? AND status = 'pending'
        """, (request_id,))

        await db.execute("""
            INSERT INTO workers (user_id, active)
            VALUES (?, 1)
            ON CONFLICT(user_id) DO UPDATE SET active = 1
        """, (user_id,))

        await db.commit()
        return user_id


async def reject_payment_request(request_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            UPDATE payment_requests
            SET status = 'rejected'
            WHERE id = ? AND status = 'pending'
        """, (request_id,))

        await db.commit()
        return cursor.rowcount > 0
