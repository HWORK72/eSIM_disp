import asyncpg
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Глобальный пул соединений с базой данных
pool = None


async def init_db() -> None:
    global pool
    db_url = os.getenv('DATABASE_URL')

    if not db_url:
        logging.error("DATABASE_URL не найден в .env!")
        return

    try:
        # Создаем пул соединений (это в разы быстрее)
        pool = await asyncpg.create_pool(db_url)

        async with pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT UNIQUE NOT NULL,
                    role VARCHAR(50) DEFAULT 'supplier', 
                    balance NUMERIC(10, 2) DEFAULT 0.0,
                    referrer_id BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (referrer_id) REFERENCES users (telegram_id) ON DELETE SET NULL
                )
            ''')

            await conn.execute('''
                CREATE TABLE IF NOT EXISTS operators (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    price_hold NUMERIC(10, 2) NOT NULL,
                    price_no_hold NUMERIC(10, 2) NOT NULL,
                    is_active INTEGER DEFAULT 1
                )
            ''')

            await conn.execute('''
                CREATE TABLE IF NOT EXISTS client_groups (
                    id SERIAL PRIMARY KEY,
                    chat_id BIGINT UNIQUE NOT NULL,
                    name VARCHAR(255),
                    added_by BIGINT,
                    FOREIGN KEY (added_by) REFERENCES users (telegram_id) ON DELETE SET NULL
                )
            ''')

            await conn.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    id SERIAL PRIMARY KEY,
                    supplier_id BIGINT NOT NULL,
                    operator_id INTEGER NOT NULL,
                    phone_number VARCHAR(50) NOT NULL, 
                    qr_data TEXT NOT NULL,
                    status VARCHAR(50) DEFAULT 'pending', 
                    client_id BIGINT,
                    group_id BIGINT,
                    mode VARCHAR(50), 
                    hold_end_time TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (supplier_id) REFERENCES users (telegram_id),
                    FOREIGN KEY (operator_id) REFERENCES operators (id),
                    FOREIGN KEY (client_id) REFERENCES users (telegram_id),
                    FOREIGN KEY (group_id) REFERENCES client_groups (chat_id)
                )
            ''')

            await conn.execute('''
                CREATE TABLE IF NOT EXISTS withdrawals (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    amount NUMERIC(10, 2) NOT NULL,
                    wallet TEXT NOT NULL,
                    status VARCHAR(50) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (telegram_id)
                )
            ''')

            await conn.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key VARCHAR(255) PRIMARY KEY,
                    value TEXT NOT NULL
                )
            ''')

            await conn.execute('''
                INSERT INTO settings (key, value) VALUES ('ref_percent', '5.0')
                ON CONFLICT (key) DO NOTHING
            ''')

            logging.info("База данных PostgreSQL успешно инициализирована.")

    except Exception as e:
        logging.error(f"Произошла ошибка при инициализации PostgreSQL: {e}")