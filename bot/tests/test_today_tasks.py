"""Юнит-тесты для парсера today_tasks.json."""

from __future__ import annotations

import json

import pytest

from moirai_bot.clock import MSK
from moirai_bot.storage.today_tasks import TodayTasks


def test_parse_valid_json() -> None:
    content = json.dumps(
        {
            "generated_at": "2026-05-02T08:00:00+03:00",
            "tasks": {"1": "Отчёт Q1", "2": "Позвонить подрядчику", "3": "Купить хлеб"},
        }
    )
    parsed = TodayTasks.parse(content)
    assert parsed.tasks == {1: "Отчёт Q1", 2: "Позвонить подрядчику", 3: "Купить хлеб"}
    assert parsed.generated_at.year == 2026
    assert parsed.generated_at.month == 5
    assert parsed.generated_at.day == 2
    assert parsed.generated_at.hour == 8
    assert parsed.generated_at.tzinfo is not None


def test_parse_empty_tasks() -> None:
    content = json.dumps({"generated_at": "2026-05-02T08:00:00+03:00", "tasks": {}})
    parsed = TodayTasks.parse(content)
    assert parsed.tasks == {}


def test_parse_missing_tasks_key() -> None:
    content = json.dumps({"generated_at": "2026-05-02T08:00:00+03:00"})
    parsed = TodayTasks.parse(content)
    assert parsed.tasks == {}


def test_parse_missing_generated_at() -> None:
    content = json.dumps({"tasks": {"1": "Купить хлеб"}})
    parsed = TodayTasks.parse(content)
    assert parsed.tasks == {1: "Купить хлеб"}
    assert parsed.generated_at.tzinfo == MSK


def test_parse_invalid_generated_at_falls_back_to_min() -> None:
    content = json.dumps({"generated_at": "not a date", "tasks": {}})
    parsed = TodayTasks.parse(content)
    assert parsed.generated_at.tzinfo == MSK
    assert parsed.generated_at.year == 1


def test_parse_invalid_json_raises() -> None:
    with pytest.raises(ValueError):
        TodayTasks.parse("{not valid json")


def test_parse_skips_non_int_keys() -> None:
    content = json.dumps(
        {
            "generated_at": "2026-05-02T08:00:00+03:00",
            "tasks": {"1": "первая", "abc": "мусор", "2": "вторая"},
        }
    )
    parsed = TodayTasks.parse(content)
    assert parsed.tasks == {1: "первая", 2: "вторая"}


def test_parse_skips_non_string_values() -> None:
    content = json.dumps(
        {
            "generated_at": "2026-05-02T08:00:00+03:00",
            "tasks": {"1": "первая", "2": 42},
        }
    )
    parsed = TodayTasks.parse(content)
    assert parsed.tasks == {1: "первая"}


def test_parse_top_level_not_object_raises() -> None:
    with pytest.raises(ValueError):
        TodayTasks.parse(json.dumps([1, 2, 3]))
