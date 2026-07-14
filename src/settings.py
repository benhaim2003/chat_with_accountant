from __future__ import annotations

import logging
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    telegram_token: str
    azure_tenant_id: str
    azure_client_id: str
    azure_client_secret: str
    mailbox: str
    secretariat_email: str
    email_poll_interval: int
    whatsapp_token: str
    whatsapp_phone_number_id: str
    whatsapp_verify_token: str
    log_level: str

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            telegram_token=os.environ.get("TELEGRAM_BOT_TOKEN", ""),
            azure_tenant_id=os.environ.get("AZURE_TENANT_ID", ""),
            azure_client_id=os.environ.get("AZURE_CLIENT_ID", ""),
            azure_client_secret=os.environ.get("AZURE_CLIENT_SECRET", ""),
            mailbox=os.environ.get("EMAIL_USERNAME", ""),
            secretariat_email=os.environ.get("SECRETARIAT_EMAIL", ""),
            email_poll_interval=int(os.environ.get("EMAIL_POLL_INTERVAL", "30")),
            whatsapp_token=os.environ.get("WHATSAPP_TOKEN", ""),
            whatsapp_phone_number_id=os.environ.get("WHATSAPP_PHONE_NUMBER_ID", ""),
            whatsapp_verify_token=os.environ.get("WHATSAPP_VERIFY_TOKEN", ""),
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
        )

    @property
    def whatsapp_enabled(self) -> bool:
        return bool(self.whatsapp_token and self.whatsapp_phone_number_id and self.whatsapp_verify_token)


def configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(levelname)s - %(message)s")
