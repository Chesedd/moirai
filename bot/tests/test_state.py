"""Юнит-тесты для UndoLog, LastSent, RemindersSent и PendingReminders."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from moirai_bot.clock import MSK
from moirai_bot.state import LastSent, PendingReminders, RemindersSent, UndoLog


def _path(tmp_path: Path) -> str:
    return str(tmp_path / "undo_log.json")


def _last_sent_path(tmp_path: Path) -> str:
    return str(tmp_path / "last_sent.json")


def _reminders_sent_path(tmp_path: Path) -> str:
    return str(tmp_path / "reminders_sent.json")


def _pending_path(tmp_path: Path) -> str:
    return str(tmp_path / "pending_reminders.json")


async def test_remember_then_pop_returns_line(tmp_path: Path) -> None:
    log = UndoLog(_path(tmp_path))
    await log.remember("[2026-04-28 14:32] TASK: купить хлеб")
    assert await log.pop() == "[2026-04-28 14:32] TASK: купить хлеб"


async def test_pop_on_empty_file_returns_none(tmp_path: Path) -> None:
    path = _path(tmp_path)
    Path(path).write_text("{}", encoding="utf-8")
    log = UndoLog(path)
    assert await log.pop() is None


async def test_pop_on_missing_file_returns_none(tmp_path: Path) -> None:
    log = UndoLog(_path(tmp_path))
    assert await log.pop() is None


async def test_pop_clears_file(tmp_path: Path) -> None:
    log = UndoLog(_path(tmp_path))
    await log.remember("первая строка")
    assert await log.pop() == "первая строка"
    assert await log.pop() is None


async def test_clear_makes_pop_return_none(tmp_path: Path) -> None:
    log = UndoLog(_path(tmp_path))
    await log.remember("какая-то строка")
    await log.clear()
    assert await log.pop() is None


async def test_remember_overwrites_previous(tmp_path: Path) -> None:
    log = UndoLog(_path(tmp_path))
    await log.remember("первая")
    await log.remember("вторая")
    assert await log.pop() == "вторая"
    assert await log.pop() is None


@pytest.mark.parametrize("payload", ["с пробелом и !важно #тег", "ascii only"])
async def test_remember_pop_roundtrip_unicode(tmp_path: Path, payload: str) -> None:
    log = UndoLog(_path(tmp_path))
    await log.remember(payload)
    assert await log.pop() == payload


async def test_get_on_missing_file_returns_none(tmp_path: Path) -> None:
    last_sent = LastSent(_last_sent_path(tmp_path))
    assert await last_sent.get("daily_plan_short.md") is None


async def test_set_then_get(tmp_path: Path) -> None:
    last_sent = LastSent(_last_sent_path(tmp_path))
    await last_sent.set("daily_plan_short.md", "2026-05-02T08:00:00.000Z")
    assert await last_sent.get("daily_plan_short.md") == "2026-05-02T08:00:00.000Z"


async def test_set_overwrites_same_key(tmp_path: Path) -> None:
    last_sent = LastSent(_last_sent_path(tmp_path))
    await last_sent.set("daily_plan_short.md", "2026-05-02T08:00:00.000Z")
    await last_sent.set("daily_plan_short.md", "2026-05-03T08:00:00.000Z")
    assert await last_sent.get("daily_plan_short.md") == "2026-05-03T08:00:00.000Z"


async def test_set_keeps_other_keys(tmp_path: Path) -> None:
    last_sent = LastSent(_last_sent_path(tmp_path))
    await last_sent.set("daily_plan_short.md", "2026-05-02T08:00:00.000Z")
    await last_sent.set("weekly_review_short.md", "2026-05-04T20:00:00.000Z")
    await last_sent.set("daily_plan_short.md", "2026-05-03T08:00:00.000Z")
    assert await last_sent.get("daily_plan_short.md") == "2026-05-03T08:00:00.000Z"
    assert await last_sent.get("weekly_review_short.md") == "2026-05-04T20:00:00.000Z"


async def test_get_unknown_key_returns_none(tmp_path: Path) -> None:
    last_sent = LastSent(_last_sent_path(tmp_path))
    await last_sent.set("daily_plan_short.md", "2026-05-02T08:00:00.000Z")
    assert await last_sent.get("priorities_short.md") is None


async def test_prune_removes_keys_not_in_set(tmp_path: Path) -> None:
    last_sent = LastSent(_last_sent_path(tmp_path))
    await last_sent.set("id-keep", "2026-05-02T08:00:00.000Z")
    await last_sent.set("id-drop", "2026-05-02T08:00:00.000Z")
    await last_sent.prune_unknown({"id-keep"})
    assert await last_sent.get("id-keep") == "2026-05-02T08:00:00.000Z"
    assert await last_sent.get("id-drop") is None


async def test_prune_keeps_keys_in_set(tmp_path: Path) -> None:
    last_sent = LastSent(_last_sent_path(tmp_path))
    await last_sent.set("id-a", "2026-05-02T08:00:00.000Z")
    await last_sent.set("id-b", "2026-05-03T08:00:00.000Z")
    await last_sent.prune_unknown({"id-a", "id-b", "id-c"})
    assert await last_sent.get("id-a") == "2026-05-02T08:00:00.000Z"
    assert await last_sent.get("id-b") == "2026-05-03T08:00:00.000Z"


async def test_prune_on_empty_state_does_nothing(tmp_path: Path) -> None:
    path = _last_sent_path(tmp_path)
    Path(path).write_text("{}", encoding="utf-8")
    last_sent = LastSent(path)
    await last_sent.prune_unknown({"id-a"})
    assert await last_sent.get("id-a") is None


async def test_prune_on_missing_file_does_nothing(tmp_path: Path) -> None:
    last_sent = LastSent(_last_sent_path(tmp_path))
    await last_sent.prune_unknown({"id-a"})
    assert await last_sent.get("id-a") is None


async def test_reminders_is_sent_on_unknown_returns_false(tmp_path: Path) -> None:
    reminders = RemindersSent(_reminders_sent_path(tmp_path))
    assert await reminders.is_sent("2026-04-24 10:00|EVENT|стоматолог") is False


async def test_reminders_mark_then_is_sent(tmp_path: Path) -> None:
    reminders = RemindersSent(_reminders_sent_path(tmp_path))
    key = "2026-04-24 10:00|EVENT|стоматолог"
    await reminders.mark_sent(key)
    assert await reminders.is_sent(key) is True


async def test_reminders_prune_removes_unknown(tmp_path: Path) -> None:
    reminders = RemindersSent(_reminders_sent_path(tmp_path))
    keep = "2026-04-24 10:00|EVENT|стоматолог"
    drop = "2026-04-23 09:00-10:00|SLOT|прошлое"
    await reminders.mark_sent(keep)
    await reminders.mark_sent(drop)
    await reminders.prune_unknown({keep})
    assert await reminders.is_sent(keep) is True
    assert await reminders.is_sent(drop) is False


# ---------- PendingReminders ----------


async def test_pending_add_and_list(tmp_path: Path) -> None:
    pending = PendingReminders(_pending_path(tmp_path))
    due = datetime(2026, 5, 2, 18, 0, tzinfo=MSK)
    key = await pending.add("Купить хлеб", due)
    contents = await pending.list_all()
    assert key in contents
    assert contents[key]["task_text"] == "Купить хлеб"
    assert contents[key]["due_at"] == due.isoformat()
    assert "created_at" in contents[key]


async def test_pending_all_due_returns_due_entries(tmp_path: Path) -> None:
    pending = PendingReminders(_pending_path(tmp_path))
    now = datetime(2026, 5, 2, 18, 0, tzinfo=MSK)
    await pending.add("Сейчас", now)
    due = await pending.all_due(now)
    assert len(due) == 1
    assert due[0]["task_text"] == "Сейчас"
    assert due[0]["due_at"] == now


async def test_pending_all_due_excludes_future(tmp_path: Path) -> None:
    pending = PendingReminders(_pending_path(tmp_path))
    now = datetime(2026, 5, 2, 18, 0, tzinfo=MSK)
    far_future = now + timedelta(minutes=30)
    await pending.add("Позже", far_future)
    due = await pending.all_due(now)
    assert due == []


async def test_pending_all_due_includes_recent_past(tmp_path: Path) -> None:
    pending = PendingReminders(_pending_path(tmp_path))
    now = datetime(2026, 5, 2, 18, 0, tzinfo=MSK)
    one_minute_ago = now - timedelta(minutes=1)
    await pending.add("Минуту назад", one_minute_ago)
    due = await pending.all_due(now)
    assert len(due) == 1
    assert due[0]["task_text"] == "Минуту назад"


async def test_pending_all_due_excludes_far_past(tmp_path: Path) -> None:
    pending = PendingReminders(_pending_path(tmp_path))
    now = datetime(2026, 5, 2, 18, 0, tzinfo=MSK)
    far_past = now - timedelta(minutes=10)
    await pending.add("Давно", far_past)
    due = await pending.all_due(now)
    assert due == []


async def test_pending_remove_deletes_entry(tmp_path: Path) -> None:
    pending = PendingReminders(_pending_path(tmp_path))
    due = datetime(2026, 5, 2, 18, 0, tzinfo=MSK)
    key = await pending.add("Купить хлеб", due)
    await pending.remove(key)
    contents = await pending.list_all()
    assert key not in contents


async def test_pending_remove_idempotent(tmp_path: Path) -> None:
    pending = PendingReminders(_pending_path(tmp_path))
    await pending.remove("nonexistent-key")
    contents = await pending.list_all()
    assert contents == {}


async def test_pending_list_all_on_missing_file_returns_empty(tmp_path: Path) -> None:
    pending = PendingReminders(_pending_path(tmp_path))
    contents = await pending.list_all()
    assert contents == {}


async def test_pending_add_requires_aware_datetime(tmp_path: Path) -> None:
    pending = PendingReminders(_pending_path(tmp_path))
    naive = datetime(2026, 5, 2, 18, 0)
    with pytest.raises(ValueError):
        await pending.add("Без TZ", naive)
