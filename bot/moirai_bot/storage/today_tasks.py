"""Чтение outputs/today_tasks.json — нумерованные задачи текущего дня."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime

from ..clock import MSK
from .drive import DriveStorage

logger = logging.getLogger(__name__)

_TODAY_TASKS_NAME = "today_tasks.json"


@dataclass(frozen=True)
class TodayTasks:
    generated_at: datetime  # МСК-aware
    tasks: dict[int, str]

    @classmethod
    def parse(cls, content: str) -> TodayTasks:
        """Парсит JSON. Бросает ValueError при невалидном JSON.

        Если поле generated_at невалидное — datetime.min с tzinfo МСК.
        Если tasks нет — пустой dict. Невалидные ключи (не int)
        логируются warning'ом и пропускаются.
        """
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"invalid JSON: {e}") from e
        if not isinstance(data, dict):
            raise ValueError("today_tasks.json: top-level value must be an object")

        generated_at_raw = data.get("generated_at")
        generated_at = _parse_generated_at(generated_at_raw)

        raw_tasks = data.get("tasks")
        tasks: dict[int, str] = {}
        if isinstance(raw_tasks, dict):
            for k, v in raw_tasks.items():
                try:
                    key = int(k)
                except (TypeError, ValueError):
                    logger.warning("today_tasks.json: skipping non-int key %r", k)
                    continue
                if not isinstance(v, str):
                    logger.warning("today_tasks.json: skipping non-string value for key %r", k)
                    continue
                tasks[key] = v

        return cls(generated_at=generated_at, tasks=tasks)


def _parse_generated_at(raw: object) -> datetime:
    if not isinstance(raw, str):
        return datetime.min.replace(tzinfo=MSK)
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return datetime.min.replace(tzinfo=MSK)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=MSK)
    return parsed


class TodayTasksReader:
    """Читает today_tasks.json из Drive. Не кэширует — каждый вызов идёт в Drive."""

    def __init__(self, drive: DriveStorage) -> None:
        self._drive = drive

    async def read(self) -> TodayTasks | None:
        """None если файла нет или JSON битый."""
        try:
            content = await self._drive.read_file_by_name(_TODAY_TASKS_NAME)
        except Exception:
            logger.exception("failed to read %s from Drive", _TODAY_TASKS_NAME)
            return None
        if content is None:
            return None
        try:
            return TodayTasks.parse(content)
        except ValueError:
            logger.error("today_tasks.json is malformed", exc_info=True)
            return None
