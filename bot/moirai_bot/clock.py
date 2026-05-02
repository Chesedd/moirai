"""Часы МСК — единая точка получения текущего времени."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

MSK = ZoneInfo("Europe/Moscow")


def now_msk() -> datetime:
    """Возвращает текущий datetime в TZ Europe/Moscow (aware)."""
    return datetime.now(MSK)
