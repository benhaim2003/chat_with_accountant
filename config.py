import logging
import os

# ── Telegram ──────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN: str = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# ── Email bridge ──────────────────────────────────────────────────────────────
SMTP_HOST: str = os.environ.get("SMTP_HOST", "")
SMTP_PORT: int = int(os.environ.get("SMTP_PORT", "587"))
IMAP_HOST: str = os.environ.get("IMAP_HOST", "")
IMAP_PORT: int = int(os.environ.get("IMAP_PORT", "993"))
EMAIL_USERNAME: str = os.environ.get("EMAIL_USERNAME", "")
EMAIL_PASSWORD: str = os.environ.get("EMAIL_PASSWORD", "")
SECRETARIAT_EMAIL: str = os.environ.get("SECRETARIAT_EMAIL", "")
EMAIL_POLL_INTERVAL: int = int(os.environ.get("EMAIL_POLL_INTERVAL", "30"))

# ── Client data ───────────────────────────────────────────────────────────────
CLIENTS_FILE: str = "data/clients.json"

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL: int = getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO)


def configure_logging() -> None:
    logging.basicConfig(level=LOG_LEVEL, format="%(levelname)s - %(message)s")
