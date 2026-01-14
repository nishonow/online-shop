import aiosqlite
import datetime

# Database file path
DB_PATH = "db/bot.db"

# Initialize database
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Create users table
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            name TEXT NOT NULL,
            username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Create products table
        await db.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL DEFAULT 0,
            category TEXT,
            image TEXT
        )
        """)

        # Create cart table
        await db.execute("""
        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(telegram_id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
        """)

        await db.commit()


async def add_user(telegram_id, name, username):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO users (telegram_id, name, username) VALUES (?, ?, ?)", (telegram_id, name, username))
        await db.commit()

async def user_exists(telegram_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT 1 FROM users WHERE telegram_id = ?", (telegram_id,))
        exists = await cursor.fetchone()
        return exists is not None

# COMMANDS FOR ONLINE SHOP BOT

async def add_product(name, description, price, category, image_url):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO products (name, description, price, category, image) VALUES (?, ?, ?, ?, ?)", (name, description, price, category, image_url))
        await db.commit()

async def delete_product(product_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM products WHERE id = ?", (product_id,))
        await db.commit()

async def get_smartphones():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT * FROM products WHERE category = ?", ('Smartphones',))
        products = await cursor.fetchall()
        return products

async def get_accessories():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT * FROM products WHERE category = ?", ('Accessories',))
        products = await cursor.fetchall()
        return products

async def add_to_cart(user_id: int, product_id: int, quantity: int = 1):
    async with aiosqlite.connect(DB_PATH) as db:
        # Check if product is already in cart
        cursor = await db.execute(
            "SELECT quantity FROM cart WHERE user_id = ? AND product_id = ?",
            (user_id, product_id)
        )
        result = await cursor.fetchone()
        if result:
            new_quantity = result[0] + quantity
            await db.execute(
                "UPDATE cart SET quantity = ? WHERE user_id = ? AND product_id = ?",
                (new_quantity, user_id, product_id)
            )
        else:
            await db.execute(
                "INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)",
                (user_id, product_id, quantity)
            )
        await db.commit()

async def get_cart(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT p.id, p.name, p.description, p.price, p.category, p.image, c.quantity
            FROM cart c
            JOIN products p ON c.product_id = p.id
            WHERE c.user_id = ?
        """, (user_id,))
        return await cursor.fetchall()

async def clear_cart(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        await db.commit()


# ADMIN COMMANDS

async def get_user_ids():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT telegram_id FROM users") as cursor:
            telegram_ids = [row[0] for row in await cursor.fetchall()]
    return telegram_ids

async def count_users():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            total_users = (await cursor.fetchone())[0]
    return total_users

# Count users who joined in the past 24 hours
async def count_new_users_last_24_hours():
    past_24_hours = datetime.datetime.now() - datetime.timedelta(hours=24)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users WHERE created_at >= ?", (past_24_hours,)) as cursor:
            new_users = (await cursor.fetchone())[0]
    return new_users

async def get_all_users(page=0, per_page=20):
    async with aiosqlite.connect(DB_PATH) as db:
        offset = page * per_page
        cursor = await db.execute(
            "SELECT telegram_id, name FROM users LIMIT ? OFFSET ?",
            (per_page, offset)
        )
        users = await cursor.fetchall()
        return users

async def on_startup():
    await init_db()