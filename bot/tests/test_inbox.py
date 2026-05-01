"""Юнит-тесты для классификации входящих и форматирования строк."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from moirai_bot.inbox import classify, format_line


def test_classify_plain_task() -> None:
    assert classify("купить хлеб") == "TASK"


def test_classify_done_capitalized() -> None:
    assert classify("Сделал отчёт") == "DONE"


def test_classify_done_with_punctuation() -> None:
    assert classify("сделано.") == "DONE"


def test_classify_not_a_prefix_match() -> None:
    # «сделалось» не входит в набор слов и не должно срабатывать.
    assert classify("сделалось как-то") == "TASK"


def test_classify_leading_whitespace() -> None:
    assert classify("  Готово") == "DONE"


def test_classify_empty_string() -> None:
    assert classify("") == "TASK"


def test_format_line_fixed_datetime() -> None:
    when = datetime(2026, 4, 28, 14, 32, tzinfo=ZoneInfo("Europe/Moscow"))
    assert format_line(when, "TASK", "купить хлеб #личное") == (
        "[2026-04-28 14:32] TASK: купить хлеб #личное"
    )


def test_format_line_preserves_text_verbatim() -> None:
    when = datetime(2026, 4, 28, 9, 5, tzinfo=ZoneInfo("Europe/Moscow"))
    text = "🎉 (срочно) тест — émoji + русский"
    assert format_line(when, "DONE", text) == f"[2026-04-28 09:05] DONE: {text}"


def test_format_line_two_digit_components() -> None:
    when = datetime(2026, 1, 2, 3, 4, tzinfo=ZoneInfo("Europe/Moscow"))
    line = format_line(when, "TASK", "x")
    assert line.startswith("[2026-01-02 03:04] ")
    assert "[2026-1-2 3:4]" not in line
