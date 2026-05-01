import database
from datetime import datetime, timedelta, timezone

MSK = timezone(timedelta(hours=3))


async def get_user(telegram_id: int):
    async with database.pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM users WHERE telegram_id = $1", telegram_id)


async def add_user(telegram_id: int, referrer_id: int = None):
    async with database.pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO users (telegram_id, referrer_id) VALUES ($1, $2) ON CONFLICT (telegram_id) DO NOTHING",
            telegram_id, referrer_id
        )


async def get_all_operators():
    async with database.pool.acquire() as conn:
        return await conn.fetch("SELECT * FROM operators WHERE is_active = 1")


async def get_queue_stats():
    async with database.pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT operator_id, mode, COUNT(*) FROM orders WHERE status = 'pending' AND mode IS NOT NULL GROUP BY operator_id, mode")
        stats = {}
        for row in rows:
            op_id, mode, count = row['operator_id'], row['mode'], row['count']
            if op_id not in stats: stats[op_id] = {'hold': 0, 'no_hold': 0}
            stats[op_id][mode] = count
        return stats


async def get_setting(key: str) -> str:
    async with database.pool.acquire() as conn:
        return await conn.fetchval("SELECT value FROM settings WHERE key = $1", key)


async def count_referrals(user_id: int) -> int:
    async with database.pool.acquire() as conn:
        return await conn.fetchval("SELECT COUNT(*) FROM users WHERE referrer_id = $1", user_id)


async def add_order(supplier_id: int, operator_id: int, phone_number: str, qr_data: str, mode: str):
    async with database.pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO orders (supplier_id, operator_id, phone_number, qr_data, mode) VALUES ($1, $2, $3, $4, $5)",
            supplier_id, operator_id, phone_number, qr_data, mode
        )


async def get_supplier_stats(supplier_id: int):
    async with database.pool.acquire() as conn:
        rows = await conn.fetch("SELECT status, COUNT(*) FROM orders WHERE supplier_id = $1 GROUP BY status",
                                supplier_id)
        return {row['status']: row['count'] for row in rows}


async def create_withdrawal(user_id: int, amount: float, wallet: str):
    async with database.pool.acquire() as conn:
        await conn.execute("UPDATE users SET balance = balance - $1 WHERE telegram_id = $2", amount, user_id)
        await conn.execute("INSERT INTO withdrawals (user_id, amount, wallet) VALUES ($1, $2, $3)", user_id, amount,
                           wallet)


async def register_group(chat_id: int, title: str, admin_id: int):
    async with database.pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO client_groups (chat_id, name, added_by) VALUES ($1, $2, $3) ON CONFLICT (chat_id) DO NOTHING",
            chat_id, title, admin_id
        )


async def get_pending_orders(limit: int):
    async with database.pool.acquire() as conn:
        return await conn.fetch('''
            SELECT o.id, o.phone_number, o.qr_data, o.mode, op.name as op_name
            FROM orders o JOIN operators op ON o.operator_id = op.id
            WHERE o.status = 'pending' ORDER BY o.created_at ASC LIMIT $1
        ''', limit)


async def update_order_status(order_id: int, status: str, group_id: int = None):
    async with database.pool.acquire() as conn:
        if group_id:
            await conn.execute("UPDATE orders SET status = $1, group_id = $2 WHERE id = $3", status, group_id, order_id)
        else:
            await conn.execute("UPDATE orders SET status = $1 WHERE id = $2", status, order_id)


async def get_order(order_id: int):
    async with database.pool.acquire() as conn:
        return await conn.fetchrow('''
            SELECT o.*, op.name as op_name, op.price_hold, op.price_no_hold 
            FROM orders o JOIN operators op ON o.operator_id = op.id 
            WHERE o.id = $1
        ''', order_id)


async def update_order_client(order_id: int, client_id: int):
    async with database.pool.acquire() as conn:
        await conn.execute("UPDATE orders SET client_id = $1 WHERE id = $2", client_id, order_id)


async def process_payment(order_id: int) -> float:
    async with database.pool.acquire() as conn:
        order = await conn.fetchrow('''
            SELECT o.supplier_id, o.mode, op.price_hold, op.price_no_hold
            FROM orders o JOIN operators op ON o.operator_id = op.id WHERE o.id = $1
        ''', order_id)

        if not order: return 0.0

        price = float(order['price_hold']) if order['mode'] == 'hold' else float(order['price_no_hold'])
        await conn.execute("UPDATE users SET balance = balance + $1 WHERE telegram_id = $2", price,
                           order['supplier_id'])

        user = await conn.fetchrow("SELECT referrer_id FROM users WHERE telegram_id = $1", order['supplier_id'])

        if user and user['referrer_id']:
            ref_setting = await conn.fetchval("SELECT value FROM settings WHERE key = 'ref_percent'")
            ref_percent = float(ref_setting) if ref_setting else 5.0
            bonus = price * (ref_percent / 100)
            if bonus > 0:
                await conn.execute("UPDATE users SET balance = balance + $1 WHERE telegram_id = $2", bonus,
                                   user['referrer_id'])

        await conn.execute("UPDATE orders SET status = 'completed' WHERE id = $1", order_id)
        return price


async def start_hold(order_id: int):
    hold_end = datetime.now(MSK) + timedelta(minutes=30)
    async with database.pool.acquire() as conn:
        await conn.execute("UPDATE orders SET status = 'holding', hold_end_time = $1 WHERE id = $2",
                           hold_end.replace(tzinfo=None), order_id)
    return hold_end


async def get_expired_holds():
    now = datetime.now(MSK).replace(tzinfo=None)
    async with database.pool.acquire() as conn:
        return await conn.fetch("SELECT * FROM orders WHERE status = 'holding' AND hold_end_time <= $1", now)


async def get_admin_stats():
    async with database.pool.acquire() as conn:
        users_count = await conn.fetchval("SELECT COUNT(*) FROM users")
        orders_count = await conn.fetchval("SELECT COUNT(*) FROM orders")
        withdrawals_count = await conn.fetchval("SELECT COUNT(*) FROM withdrawals WHERE status = 'pending'")
        return {"users": users_count, "orders": orders_count, "withdrawals": withdrawals_count}


async def get_pending_withdrawals(limit: int = 1):
    async with database.pool.acquire() as conn:
        return await conn.fetch("SELECT * FROM withdrawals WHERE status = 'pending' ORDER BY created_at ASC LIMIT $1",
                                limit)


async def get_withdrawal_by_id(withdraw_id: int):
    async with database.pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM withdrawals WHERE id = $1", withdraw_id)


async def process_withdrawal(withdraw_id: int, status: str, user_id: int = None, amount: float = None):
    async with database.pool.acquire() as conn:
        await conn.execute("UPDATE withdrawals SET status = $1 WHERE id = $2", status, withdraw_id)
        if status == 'rejected' and user_id and amount:
            await conn.execute("UPDATE users SET balance = balance + $1 WHERE telegram_id = $2", amount, user_id)


async def get_all_user_ids():
    async with database.pool.acquire() as conn:
        rows = await conn.fetch("SELECT telegram_id FROM users")
        return [row['telegram_id'] for row in rows]


async def set_user_role(telegram_id: int, role: str):
    """Обновляет роль пользователя (назначает админом)."""
    async with database.pool.acquire() as conn:
        await conn.execute("UPDATE users SET role = $1 WHERE telegram_id = $2", role, telegram_id)