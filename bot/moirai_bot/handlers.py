"""Хендлеры aiogram и middleware whitelist'а."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from html import escape
from typing import Any
from zoneinfo import ZoneInfo

from aiogram import BaseMiddleware, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, TelegramObject, User

from .inbox import classify, format_line
from .state import UndoLog
from .storage.drive import DriveStorage

logger = logging.getLogger(__name__)

router = Router(name="moirai")

_TZ = ZoneInfo("Europe/Moscow")

_HELP_TEXT = (
    "Команды:\n"
    "/start — начало работы\n"
    "/help — это сообщение\n"
    "/undo — отменить последнюю запись в inbox\n"
    "/done N — отметить задачу выполненной (после первого daily_plan)\n"
    "/plan — показать план на сегодня (после первого daily_plan)\n\n"
    "Любое текстовое сообщение — задача или выполнение.\n"
    '"сделал X" / "выполнил X" — будет записано как DONE,\n'
    "остальное — как TASK."
)

_DONE_STUB_TEXT = (
    "Эта команда будет работать после первого daily_plan от Claude.\n"
    "Сейчас в inbox ещё нет нумерации задач."
)

_PLAN_STUB_TEXT = (
    "План появится после первого daily_plan от Claude.\nБот начнёт его пересылать автоматически."
)


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
    await message.answer(
        "Привет. Я Moirai. Пиши задачи, события, заметки — буду складывать.\n\n"
        "Используй /help для списка команд."
    )


@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    await message.answer(_HELP_TEXT)


@router.message(Command("done"))
async def handle_done(message: Message) -> None:
    await message.answer(_DONE_STUB_TEXT)


@router.message(Command("plan"))
async def handle_plan(message: Message) -> None:
    await message.answer(_PLAN_STUB_TEXT)


@router.message(Command("undo"))
async def handle_undo(message: Message, drive: DriveStorage, undo_log: UndoLog) -> None:
    line = await undo_log.pop()
    if line is None:
        await message.answer("Нечего отменять.")
        return
    try:
        ok = await drive.delete_line_from_inbox(line)
    except Exception:
        logger.exception("failed to delete line from inbox.md")
        await message.answer("⚠️ Ошибка при удалении строки из inbox. Попробуй ещё раз.")
        return
    if ok:
        await message.answer(
            f"Отменено:\n<code>{escape(line)}</code>",
            parse_mode="HTML",
        )
    else:
        logger.error("undo: line not found in inbox.md: %r", line)
        await message.answer("⚠️ Строка не найдена в inbox. Возможно, файл был изменён вручную.")


@router.message(F.text)
async def handle_text(message: Message, drive: DriveStorage, undo_log: UndoLog) -> None:
    text = message.text or ""
    kind = classify(text)
    line = format_line(datetime.now(_TZ), kind, text)
    try:
        await drive.append_inbox_line(line)
    except Exception:
        logger.exception("failed to append line to inbox.md")
        await message.answer("⚠️ Ошибка записи. Попробуй ещё раз через минуту.")
        return
    await undo_log.remember(line)
    await message.answer("📝 TASK" if kind == "TASK" else "✅ DONE")
