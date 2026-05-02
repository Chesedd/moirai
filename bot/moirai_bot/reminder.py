"""Таймер напоминаний: читает schedule.md и шлёт уведомления о EVENT/SLOT."""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot

from .state import RemindersSent
from .storage.drive import DriveStorage

logger = logging.getLogger(__name__)

MSK = ZoneInfo("Europe/Moscow")

# Регулярка соответствует формату из docs/DATA_FORMATS.md.
# Группы: 1=date, 2=time_start, 3=time_end_optional, 4=type, 5=desc
SCHEDULE_LINE_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})"
    r"(?:-(\d{2}:\d{2}))?\s*\|\s*(EVENT|SLOT)\s*\|\s*(.+)$"
)

_SCHEDULE_NAME = "schedule.md"


@dataclass(frozen=True)
class ScheduleEntry:
    start: datetime  # МСК-aware datetime
    kind: str  # "EVENT" или "SLOT"
    description: str
    raw_line: str  # для логов и формирования ключа

    @property
    def key(self) -> str:
        return self.raw_line


def parse_schedule(content: str) -> tuple[list[ScheduleEntry], list[str]]:
    """Парсит schedule.md.

    Возвращает (entries, malformed_lines). Заголовок (первая строка с #) и
    пустые строки пропускаются без warning. Любая нераспознанная содержательная
    строка — в malformed_lines. Время парсится в МСК (Europe/Moscow), aware
    datetime.
    """
    entries: list[ScheduleEntry] = []
    malformed: list[str] = []
    for raw in content.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        match = SCHEDULE_LINE_RE.match(stripped)
        if match is None:
            malformed.append(stripped)
            continue
        date_str, time_start, _time_end, kind, desc = match.groups()
        start = datetime.strptime(f"{date_str} {time_start}", "%Y-%m-%d %H:%M").replace(tzinfo=MSK)
        entries.append(
            ScheduleEntry(
                start=start,
                kind=kind,
                description=desc.strip(),
                raw_line=stripped,
            )
        )
    return entries, malformed


class ReminderTimer:
    """Раз в interval_sec проверяет schedule.md и шлёт напоминания."""

    def __init__(
        self,
        bot: Bot,
        drive: DriveStorage,
        reminders_sent: RemindersSent,
        chat_id: int,
        interval_sec: int,
        lead_event_min: int,
        lead_slot_min: int,
    ) -> None:
        self._bot = bot
        self._drive = drive
        self._reminders_sent = reminders_sent
        self._chat_id = chat_id
        self._interval_sec = interval_sec
        self._lead_event_min = lead_event_min
        self._lead_slot_min = lead_slot_min

    async def run(self) -> None:
        """Бесконечный цикл: sleep -> tick -> sleep, ловит и логирует все ошибки."""
        while True:
            await asyncio.sleep(self._interval_sec)
            try:
                await self.tick()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("reminder timer tick failed")

    async def tick(self) -> None:
        """Один проход: читает schedule.md, шлёт напоминания, чистит state."""
        content = await self._drive.read_file_by_name(_SCHEDULE_NAME)
        if content is None:
            logger.debug("schedule.md not found in outputs/")
            return
        entries, malformed = parse_schedule(content)
        for line in malformed:
            logger.warning("malformed schedule line: %r", line)
        now = datetime.now(MSK)
        for entry in entries:
            lead_min = self._lead_event_min if entry.kind == "EVENT" else self._lead_slot_min
            window_end = now + timedelta(minutes=lead_min)
            if not (now <= entry.start <= window_end):
                continue
            if await self._reminders_sent.is_sent(entry.key):
                continue
            await self._send(entry, now)
            await self._reminders_sent.mark_sent(entry.key)
        await self._reminders_sent.prune_unknown({e.key for e in entries})

    async def _send(self, entry: ScheduleEntry, now: datetime) -> None:
        """Отправляет напоминание про entry в self._chat_id (plain text)."""
        match = SCHEDULE_LINE_RE.match(entry.raw_line)
        time_start = match.group(2) if match else entry.start.strftime("%H:%M")
        time_end = match.group(3) if match else None

        if entry.kind == "EVENT":
            minutes = round((entry.start - now).total_seconds() / 60)
            prefix = "Сейчас" if minutes == 0 else f"Через {minutes} мин"
            text = f"⏰ {prefix} — {time_start} {entry.description}"
        else:
            time_range = f"{time_start}-{time_end}" if time_end else time_start
            text = f"🔒 Скоро занятой слот — {time_range} {entry.description}"

        await self._bot.send_message(chat_id=self._chat_id, text=text)
        logger.info("reminded %s at %s: %s", entry.kind, entry.start, entry.description)
