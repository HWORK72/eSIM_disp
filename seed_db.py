import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()


async def seed_operators():
    """Скрипт для первичного заполнения прайс-листа в PostgreSQL."""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("Ошибка: DATABASE_URL не найден в .env")
        return

    operators_data = [
        ("МТС ГК", 18.00, 14.00),
        ("МТС Салон", 18.00, 18.00),
        ("Билайн ГК", 17.00, 14.00),
        ("Билайн Салон", 17.00, 16.00),
        ("Tele2 ГК", 0.00, 13.00),
        ("Tele2 Салон", 0.00, 15.00),
        ("Сбер", 0.00, 12.00),
        ("Мегафон", 0.00, 10.00),
        ("ВТБ", 0.00, 20.00),
        ("Газпром", 0.00, 20.00),
        ("Миранда", 0.00, 15.00),
        ("Добросвязь", 0.00, 6.00)
    ]

    try:
        # Подключаемся к Postgres напрямую (без пула, так как это скрипт на 1 раз)
        conn = await asyncpg.connect(db_url)
        count = await conn.fetchval("SELECT COUNT(*) FROM operators")

        if count == 0:
            print("Начинаю загрузку данных...")
            await conn.executemany(
                "INSERT INTO operators (name, price_hold, price_no_hold) VALUES ($1, $2, $3)",
                operators_data
            )
            print("Успешно! Все операторы из ТЗ добавлены в базу данных.")
        else:
            print("В таблице уже есть данные. Заполнение отменено.")

        await conn.close()
    except Exception as e:
        print(f"Ошибка при загрузке: {e}")


if __name__ == '__main__':
    asyncio.run(seed_operators())