"""Moirai Telegram bot — entry point.

Заглушка для первого коммита. Реальная реализация — в Фазе 3 роадмапа.
Сейчас контейнер просто поднимается и висит, чтобы инфраструктуру
можно было проверить целиком до того, как появится логика.
"""

from __future__ import annotations

import asyncio
import logging
import os

logger = logging.getLogger(__name__)


async def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger.info("Moirai bot starting (stub — см. ROADMAP Фаза 3)")

    # TODO: aiogram Bot + Dispatcher + handlers + long polling.
    # Пока держим процесс живым, чтобы docker-compose не рестартил.
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
