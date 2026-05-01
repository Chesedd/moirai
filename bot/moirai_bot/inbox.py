"""Классификация входящих сообщений и форматирование строк inbox.md."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

_DONE_WORDS: frozenset[str] = frozenset(
    {
        "сделал",
        "сделала",
        "сделано",
        "выполнил",
        "выполнила",
        "выполнено",
        "закрыл",
        "закрыла",
        "готово",
    }
)

_TRAILING_PUNCT: str = ".,:—-"


def classify(text: str) -> Literal["TASK", "DONE"]:
    """Возвращает тип записи по первому токену сообщения."""
    tokens = text.split()
    if not tokens:
        return "TASK"
    first = tokens[0].lower().rstrip(_TRAILING_PUNCT)
    if first in _DONE_WORDS:
        return "DONE"
    return "TASK"


def format_line(when: datetime, kind: str, text: str) -> str:
    """Возвращает строку формата `[YYYY-MM-DD HH:MM] TYPE: text` без перевода."""
    timestamp = when.strftime("%Y-%m-%d %H:%M")
    return f"[{timestamp}] {kind}: {text}"
