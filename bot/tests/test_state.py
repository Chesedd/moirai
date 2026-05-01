"""Юнит-тесты для UndoLog и LastSent."""

from __future__ import annotations

from pathlib import Path

import pytest

from moirai_bot.state import LastSent, UndoLog


def _path(tmp_path: Path) -> str:
    return str(tmp_path / "undo_log.json")


def _last_sent_path(tmp_path: Path) -> str:
    return str(tmp_path / "last_sent.json")


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
