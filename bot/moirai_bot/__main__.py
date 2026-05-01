"""Точка входа: `python -m moirai_bot`."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher

from .config import Settings
from .handlers import WhitelistMiddleware, router

logger = logging.getLogger("moirai_bot")


async def _run() -> None:
    settings = Settings()  # type: ignore[call-arg]
    logger.info("bot started, allowed users: %s", settings.telegram_allowed_user_ids)

    bot = Bot(token=settings.telegram_bot_token)
    dispatcher = Dispatcher()

    middleware = WhitelistMiddleware(set(settings.telegram_allowed_user_ids))
    dispatcher.message.middleware(middleware)
    dispatcher.edited_message.middleware(middleware)

    dispatcher.include_router(router)

    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    )
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        logger.info("bot stopped by KeyboardInterrupt")


if __name__ == "__main__":
    main()
