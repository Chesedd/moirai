"""State-файлы бота: undo log."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path


class UndoLog:
    """Хранит последнюю строку, записанную в inbox, для /undo.

    Файл JSON формата: {"line": "<строка без \\n>"} или {} если пусто.
    """

    def __init__(self, path: str):
        self._path = path
        self._lock = asyncio.Lock()

    async def remember(self, line: str) -> None:
        async with self._lock:
            await asyncio.to_thread(self._write_sync, {"line": line})

    async def pop(self) -> str | None:
        async with self._lock:
            data = await asyncio.to_thread(self._read_sync)
            line = data.get("line") if isinstance(data, dict) else None
            if line is None:
                return None
            await asyncio.to_thread(self._write_sync, {})
            return line

    async def clear(self) -> None:
        async with self._lock:
            await asyncio.to_thread(self._write_sync, {})

    def _read_sync(self) -> dict:
        try:
            with open(self._path, encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            return {}
        if not content.strip():
            return {}
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return {}
        if not isinstance(data, dict):
            return {}
        return data

    def _write_sync(self, data: dict) -> None:
        path = Path(self._path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=None)
        os.replace(tmp_path, path)
