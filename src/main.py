from __future__ import annotations
import logging
import os

from dotenv import load_dotenv
load_dotenv()

import config
config.configure_logging()
logger = logging.getLogger(__name__)

from src.adapters.telegram_adapter import TelegramAdapter
from src.adapters.whatsapp_adapter import WhatsAppAdapter
from src.core.menu_handler import MenuHandler, _SESSION_DECISION_TEXT
from src.core.message_router import MessageRouter
from src.services.email_gateway import GraphEmailGateway
from src.services.file_handler import FileHandler


def _build_email_gateway() -> GraphEmailGateway:
    return GraphEmailGateway(
        tenant_id=os.environ.get("AZURE_TENANT_ID", ""),
        client_id=os.environ.get("AZURE_CLIENT_ID", ""),
        client_secret=os.environ.get("AZURE_CLIENT_SECRET", ""),
        mailbox=os.environ.get("EMAIL_USERNAME", ""),
        secretariat_address=os.environ.get("SECRETARIAT_EMAIL", ""),
    )


def main() -> None:
    logger.info("=== CPA Bot starting ===")

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise EnvironmentError("TELEGRAM_BOT_TOKEN is not set.")

    email_gateway = _build_email_gateway()
    file_handler = FileHandler()
    menu_handler = MenuHandler(email_gateway=email_gateway, file_handler=file_handler)
    router = MessageRouter(menu_handler=menu_handler)

    telegram_adapter = TelegramAdapter(token=token, router=router, file_handler=file_handler)

    wa_token = os.environ.get("WHATSAPP_TOKEN", "")
    whatsapp_adapter: WhatsAppAdapter | None = None
    if wa_token:
        whatsapp_adapter = WhatsAppAdapter(
            token=wa_token,
            phone_number_id=os.environ.get("WHATSAPP_PHONE_NUMBER_ID", ""),
            verify_token=os.environ.get("WHATSAPP_VERIFY_TOKEN", ""),
            router=router,
            file_handler=file_handler,
        )

    def on_secretary_reply(
        platform: str,
        chat_id: str,
        text: str,
        attachments: list[str],
        close_requested: bool,
    ) -> None:
        from src.core import session_manager

        logger.info("Forwarding reply to %s:%s (close=%s)", platform, chat_id, close_requested)

        adapter = whatsapp_adapter if platform == "whatsapp" and whatsapp_adapter else telegram_adapter

        if close_requested:
            body = f"הודעה ממשרד רואה החשבון שלך:\n\n{text}\n\n{_SESSION_DECISION_TEXT}" if text else _SESSION_DECISION_TEXT
            adapter.send_text(chat_id, body)
        elif text:
            adapter.send_text(chat_id, f"הודעה ממשרד רואה החשבון שלך:\n\n{text}")

        for path in attachments:
            adapter.send_file(chat_id, path)

        if close_requested:
            session_manager.set_state(chat_id, "awaiting_session_decision", platform)

    email_gateway.set_reply_callback(on_secretary_reply)
    email_gateway.start_polling()

    if whatsapp_adapter:
        whatsapp_adapter.start()  # non-blocking — runs uvicorn in a daemon thread

    telegram_adapter.start()  # blocking — runs until process is killed


if __name__ == "__main__":
    main()
