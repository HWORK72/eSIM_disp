import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

from database import init_db
from handlers import router
from middlewares import ThrottlingMiddleware
from db_requests import get_expired_holds, process_payment

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    sys.exit("Ошибка: BOT_TOKEN не найден. Проверьте файл .env")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def hold_checker(bot: Bot):
    """Каждую минуту проверяет базу на наличие истекших холдов."""
    while True:
        try:
            expired_orders = await get_expired_holds()
            for order in expired_orders:
                price = await process_payment(order['id'])

                try:
                    supplier_text = (
                        f"✅ <b>Холд успешно пройден!</b>\n"
                        f"Ваш номер <code>{order['phone_number']}</code> оплачен.\n"
                        f"💰 Начислено: <b>${price:.2f}</b>"
                    )
                    await bot.send_message(chat_id=order['supplier_id'], text=supplier_text)
                except Exception as e:
                    logger.error(f"Не удалось отправить уведомление поставщику: {e}")

        except Exception as e:
            logger.error(f"Ошибка в фоновом чекере холдов: {e}")

        await asyncio.sleep(60)


async def main():
    await init_db()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # === ПОДКЛЮЧАЕМ АНТИ-СПАМ ===
    # Вешаем Middleware на текстовые сообщения и на кнопки
    dp.message.middleware(ThrottlingMiddleware(limit=1.0))
    dp.callback_query.middleware(ThrottlingMiddleware(limit=1.0))

    dp.include_router(router)

    asyncio.create_task(hold_checker(bot))

    logger.info("Бот успешно запущен и готов к работе!")

    try:
        await dp.start_polling(bot, drop_pending_updates=True)
    except Exception as e:
        logger.error(f"Критическая ошибка при работе бота: {e}")
    finally:
        logger.info("Остановка бота, закрытие сессий...")
        await bot.session.close()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Работа бота прервана пользователем (Ctrl+C).")