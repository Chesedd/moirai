"""Точка входа: `python -m moirai_bot`."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession

from .config import Settings
from .handlers import WhitelistMiddleware, router
from .storage.drive import DriveStorage

logger = logging.getLogger("moirai_bot")


async def _run() -> None:
    settings = Settings()  # type: ignore[call-arg]
    if settings.telegram_proxy_url:
        logger.info("telegram proxy: %s", settings.telegram_proxy_url)
        session = AiohttpSession(proxy=settings.telegram_proxy_url)
    else:
        logger.info("telegram proxy: not set, using direct connection")
        session = AiohttpSession()
    logger.info("bot started, allowed users: %s", settings.telegram_allowed_user_ids)

    drive_storage = DriveStorage(
        service_account_file=settings.gdrive_service_account_file,
        folder_id=settings.gdrive_folder_id,
    )
    logger.info("drive storage: folder=%s", settings.gdrive_folder_id)

    bot = Bot(token=settings.telegram_bot_token, session=session)
    dispatcher = Dispatcher()
    dispatcher["drive"] = drive_storage

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
