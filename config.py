import logging
import os
from datetime import datetime


# --- File paths ---
CLIENTS_FILE: str = "data/clients.json"
RECEIVED_DOCS_FILE: str = "data/received_docs.json"
DUMMY_FILES_DIR: str = "dummy_files"

# --- Current reporting period ---
# Defaults to the current month (YYYY-MM). Override by setting the
# CURRENT_MONTH environment variable, e.g. CURRENT_MONTH=2026-04
CURRENT_MONTH: str = os.environ.get(
    "CURRENT_MONTH", datetime.now().strftime("%Y-%m")
)

# --- Notification mode ---
# Set USE_MOCK=false in the environment to switch to the real WhatsApp sender.
USE_MOCK: bool = os.environ.get("USE_MOCK", "true").lower() == "true"

# --- Twilio credentials (only required when USE_MOCK=false) ---
TWILIO_ACCOUNT_SID: str = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN: str = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM: str = os.environ.get(
    "TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886"
)

# --- Logging ---
_LOG_LEVEL_NAME: str = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_LEVEL: int = getattr(logging, _LOG_LEVEL_NAME, logging.INFO)


def configure_logging() -> None:
    logging.basicConfig(level=LOG_LEVEL, format="%(levelname)s - %(message)s")
