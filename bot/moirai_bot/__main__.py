"""Точка входа: `python -m moirai_bot`."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession

from .config import Settings
from .handlers import WhitelistMiddleware, router
from .poller import OutputsPoller
from .state import LastSent, UndoLog
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

    undo_log_path = f"{settings.state_dir}/undo_log.json"
    undo_log = UndoLog(undo_log_path)
    logger.info("undo log: %s", undo_log_path)

    last_sent_path = f"{settings.state_dir}/last_sent.json"
    last_sent = LastSent(last_sent_path)
    logger.info("last sent: %s", last_sent_path)

    bot = Bot(token=settings.telegram_bot_token, session=session)
    dispatcher = Dispatcher()
    dispatcher["drive"] = drive_storage
    dispatcher["undo_log"] = undo_log

    middleware = WhitelistMiddleware(set(settings.telegram_allowed_user_ids))
    dispatcher.message.middleware(middleware)
    dispatcher.edited_message.middleware(middleware)

    dispatcher.include_router(router)

    poller = OutputsPoller(
        bot=bot,
        drive=drive_storage,
        last_sent=last_sent,
        chat_id=settings.chat_id,
        interval_sec=settings.outputs_poll_interval_sec,
    )
    logger.info(
        "outputs poller: every %s sec, target chat %s",
        settings.outputs_poll_interval_sec,
        settings.chat_id,
    )

    poller_task = asyncio.create_task(poller.run(), name="outputs-poller")
    try:
        await dispatcher.start_polling(bot)
    finally:
        poller_task.cancel()
        try:
            await poller_task
        except asyncio.CancelledError:
            pass
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
