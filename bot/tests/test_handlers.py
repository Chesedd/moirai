"""Юнит-тесты команд /done, /skip, /now, /remind."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import patch

import pytest

from moirai_bot.clock import MSK
from moirai_bot.handlers import handle_done, handle_now, handle_remind, handle_skip
from moirai_bot.storage.today_tasks import TodayTasks


class FakeDrive:
    def __init__(self, schedule_content: str | None = None, fail_append: bool = False) -> None:
        self.appended: list[str] = []
        self._schedule_content = schedule_content
        self._fail_append = fail_append

    async def append_inbox_line(self, line: str) -> None:
        if self._fail_append:
            raise RuntimeError("simulated drive failure")
        self.appended.append(line)

    async def read_file_by_name(self, name: str) -> str | None:
        if name == "schedule.md":
            return self._schedule_content
        return None


class FakeUndoLog:
    def __init__(self) -> None:
        self.remembered: list[str] = []

    async def remember(self, line: str) -> None:
        self.remembered.append(line)


class FakePendingReminders:
    def __init__(self) -> None:
        self.added: list[tuple[str, datetime]] = []

    async def add(self, task_text: str, due_at: datetime) -> str:
        self.added.append((task_text, due_at))
        return f"pending|{task_text}|{due_at.isoformat()}"


class FakeTodayTasksReader:
    def __init__(self, tasks: TodayTasks | None) -> None:
        self._tasks = tasks

    async def read(self) -> TodayTasks | None:
        return self._tasks


class FakeCommand:
    def __init__(self, args: str | None) -> None:
        self.args = args


class FakeMessage:
    def __init__(self) -> None:
        self.replies: list[tuple[str, dict[str, Any]]] = []

    async def answer(self, text: str, **kwargs: Any) -> None:
        self.replies.append((text, kwargs))


def _tasks(items: dict[int, str]) -> TodayTasks:
    return TodayTasks(generated_at=datetime(2026, 5, 2, 8, 0, tzinfo=MSK), tasks=items)


def _frozen_now() -> datetime:
    return datetime(2026, 5, 2, 14, 30, tzinfo=MSK)


# ---------- /done ----------


async def test_done_with_valid_n_appends_to_inbox() -> None:
    drive = FakeDrive()
    undo = FakeUndoLog()
    reader = FakeTodayTasksReader(_tasks({1: "Отчёт Q1", 2: "Купить хлеб"}))
    msg = FakeMessage()
    with patch("moirai_bot.handlers.now_msk", _frozen_now):
        await handle_done(msg, FakeCommand("1"), drive, undo, reader)  # type: ignore[arg-type]
    assert drive.appended == ["[2026-05-02 14:30] DONE: Отчёт Q1"]
    assert undo.remembered == ["[2026-05-02 14:30] DONE: Отчёт Q1"]
    assert msg.replies[0][0] == "✅ DONE: Отчёт Q1"


async def test_done_with_missing_n_shows_help() -> None:
    drive = FakeDrive()
    undo = FakeUndoLog()
    reader = FakeTodayTasksReader(_tasks({1: "Купить хлеб"}))
    msg = FakeMessage()
    await handle_done(msg, FakeCommand(None), drive, undo, reader)  # type: ignore[arg-type]
    assert drive.appended == []
    assert undo.remembered == []
    assert "/done N" in msg.replies[0][0]


async def test_done_with_unknown_n_shows_available() -> None:
    drive = FakeDrive()
    undo = FakeUndoLog()
    reader = FakeTodayTasksReader(_tasks({1: "Купить хлеб", 2: "Отчёт", 3: "Посылка"}))
    msg = FakeMessage()
    await handle_done(msg, FakeCommand("99"), drive, undo, reader)  # type: ignore[arg-type]
    assert drive.appended == []
    assert "1-3" in msg.replies[0][0]


async def test_done_when_today_tasks_missing_shows_message() -> None:
    drive = FakeDrive()
    undo = FakeUndoLog()
    reader = FakeTodayTasksReader(None)
    msg = FakeMessage()
    await handle_done(msg, FakeCommand("1"), drive, undo, reader)  # type: ignore[arg-type]
    assert drive.appended == []
    assert "План на сегодня" in msg.replies[0][0]


async def test_done_handles_drive_error() -> None:
    drive = FakeDrive(fail_append=True)
    undo = FakeUndoLog()
    reader = FakeTodayTasksReader(_tasks({1: "Купить хлеб"}))
    msg = FakeMessage()
    with patch("moirai_bot.handlers.now_msk", _frozen_now):
        await handle_done(msg, FakeCommand("1"), drive, undo, reader)  # type: ignore[arg-type]
    assert undo.remembered == []
    assert "Ошибка записи" in msg.replies[0][0]


# ---------- /skip ----------


async def test_skip_with_valid_n_appends_to_inbox() -> None:
    drive = FakeDrive()
    undo = FakeUndoLog()
    reader = FakeTodayTasksReader(_tasks({1: "Купить хлеб"}))
    msg = FakeMessage()
    with patch("moirai_bot.handlers.now_msk", _frozen_now):
        await handle_skip(msg, FakeCommand("1"), drive, undo, reader)  # type: ignore[arg-type]
    assert drive.appended == ["[2026-05-02 14:30] SKIP: Купить хлеб"]
    assert undo.remembered == ["[2026-05-02 14:30] SKIP: Купить хлеб"]
    assert msg.replies[0][0].startswith("⏭ SKIP: Купить хлеб")


async def test_skip_writes_skip_not_done() -> None:
    drive = FakeDrive()
    undo = FakeUndoLog()
    reader = FakeTodayTasksReader(_tasks({1: "Отчёт Q1"}))
    msg = FakeMessage()
    with patch("moirai_bot.handlers.now_msk", _frozen_now):
        await handle_skip(msg, FakeCommand("1"), drive, undo, reader)  # type: ignore[arg-type]
    assert "SKIP:" in drive.appended[0]
    assert "DONE:" not in drive.appended[0]


async def test_skip_with_unknown_n_shows_available() -> None:
    drive = FakeDrive()
    undo = FakeUndoLog()
    reader = FakeTodayTasksReader(_tasks({1: "Купить хлеб"}))
    msg = FakeMessage()
    await handle_skip(msg, FakeCommand("5"), drive, undo, reader)  # type: ignore[arg-type]
    assert drive.appended == []
    assert "Нет задачи" in msg.replies[0][0]


# ---------- /now ----------


@pytest.fixture
def schedule_with_event() -> str:
    return (
        "# Расписание\n"
        "2026-05-02 16:00 | EVENT | стоматолог\n"
        "2026-05-02 18:00-20:00 | SLOT | работа\n"
    )


async def test_now_shows_next_event(schedule_with_event: str) -> None:
    drive = FakeDrive(schedule_content=schedule_with_event)
    msg = FakeMessage()
    with patch("moirai_bot.handlers.now_msk", _frozen_now):
        await handle_now(msg, drive)  # type: ignore[arg-type]
    text = msg.replies[0][0]
    assert "🕐 Сейчас: 14:30" in text
    assert "Через 1ч 30м" in text
    assert "⏰ 16:00 стоматолог" in text


async def test_now_when_no_schedule_shows_message() -> None:
    drive = FakeDrive(schedule_content=None)
    msg = FakeMessage()
    with patch("moirai_bot.handlers.now_msk", _frozen_now):
        await handle_now(msg, drive)  # type: ignore[arg-type]
    text = msg.replies[0][0]
    assert "🕐 Сейчас: 14:30" in text
    assert "Расписание не обнаружено" in text


async def test_now_when_no_future_events() -> None:
    schedule = "# Расписание\n2026-05-02 10:00 | EVENT | прошедшее\n"
    drive = FakeDrive(schedule_content=schedule)
    msg = FakeMessage()
    with patch("moirai_bot.handlers.now_msk", _frozen_now):
        await handle_now(msg, drive)  # type: ignore[arg-type]
    text = msg.replies[0][0]
    assert "🕐 Сейчас: 14:30" in text
    assert "больше событий нет" in text


async def test_now_picks_earliest_future_event() -> None:
    schedule = (
        "# Расписание\n"
        "2026-05-03 09:00 | EVENT | завтра\n"
        "2026-05-02 15:00 | EVENT | через полчаса\n"
    )
    drive = FakeDrive(schedule_content=schedule)
    msg = FakeMessage()
    with patch("moirai_bot.handlers.now_msk", _frozen_now):
        await handle_now(msg, drive)  # type: ignore[arg-type]
    text = msg.replies[0][0]
    assert "через полчаса" in text
    assert "Через 30м" in text


async def test_now_formats_days_for_far_event() -> None:
    schedule = "# Расписание\n2026-05-05 14:30 | EVENT | через три дня\n"
    drive = FakeDrive(schedule_content=schedule)
    msg = FakeMessage()
    with patch("moirai_bot.handlers.now_msk", _frozen_now):
        await handle_now(msg, drive)  # type: ignore[arg-type]
    text = msg.replies[0][0]
    assert "Через 3д 0ч" in text


async def test_now_slot_uses_lock_emoji() -> None:
    schedule = "# Расписание\n2026-05-02 17:00-19:00 | SLOT | работа\n"
    drive = FakeDrive(schedule_content=schedule)
    msg = FakeMessage()
    with patch("moirai_bot.handlers.now_msk", _frozen_now):
        await handle_now(msg, drive)  # type: ignore[arg-type]
    text = msg.replies[0][0]
    assert "🔒 17:00 работа" in text


# ---------- /remind ----------


async def test_remind_no_args_shows_usage() -> None:
    reader = FakeTodayTasksReader(_tasks({1: "Купить хлеб"}))
    pending = FakePendingReminders()
    msg = FakeMessage()
    await handle_remind(msg, FakeCommand(None), reader, pending)  # type: ignore[arg-type]
    assert pending.added == []
    assert "/remind N HH:MM" in msg.replies[0][0]


async def test_remind_only_n_shows_usage() -> None:
    reader = FakeTodayTasksReader(_tasks({1: "Купить хлеб"}))
    pending = FakePendingReminders()
    msg = FakeMessage()
    await handle_remind(msg, FakeCommand("3"), reader, pending)  # type: ignore[arg-type]
    assert pending.added == []
    assert "/remind N HH:MM" in msg.replies[0][0]


async def test_remind_with_invalid_time_format() -> None:
    reader = FakeTodayTasksReader(_tasks({1: "Купить хлеб"}))
    pending = FakePendingReminders()
    msg = FakeMessage()
    await handle_remind(msg, FakeCommand("1 abc"), reader, pending)  # type: ignore[arg-type]
    assert pending.added == []
    assert "формат времени" in msg.replies[0][0]


async def test_remind_with_non_int_n() -> None:
    reader = FakeTodayTasksReader(_tasks({1: "Купить хлеб"}))
    pending = FakePendingReminders()
    msg = FakeMessage()
    await handle_remind(msg, FakeCommand("abc 18:00"), reader, pending)  # type: ignore[arg-type]
    assert pending.added == []
    assert "числом" in msg.replies[0][0]


async def test_remind_with_unknown_n() -> None:
    reader = FakeTodayTasksReader(_tasks({1: "Купить хлеб"}))
    pending = FakePendingReminders()
    msg = FakeMessage()
    with patch("moirai_bot.handlers.now_msk", _frozen_now):
        await handle_remind(msg, FakeCommand("99 18:00"), reader, pending)  # type: ignore[arg-type]
    assert pending.added == []
    assert "Нет задачи" in msg.replies[0][0]


async def test_remind_when_today_tasks_missing() -> None:
    reader = FakeTodayTasksReader(None)
    pending = FakePendingReminders()
    msg = FakeMessage()
    with patch("moirai_bot.handlers.now_msk", _frozen_now):
        await handle_remind(msg, FakeCommand("1 18:00"), reader, pending)  # type: ignore[arg-type]
    assert pending.added == []
    assert "План на сегодня" in msg.replies[0][0]


async def test_remind_with_past_time_rejected() -> None:
    reader = FakeTodayTasksReader(_tasks({1: "Купить хлеб"}))
    pending = FakePendingReminders()
    msg = FakeMessage()
    with patch("moirai_bot.handlers.now_msk", _frozen_now):
        await handle_remind(msg, FakeCommand("1 10:00"), reader, pending)  # type: ignore[arg-type]
    assert pending.added == []
    assert "уже прошло" in msg.replies[0][0]


async def test_remind_with_valid_args_adds_to_pending() -> None:
    reader = FakeTodayTasksReader(_tasks({1: "Купить хлеб", 2: "Отчёт Q1"}))
    pending = FakePendingReminders()
    msg = FakeMessage()
    with patch("moirai_bot.handlers.now_msk", _frozen_now):
        await handle_remind(msg, FakeCommand("2 18:00"), reader, pending)  # type: ignore[arg-type]
    assert len(pending.added) == 1
    task_text, due_at = pending.added[0]
    assert task_text == "Отчёт Q1"
    assert due_at == datetime(2026, 5, 2, 18, 0, tzinfo=MSK)
    assert "⏰ Напомню в 18:00" in msg.replies[0][0]
    assert "Отчёт Q1" in msg.replies[0][0]


async def test_remind_does_not_write_to_inbox() -> None:
    drive = FakeDrive()
    reader = FakeTodayTasksReader(_tasks({1: "Купить хлеб"}))
    pending = FakePendingReminders()
    msg = FakeMessage()
    with patch("moirai_bot.handlers.now_msk", _frozen_now):
        await handle_remind(msg, FakeCommand("1 18:00"), reader, pending)  # type: ignore[arg-type]
    assert drive.appended == []
