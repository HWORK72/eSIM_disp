import time
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, limit: float = 1.0):
        """
        limit: Время в секундах, которое должен подождать юзер между действиями.
        """
        self.limit = limit
        self.users = {}

    async def __call__(
            self,
            handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
            event: Any,
            data: Dict[str, Any]
    ) -> Any:

        # Определяем ID пользователя (из сообщения или нажатия кнопки)
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        else:
            return await handler(event, data)

        now = time.time()

        # Базовая защита от утечки памяти
        if len(self.users) > 10000:
            self.users.clear()

        # Проверяем, как давно было последнее действие
        if user_id in self.users:
            if now - self.users[user_id] < self.limit:
                # Если времени прошло меньше лимита - игнорируем действие (защита от спама)
                return

                # Обновляем время последнего действия
        self.users[user_id] = now

        # Передаем управление дальше (в handlers)
        return await handler(event, data)