from __future__ import annotations
import logging
import os

from dotenv import load_dotenv
load_dotenv()

import config
config.configure_logging()
logger = logging.getLogger(__name__)

from src.adapters.telegram_adapter import TelegramAdapter
from src.core.menu_handler import MenuHandler
from src.core.message_router import MessageRouter
from src.services.email_gateway import EmailGateway
from src.services.file_handler import FileHandler


def _build_email_gateway() -> EmailGateway:
    return EmailGateway(
        smtp_host=os.environ.get("SMTP_HOST", ""),
        smtp_port=int(os.environ.get("SMTP_PORT", "587")),
        imap_host=os.environ.get("IMAP_HOST", ""),
        imap_port=int(os.environ.get("IMAP_PORT", "993")),
        username=os.environ.get("EMAIL_USERNAME", ""),
        password=os.environ.get("EMAIL_PASSWORD", ""),
        secretariat_address=os.environ.get("SECRETARIAT_EMAIL", ""),
    )


def main() -> None:
    logger.info("=== CPA Bot starting ===")

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise EnvironmentError("TELEGRAM_BOT_TOKEN is not set. Add it to your .env file.")

    email_gateway = _build_email_gateway()
    file_handler = FileHandler()
    menu_handler = MenuHandler(email_gateway=email_gateway, file_handler=file_handler)
    router = MessageRouter(menu_handler=menu_handler)
    adapter = TelegramAdapter(token=token, router=router, file_handler=file_handler)

    # Wire the email reply callback: secretary replies → forwarded to client via Telegram
    def on_secretary_reply(chat_id: str, text: str, attachments: list[str], close_requested: bool) -> None:
        from src.core import session_manager
        from src.core.menu_handler import _SESSION_DECISION_TEXT
        logger.info("Forwarding secretary reply to chat %s (close_requested=%s)", chat_id, close_requested)

        if close_requested:
            adapter.send_text(chat_id, f"הודעה ממשרד רואה החשבון שלך:\n\n{text}\n\n{_SESSION_DECISION_TEXT}")
        else:
            adapter.send_text(chat_id, f"הודעה ממשרד רואה החשבון שלך:\n\n{text}")

        for path in attachments:
            adapter.send_file(chat_id, path)

        if close_requested:
            session_manager.set_state(chat_id, "awaiting_session_decision", "telegram")

    email_gateway.set_reply_callback(on_secretary_reply)
    email_gateway.start_polling()

    adapter.start()   # blocking — runs until process is killed


if __name__ == "__main__":
    main()
