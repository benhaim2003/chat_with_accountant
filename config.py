import logging
import os
from datetime import datetime

# --- File paths ---
CLIENTS_FILE: str = "data/clients.json"
RECEIVED_DOCS_FILE: str = "data/received_docs.json"
DUMMY_FILES_DIR: str = "dummy_files"

# --- Current reporting period ---
CURRENT_MONTH: str = os.environ.get(
    "CURRENT_MONTH", datetime.now().strftime("%Y-%m")
)

# --- Notification mode ---
USE_MOCK: bool = os.environ.get("USE_MOCK", "true").lower() == "true"

# --- Twilio credentials (only required when USE_MOCK=false) ---
TWILIO_ACCOUNT_SID: str = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN: str = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM: str = os.environ.get("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

# --- Logging ---
LOG_LEVEL: int = getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO)


def configure_logging() -> None:
    logging.basicConfig(level=LOG_LEVEL, format="%(levelname)s - %(message)s")
