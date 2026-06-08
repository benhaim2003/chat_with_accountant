import logging
import os
from datetime import datetime

# --- File paths ---
CLIENTS_FILE: str = "data/clients.json"
RECEIVED_DOCS_FILE: str = "data/received_docs.json"
DUMMY_FILES_DIR: str = "dummy_files"

# --- Current reporting period (used by pipeline.py) ---
CURRENT_MONTH: str = os.environ.get(
    "CURRENT_MONTH", datetime.now().strftime("%Y-%m")
)

# --- Telegram ---
TELEGRAM_BOT_TOKEN: str = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# --- Email bridge ---
SMTP_HOST: str = os.environ.get("SMTP_HOST", "")
SMTP_PORT: int = int(os.environ.get("SMTP_PORT", "587"))
IMAP_HOST: str = os.environ.get("IMAP_HOST", "")
IMAP_PORT: int = int(os.environ.get("IMAP_PORT", "993"))
EMAIL_USERNAME: str = os.environ.get("EMAIL_USERNAME", "")
EMAIL_PASSWORD: str = os.environ.get("EMAIL_PASSWORD", "")
SECRETARIAT_EMAIL: str = os.environ.get("SECRETARIAT_EMAIL", "")
EMAIL_POLL_INTERVAL: int = int(os.environ.get("EMAIL_POLL_INTERVAL", "30"))

# --- Notification mode (used by pipeline.py) ---
USE_MOCK: bool = os.environ.get("USE_MOCK", "true").lower() == "true"

# --- Twilio credentials (used by pipeline.py when USE_MOCK=false) ---
TWILIO_ACCOUNT_SID: str = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN: str = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM: str = os.environ.get("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

# --- Logging ---
LOG_LEVEL: int = getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO)


def configure_logging() -> None:
    logging.basicConfig(level=LOG_LEVEL, format="%(levelname)s - %(message)s")
