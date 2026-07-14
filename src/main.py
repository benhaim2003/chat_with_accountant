from __future__ import annotations

import logging

from dotenv import load_dotenv

load_dotenv()

from src.settings import Settings, configure_logging

settings = Settings.from_env()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

from src.adapters.base import PlatformAdapter
from src.adapters.telegram_adapter import TelegramAdapter
from src.adapters.whatsapp_adapter import WhatsAppAdapter
from src.core import texts
from src.core.menu_handler import MenuHandler
from src.core.message_router import MessageRouter
from src.services.email_gateway import GraphEmailGateway
from src.services.file_handler import FileHandler


def build_adapters(router: MessageRouter, file_handler: FileHandler) -> dict[str, PlatformAdapter]:
    adapters: dict[str, PlatformAdapter] = {
        "telegram": TelegramAdapter(
            token=settings.telegram_token, router=router, file_handler=file_handler
        ),
    }
    if settings.whatsapp_enabled:
        adapters["whatsapp"] = WhatsAppAdapter(
            token=settings.whatsapp_token,
            phone_number_id=settings.whatsapp_phone_number_id,
            verify_token=settings.whatsapp_verify_token,
            router=router,
            file_handler=file_handler,
        )
    return adapters


def make_reply_forwarder(adapters: dict[str, PlatformAdapter]):
    def on_secretary_reply(platform: str, chat_id: str, text: str, attachments: list[str]) -> None:
        logger.info("Forwarding reply to %s:%s", platform, chat_id)
        adapter = adapters.get(platform, adapters["telegram"])

        if text:
            adapter.send_text(chat_id, f"{texts.SECRETARY_REPLY_PREFIX}\n\n{text}")

        failed = 0
        for path in attachments:
            try:
                adapter.send_file(chat_id, path)
            except Exception as exc:
                failed += 1
                logger.error("Failed to deliver attachment %s to %s:%s — %s", path, platform, chat_id, exc)

        if failed:
            adapter.send_text(chat_id, texts.attachments_failed(failed, len(attachments)))

    return on_secretary_reply


def main() -> None:
    logger.info("=== CPA Bot starting ===")

    if not settings.telegram_token:
        raise EnvironmentError("TELEGRAM_BOT_TOKEN is not set.")

    email_gateway = GraphEmailGateway(
        tenant_id=settings.azure_tenant_id,
        client_id=settings.azure_client_id,
        client_secret=settings.azure_client_secret,
        mailbox=settings.mailbox,
        secretariat_address=settings.secretariat_email,
    )
    file_handler = FileHandler()
    router = MessageRouter(MenuHandler(email_gateway))
    adapters = build_adapters(router, file_handler)

    email_gateway.set_reply_callback(make_reply_forwarder(adapters))
    email_gateway.start_polling(settings.email_poll_interval)

    whatsapp = adapters.get("whatsapp")
    if whatsapp:
        whatsapp.start()

    adapters["telegram"].start()  # blocking — must start last


if __name__ == "__main__":
    main()
