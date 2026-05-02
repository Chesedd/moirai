"""Хендлеры aiogram и middleware whitelist'а."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from html import escape
from typing import Any

from aiogram import BaseMiddleware, F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message, TelegramObject, User

from .clock import now_msk
from .inbox import classify, format_line
from .reminder import parse_schedule
from .state import UndoLog
from .storage.drive import DriveStorage
from .storage.today_tasks import TodayTasksReader

logger = logging.getLogger(__name__)

router = Router(name="moirai")

_HELP_TEXT = (
    "Команды:\n"
    "/start — начало работы\n"
    "/help — это сообщение\n"
    "/undo — отменить последнюю запись в inbox\n"
    "/done N — отметить задачу N как выполненную\n"
    "/skip N — пропустить задачу N (не закрывать, перенести)\n"
    "/now — текущее время и ближайшее событие\n"
    "/plan — показать план на сегодня (после первого daily_plan)\n\n"
    "Любое текстовое сообщение — задача или выполнение.\n"
    '"сделал X" / "выполнил X" — будет записано как DONE,\n'
    "остальное — как TASK."
)

_PLAN_STUB_TEXT = (
    "План появится после первого daily_plan от Claude.\nБот начнёт его пересылать автоматически."
)

_DONE_USAGE = "Использование: /done N — где N это номер задачи из /plan."
_SKIP_USAGE = "Использование: /skip N — где N это номер задачи из /plan."

_NO_TODAY_TASKS = (
    "📅 План на сегодня ещё не сгенерирован. Попробуй после 08:00 МСК или напиши /plan."
)

_DRIVE_WRITE_ERROR = "⚠️ Ошибка записи в Drive. Попробуй ещё раз."

_SCHEDULE_NAME = "schedule.md"


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


def _parse_n(command: CommandObject) -> int | None:
    raw = (command.args or "").strip()
    if not raw:
        return None
    try:
        return int(raw.split()[0])
    except (ValueError, IndexError):
        return None


def _unknown_n_text(tasks: dict[int, str]) -> str:
    if not tasks:
        return "❓ В сегодняшнем плане нет задач. Список задач в /plan."
    nums = sorted(tasks.keys())
    if len(nums) == 1:
        rng = f"{nums[0]}"
    else:
        rng = f"{nums[0]}-{nums[-1]}"
    return f"❓ Нет задачи №N. Доступны: {rng}. Список задач в /plan."


async def _resolve_task(
    message: Message,
    command: CommandObject,
    today_tasks: TodayTasksReader,
    usage: str,
) -> str | None:
    n = _parse_n(command)
    if n is None:
        await message.answer(usage)
        return None
    snapshot = await today_tasks.read()
    if snapshot is None:
        await message.answer(_NO_TODAY_TASKS)
        return None
    text = snapshot.tasks.get(n)
    if text is None:
        await message.answer(_unknown_n_text(snapshot.tasks))
        return None
    return text


@router.message(Command("done"))
async def handle_done(
    message: Message,
    command: CommandObject,
    drive: DriveStorage,
    undo_log: UndoLog,
    today_tasks: TodayTasksReader,
) -> None:
    text = await _resolve_task(message, command, today_tasks, _DONE_USAGE)
    if text is None:
        return
    line = format_line(now_msk(), "DONE", text)
    try:
        await drive.append_inbox_line(line)
    except Exception:
        logger.exception("failed to append DONE line to inbox.md")
        await message.answer(_DRIVE_WRITE_ERROR)
        return
    await undo_log.remember(line)
    await message.answer(f"✅ DONE: {text}")


@router.message(Command("skip"))
async def handle_skip(
    message: Message,
    command: CommandObject,
    drive: DriveStorage,
    undo_log: UndoLog,
    today_tasks: TodayTasksReader,
) -> None:
    text = await _resolve_task(message, command, today_tasks, _SKIP_USAGE)
    if text is None:
        return
    line = format_line(now_msk(), "SKIP", text)
    try:
        await drive.append_inbox_line(line)
    except Exception:
        logger.exception("failed to append SKIP line to inbox.md")
        await message.answer(_DRIVE_WRITE_ERROR)
        return
    await undo_log.remember(line)
    await message.answer(
        f"⏭ SKIP: {text}\n(задача останется открытой, но сегодня её делать не будешь)"
    )


@router.message(Command("now"))
async def handle_now(message: Message, drive: DriveStorage) -> None:
    now = now_msk()
    now_str = now.strftime("%H:%M")
    try:
        content = await drive.read_file_by_name(_SCHEDULE_NAME)
    except Exception:
        logger.exception("failed to read schedule.md from Drive")
        await message.answer(_DRIVE_WRITE_ERROR)
        return
    if content is None:
        await message.answer(
            f"🕐 Сейчас: {now_str}\n\nРасписание не обнаружено. schedule_refresh пока не работала."
        )
        return
    entries, _malformed = parse_schedule(content)
    future = [e for e in entries if e.start > now]
    if not future:
        await message.answer(
            f"🕐 Сейчас: {now_str}\n\nДо конца горизонта (7 дней) больше событий нет."
        )
        return
    next_entry = min(future, key=lambda e: e.start)
    delta = next_entry.start - now
    days = delta.days
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    if days > 0:
        time_str = f"{days}д {hours}ч"
    elif hours > 0:
        time_str = f"{hours}ч {minutes}м"
    else:
        time_str = f"{minutes}м"
    kind_emoji = "⏰" if next_entry.kind == "EVENT" else "🔒"
    start_str = next_entry.start.strftime("%H:%M")
    await message.answer(
        f"🕐 Сейчас: {now_str}\n\n"
        f"Через {time_str}: {kind_emoji} {start_str} {next_entry.description}"
    )


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
    line = format_line(now_msk(), kind, text)
    try:
        await drive.append_inbox_line(line)
    except Exception:
        logger.exception("failed to append line to inbox.md")
        await message.answer("⚠️ Ошибка записи. Попробуй ещё раз через минуту.")
        return
    await undo_log.remember(line)
    await message.answer("📝 TASK" if kind == "TASK" else "✅ DONE")
