"""Хендлеры aiogram и middleware whitelist'а."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware, F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message, TelegramObject, User

logger = logging.getLogger(__name__)

router = Router(name="moirai")


class WhitelistMiddleware(BaseMiddleware):
    """Пропускает апдейты только от заранее разрешённых user_id."""

    def __init__(self, allowed_user_ids: set[int]) -> None:
        self._allowed = allowed_user_ids

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        if user is None or user.id not in self._allowed:
            logger.warning(
                "dropped update from non-whitelisted user_id=%s",
                user.id if user is not None else None,
            )
            return None
        return await handler(event, data)


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    await message.answer("Привет. Я Moirai. Пиши задачи, события, заметки — буду складывать.")


@router.message(F.text)
async def handle_text(message: Message) -> None:
    # Временная заглушка: в подзадаче 3.2 заменится записью в inbox.md.
    await message.answer(f"Принято: {message.text}")
