from __future__ import annotations
import asyncio
import logging
import time

import telegram
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from src.adapters.base import PlatformAdapter
from src.models.internal_message import InternalMessage, MessageType, Platform
from src.core.message_router import MessageRouter
from src.core import session_manager
from src.services.file_handler import FileHandler

logger = logging.getLogger(__name__)


class TelegramAdapter(PlatformAdapter):
    def __init__(self, token: str, router: MessageRouter, file_handler: FileHandler) -> None:
        self._router = router
        self._files = file_handler
        self._loop: asyncio.AbstractEventLoop | None = None

        async def _post_init(app) -> None:
            self._loop = asyncio.get_running_loop()

        self._app = ApplicationBuilder().token(token).post_init(_post_init).build()
        self._app.add_handler(CommandHandler("start", self._on_start))
        self._app.add_handler(CommandHandler("menu", self._on_start))
        self._app.add_handler(CommandHandler("close", self._on_close))
        self._app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_text))
        self._app.add_handler(MessageHandler(filters.Document.ALL, self._on_document))
        self._app.add_handler(MessageHandler(filters.PHOTO, self._on_photo))

    # ---------------------------------------------------------------- public

    def send_text(self, chat_id: str, text: str) -> None:
        future = asyncio.run_coroutine_threadsafe(
            self._app.bot.send_message(chat_id=int(chat_id), text=text),
            self._loop,
        )
        future.result(timeout=30)

    def send_file(self, chat_id: str, file_path: str, caption: str = "") -> None:
        async def _send():
            with open(file_path, "rb") as f:
                await self._app.bot.send_document(
                    chat_id=int(chat_id), document=f, caption=caption
                )

        asyncio.run_coroutine_threadsafe(_send(), self._loop).result(timeout=60)

    def start(self) -> None:
        max_retries = 10
        for attempt in range(1, max_retries + 1):
            try:
                logger.info("Telegram adapter started — polling for updates")
                self._app.run_polling(drop_pending_updates=True)
                return
            except telegram.error.Conflict:
                if attempt == max_retries:
                    raise
                wait = attempt * 3
                logger.warning("Conflict: previous instance still running. Retrying in %ds (attempt %d/%d)...", wait,
                               attempt, max_retries)
                time.sleep(wait)

    # --------------------------------------------------------------- handlers

    async def _on_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        msg = self._make_text_message(update, "/start")
        await update.message.reply_text(self._router.route(msg))

    async def _on_close(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = str(update.effective_chat.id)
        session_manager.clear_session(chat_id, Platform.TELEGRAM)
        await update.message.reply_text(
            "השיחה הסתיימה. בכל פעם שתזדקק/י לעזרה, פשוט שלח/י הודעה ונציג לך את התפריט."
        )

    async def _on_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        msg = self._make_text_message(update, update.message.text or "")
        await update.message.reply_text(self._router.route(msg))

    async def _on_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        tg_file = await update.message.document.get_file()
        data = bytes(await tg_file.download_as_bytearray())
        filename = update.message.document.file_name or "upload.pdf"
        local_path = self._files.save_bytes(data, filename)
        msg = self._build_message(
            update, MessageType.DOCUMENT, file_path=local_path, file_name=filename
        )
        await update.message.reply_text(self._router.route(msg))

    async def _on_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        photo = update.message.photo[-1]  # largest available size
        tg_file = await photo.get_file()
        data = bytes(await tg_file.download_as_bytearray())
        filename = f"{photo.file_id}.jpg"
        local_path = self._files.save_bytes(data, filename)
        msg = self._build_message(
            update, MessageType.PHOTO, file_path=local_path, file_name=filename
        )
        await update.message.reply_text(self._router.route(msg))

    # --------------------------------------------------------------- helpers

    def _make_text_message(self, update: Update, text: str) -> InternalMessage:
        return self._build_message(update, MessageType.TEXT, text=text)

    def _build_message(
            self,
            update: Update,
            message_type: MessageType,
            text: str | None = None,
            file_path: str | None = None,
            file_name: str | None = None,
    ) -> InternalMessage:
        return InternalMessage(
            platform=Platform.TELEGRAM,
            chat_id=str(update.effective_chat.id),
            message_type=message_type,
            text=text,
            file_path=file_path,
            file_name=file_name,
        )
