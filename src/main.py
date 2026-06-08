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
    def on_secretary_reply(chat_id: str, text: str, attachments: list[str]) -> None:
        logger.info("Forwarding secretary reply to chat %s", chat_id)
        adapter.send_text(chat_id, f"הודעה ממשרד רואה החשבון שלך:\n\n{text}")
        for path in attachments:
            adapter.send_file(chat_id, path)

    email_gateway.set_reply_callback(on_secretary_reply)
    email_gateway.start_polling()

    adapter.start()   # blocking — runs until process is killed


if __name__ == "__main__":
    main()
