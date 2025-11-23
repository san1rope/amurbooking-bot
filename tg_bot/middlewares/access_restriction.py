from typing import Dict, Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message

from config import Config


class AccessRestriction(BaseMiddleware):
    def __init__(self) -> None:
        pass

    async def __call__(
            self, handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]], event: Message, data: Dict[str, Any]
    ) -> Any:
        if event.from_user.id in Config.ADMINS:
            return await handler(event, data)

        return None
