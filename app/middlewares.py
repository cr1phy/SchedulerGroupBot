from collections.abc import Awaitable, Callable
from typing import Any, cast
from aiogram import BaseMiddleware
from aiogram.types import (
    TelegramObject,
    Update,
)
from structlog import get_logger
from structlog.types import FilteringBoundLogger


class LoggingMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        self._logger: FilteringBoundLogger = get_logger().bind(event="update")

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ):
        update = cast(Update, event)
        match update:
            case Update(message=msg) if msg and msg.from_user:
                await self._logger.ainfo(
                    "Get message from user_id=%s, message_id=%s",
                    msg.from_user.id,
                    msg.message_id,
                )
            case Update(my_chat_member=member) if member:  # ← добавь
                await self._logger.ainfo(
                    "Get my_chat_member event from user_id=%s, status=%s → %s",
                    member.from_user.id,
                    member.old_chat_member.status,
                    member.new_chat_member.status,
                )
            case Update(chat_join_request=req) if req:
                await self._logger.ainfo(
                    "Get chat join request from user_id=%s, chat_id=%s",
                    req.from_user.id,
                    req.chat.id,
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
    ):
        update = cast(Update, event)
        user_id: int | None = None

        match update:
            case Update(message=msg) if msg and msg.from_user:
                user_id = msg.from_user.id
            case Update(my_chat_member=member) if member and member.from_user:
                user_id = member.from_user.id
            case Update(chat_join_request=req) if req and req.from_user:
                user_id = req.from_user.id
            case _:
                return await handler(event, data)

        if user_id != self._owner_id:
            return

        return await handler(event, data)
