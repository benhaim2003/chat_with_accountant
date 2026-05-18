import json
import logging
from typing import TypedDict

logger = logging.getLogger(__name__)


# --- Type definitions ---

class ContactInfo(TypedDict):
    phone: str
    email: str


class ExpectedDocument(TypedDict):
    type: str
    label: str
    frequency: str


class Client(TypedDict):
    id: str
    name: str
    contact: ContactInfo
    expected_documents: list[ExpectedDocument]


class ReceivedDocument(TypedDict):
    type: str
    filename: str
    received_at: str


class ClientReceivedDocs(TypedDict):
    client_id: str
    month: str
    received: list[ReceivedDocument]


class MissingDocumentReport(TypedDict):
    client_id: str
    client_name: str
    contact: ContactInfo
    month: str
    missing_documents: list[ExpectedDocument]


# --- Data loaders ---

def load_clients(filepath: str) -> list[Client]:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            clients: list[Client] = json.load(f)
        logger.info("Loaded %d clients from %s", len(clients), filepath)
        return clients
    except FileNotFoundError:
        logger.error("Clients file not found: %s", filepath)
        raise
    except json.JSONDecodeError as e:
        logger.error("Failed to parse clients file %s: %s", filepath, e)
        raise


def load_received_docs(filepath: str) -> list[ClientReceivedDocs]:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            received_docs: list[ClientReceivedDocs] = json.load(f)
        logger.info("Loaded received docs for %d clients from %s", len(received_docs), filepath)
        return received_docs
    except FileNotFoundError:
        logger.error("Received docs file not found: %s", filepath)
        raise
    except json.JSONDecodeError as e:
        logger.error("Failed to parse received docs file %s: %s", filepath, e)
        raise


# --- Core comparison logic ---

def get_missing_documents(
    clients: list[Client],
    received_docs: list[ClientReceivedDocs],
    month: str,
) -> list[MissingDocumentReport]:
    # Build a lookup: client_id -> set of received doc types for the given month
    received_lookup: dict[str, set[str]] = {}
    for entry in received_docs:
        if entry["month"] == month:
            received_lookup[entry["client_id"]] = {
                doc["type"] for doc in entry["received"]
            }

    reports: list[MissingDocumentReport] = []

    for client in clients:
        client_id = client["id"]
        received_types = received_lookup.get(client_id, set())

        missing = [
            doc for doc in client["expected_documents"]
            if doc["type"] not in received_types
        ]

        if missing:
            logger.info(
                "Client %s (%s) is missing %d document(s) for %s",
                client_id, client["name"], len(missing), month,
            )
            reports.append(
                MissingDocumentReport(
                    client_id=client_id,
                    client_name=client["name"],
                    contact=client["contact"],
                    month=month,
                    missing_documents=missing,
                )
            )
        else:
            logger.info("Client %s (%s) has submitted all documents for %s", client_id, client["name"], month)

    return reports
