import logging
from data_manager import load_clients, load_received_docs, get_missing_documents
from notifier import notify_all

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

CLIENTS_FILE = "data/clients.json"
RECEIVED_DOCS_FILE = "data/received_docs.json"
CURRENT_MONTH = "2026-05"


def main() -> None:
    clients = load_clients(CLIENTS_FILE)
    received_docs = load_received_docs(RECEIVED_DOCS_FILE)

    reports = get_missing_documents(clients, received_docs, CURRENT_MONTH)

    if not reports:
        logging.info("All clients have submitted their documents for %s.", CURRENT_MONTH)
        return

    notify_all(reports, use_mock=True)


if __name__ == "__main__":
    main()
