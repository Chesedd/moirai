"""Юнит-тесты для UndoLog."""

from __future__ import annotations

from pathlib import Path

import pytest

from moirai_bot.state import UndoLog


def _path(tmp_path: Path) -> str:
    return str(tmp_path / "undo_log.json")


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
