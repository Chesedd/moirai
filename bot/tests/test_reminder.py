"""Юнит-тесты parse_schedule и ScheduleEntry."""

from __future__ import annotations

from moirai_bot.reminder import MSK, ScheduleEntry, parse_schedule


def test_parse_schedule_valid_lines() -> None:
    content = (
        "# Расписание (обновлено 2026-04-24 08:00)\n"
        "\n"
        "2026-04-24 10:00       | EVENT | стоматолог\n"
        "2026-04-24 17:00-18:00 | SLOT  | работа\n"
        "2026-04-25 09:00-13:00 | SLOT  | офис с пробелами и тире — длинно\n"
        "2026-04-25 14:00       | EVENT | созвон #команда !важно\n"
    )
    entries, malformed = parse_schedule(content)
    assert malformed == []
    assert len(entries) == 4

    event = entries[0]
    assert event.kind == "EVENT"
    assert event.description == "стоматолог"
    assert event.start.tzinfo == MSK
    assert event.start.year == 2026
    assert event.start.month == 4
    assert event.start.day == 24
    assert event.start.hour == 10
    assert event.start.minute == 0

    slot = entries[1]
    assert slot.kind == "SLOT"
    assert slot.description == "работа"
    assert slot.start.hour == 17

    slot_with_spaces = entries[2]
    assert slot_with_spaces.kind == "SLOT"
    assert slot_with_spaces.description == "офис с пробелами и тире — длинно"

    event_special = entries[3]
    assert event_special.kind == "EVENT"
    assert event_special.description == "созвон #команда !важно"


def test_parse_schedule_skips_header_and_blank() -> None:
    content = "# Расписание\n\n   \n2026-04-24 10:00 | EVENT | стоматолог\n\n"
    entries, malformed = parse_schedule(content)
    assert malformed == []
    assert len(entries) == 1
    assert entries[0].description == "стоматолог"


def test_parse_schedule_collects_malformed() -> None:
    content = (
        "# заголовок\n"
        "2026-04-24 10:00 | EVENT | стоматолог\n"
        "это битая строка\n"
        "2026-04-24 11:00 | OTHER | неизвестный тип\n"
        "26-04-24 11:00 | EVENT | плохая дата\n"
        "2026-04-24 12:00 | SLOT | валидный слот без конца\n"
    )
    entries, malformed = parse_schedule(content)
    assert len(entries) == 2
    assert {e.description for e in entries} == {"стоматолог", "валидный слот без конца"}
    assert "это битая строка" in malformed
    assert "2026-04-24 11:00 | OTHER | неизвестный тип" in malformed
    assert "26-04-24 11:00 | EVENT | плохая дата" in malformed


def test_parse_schedule_empty_content() -> None:
    entries, malformed = parse_schedule("")
    assert entries == []
    assert malformed == []


def test_schedule_entry_key_is_raw_line() -> None:
    content = "2026-04-24 17:00-18:00 | SLOT  | работа\n"
    entries, _ = parse_schedule(content)
    entry = entries[0]
    assert entry.key == "2026-04-24 17:00-18:00 | SLOT  | работа"
    assert isinstance(entry, ScheduleEntry)
