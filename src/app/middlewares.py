from collections.abc import Awaitable, Callable
from typing import Any, cast
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from structlog import get_logger
from structlog.types import FilteringBoundLogger

from src.app.main import OWNER_TGID


class LoggingMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        self._logger: FilteringBoundLogger = get_logger().bind(event="update")

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        match event:
            case Update(message=msg) if msg and msg.from_user:
                await self._logger.ainfo(
                    "Get some message from ID=%s!", msg.from_user.id
                )
            case _:
                pass
        return await handler(event, data)


class OnlyOwnerMiddleware(BaseMiddleware):
    def __init__(self, owner_id: int) -> None:
        self._owner_id = owner_id

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        update = cast(Update, event)
        user_id: int = -1
        match update:
            case Update(message=msg) if msg and msg.from_user:
                user_id = msg.from_user.id
            case _:
                pass
        if user_id != OWNER_TGID:
            return
        return await handler(event, data)
