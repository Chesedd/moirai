"""Юнит-тесты команд /done, /skip, /now."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import patch

import pytest

from moirai_bot.clock import MSK
from moirai_bot.handlers import handle_done, handle_now, handle_skip
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
