import logging
import os

import config
from app.classification.base import DocumentClassifier
from app.classification.factory import get_classifier
from app.classification.mock_classifier import MockClassifier
from app.classification.model_config import get_active_model
from app.repositories import ClientRepository, FileScanner
from app.notifications import MockSender, TwilioWhatsAppSender, Notifier

config.configure_logging()
logger = logging.getLogger(__name__)


def _build_classifier() -> DocumentClassifier:
    model = get_active_model()
    if os.environ.get(model.api_key_env, ""):
        logger.info("Using AnthropicClassifier (%s)", model.model_id)
        return get_classifier()
    logger.warning(
        "%s not set — falling back to MockClassifier (filename-based, no API calls)",
        model.api_key_env,
    )
    return MockClassifier()


def _build_sender():
    if config.USE_MOCK:
        return MockSender()
    return TwilioWhatsAppSender(
        account_sid=config.TWILIO_ACCOUNT_SID,
        auth_token=config.TWILIO_AUTH_TOKEN,
        from_number=config.TWILIO_WHATSAPP_FROM,
    )


def main() -> None:
    logger.info("=== Document Reminder Pipeline — %s ===", config.CURRENT_MONTH)

    # 1. Load expected documents for all clients
    repository = ClientRepository(config.CLIENTS_FILE, config.RECEIVED_DOCS_FILE)
    clients = repository.load_clients()
    logger.info("Loaded %d clients", len(clients))

    # 2. Scan dummy_files/, classify every PDF found
    classifier = _build_classifier()
    scanner = FileScanner(config.DUMMY_FILES_DIR, classifier)
    received_docs = scanner.build_received_docs(clients, config.CURRENT_MONTH)

    # 3. Compare received vs expected → missing documents
    reports = repository.compute_missing(clients, received_docs, config.CURRENT_MONTH)

    if not reports:
        logger.info("All clients have submitted their documents for %s.", config.CURRENT_MONTH)
        return

    # 4. Send reminders for every client that has missing docs
    notifier = Notifier(_build_sender())
    notifier.notify_all(reports)


if __name__ == "__main__":
    main()
