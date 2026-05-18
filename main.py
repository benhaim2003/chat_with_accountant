import logging
import config
from data_manager import load_clients, load_received_docs, get_missing_documents
from notifier import notify_all

config.configure_logging()


def main() -> None:
    clients = load_clients(config.CLIENTS_FILE)
    received_docs = load_received_docs(config.RECEIVED_DOCS_FILE)

    reports = get_missing_documents(clients, received_docs, config.CURRENT_MONTH)

    if not reports:
        logging.info("All clients have submitted their documents for %s.", config.CURRENT_MONTH)
        return

    notify_all(reports, use_mock=config.USE_MOCK)


if __name__ == "__main__":
    main()
