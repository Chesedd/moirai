"""Фоновый поллер outputs/ на Drive: пересылает короткие артефакты в Telegram."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot

from .state import LastSent
from .storage.drive import DriveStorage

logger = logging.getLogger(__name__)

_SHORT_SUFFIX: str = "_short.md"
_CHUNK_LIMIT: int = 3900


class OutputsPoller:
    """Раз в interval_sec проверяет outputs/ и пересылает обновлённые *_short.md."""

    def __init__(
        self,
        bot: Bot,
        drive: DriveStorage,
        last_sent: LastSent,
        chat_id: int,
        interval_sec: int,
    ) -> None:
        self._bot = bot
        self._drive = drive
        self._last_sent = last_sent
        self._chat_id = chat_id
        self._interval_sec = interval_sec

    async def run(self) -> None:
        """Бесконечный цикл: sleep -> tick -> sleep, ловит и логирует все ошибки."""
        while True:
            await asyncio.sleep(self._interval_sec)
            try:
                await self.tick()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("outputs poller tick failed")

    async def tick(self) -> None:
        """Один проход: список outputs/, отправка обновлённых *_short.md."""
        files = await self._drive.list_outputs()
        for file in files:
            if not file.name.endswith(_SHORT_SUFFIX):
                continue
            prev = await self._last_sent.get(file.id)
            if prev == file.modified_time:
                continue
            content = await self._drive.read_file(file.id)
            await self._send(file.name, content)
            await self._last_sent.set(file.id, file.modified_time)
        await self._last_sent.prune_unknown({f.id for f in files})

    async def _send(self, name: str, content: str) -> None:
        """Отправляет content в self._chat_id, разбивая на куски при необходимости."""
        chunks = _split_chunks(content, _CHUNK_LIMIT)
        for chunk in chunks:
            await self._bot.send_message(chat_id=self._chat_id, text=chunk)
        logger.info("sent %s (%d chars, %d chunks)", name, len(content), len(chunks))


def _split_chunks(content: str, limit: int) -> list[str]:
    if not content:
        return [""]
    return [content[i : i + limit] for i in range(0, len(content), limit)]
