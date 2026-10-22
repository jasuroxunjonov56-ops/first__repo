
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
            CREATE TABLE IF NOT EXISTS worker_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                link_token TEXT NOT NULL UNIQUE,
                telegram_id INTEGER UNIQUE,
                active INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS web_sessions (
                token TEXT PRIMARY KEY,
                account_id INTEGER,
                role TEXT NOT NULL,
                username TEXT NOT NULL,
                created_at INTEGER NOT NULL
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

        # Safe migrations for existing deployments.
        order_columns = {row[1] for row in await (await db.execute("PRAGMA table_info(orders)")).fetchall()}
        if "contact" not in order_columns:
            await db.execute("ALTER TABLE orders ADD COLUMN contact TEXT")
        if "source" not in order_columns:
            await db.execute("ALTER TABLE orders ADD COLUMN source TEXT DEFAULT 'telegram'")

        await db.commit()


async def link_worker_account(link_token, telegram_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, active FROM worker_accounts WHERE link_token = ?",
            (link_token,),
        )
        account = await cursor.fetchone()
        if account is None:
            return None
        cursor = await db.execute(
            "SELECT telegram_id FROM worker_accounts WHERE id = ?",
            (account["id"],),
        )
        existing = await cursor.fetchone()
        if existing and existing[0] not in (None, telegram_id):
            return None
        cursor = await db.execute(
            "SELECT id FROM worker_accounts WHERE telegram_id = ? AND id != ?",
            (telegram_id, account["id"]),
        )
        already_linked = await cursor.fetchone()
        if already_linked:
            return None
        await db.execute(
            "UPDATE worker_accounts SET telegram_id = ? WHERE id = ?",
            (telegram_id, account["id"]),
        )
        await db.execute(
            "INSERT INTO workers (user_id, active) VALUES (?, 0) ON CONFLICT(user_id) DO NOTHING",
            (telegram_id,),
        )
        await db.commit()
        return {"id": account["id"], "active": bool(account["active"])}


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

        await db.execute("UPDATE worker_accounts SET active = 1 WHERE telegram_id = ?", (user_id,))

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


async def get_order_details(order_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
