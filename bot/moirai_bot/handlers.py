"""Хендлеры aiogram и middleware whitelist'а."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from aiogram import BaseMiddleware, F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message, TelegramObject, User

from .inbox import classify, format_line
from .storage.drive import DriveStorage

logger = logging.getLogger(__name__)

router = Router(name="moirai")

_TZ = ZoneInfo("Europe/Moscow")


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
async def handle_text(message: Message, drive: DriveStorage) -> None:
    text = message.text or ""
    kind = classify(text)
    line = format_line(datetime.now(_TZ), kind, text)
    try:
        await drive.append_inbox_line(line)
    except Exception:
        logger.exception("failed to append line to inbox.md")
        await message.answer("⚠️ Ошибка записи. Попробуй ещё раз через минуту.")
        return
    await message.answer("📝 TASK" if kind == "TASK" else "✅ DONE")
