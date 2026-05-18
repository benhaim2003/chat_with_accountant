from __future__ import annotations
import json
import logging

from app.models.client import Client
from app.models.document import ClientReceivedDocs, MissingDocumentReport

logger = logging.getLogger(__name__)


class ClientRepository:
    def __init__(self, clients_file: str, received_docs_file: str) -> None:
        self._clients_file = clients_file
        self._received_docs_file = received_docs_file

    def load_clients(self) -> list[Client]:
        return [Client.from_dict(raw) for raw in self._read_json(self._clients_file)]

    def load_received_docs(self) -> list[ClientReceivedDocs]:
        return [
            ClientReceivedDocs.from_dict(raw)
            for raw in self._read_json(self._received_docs_file)
        ]

    def get_missing_documents(self, month: str) -> list[MissingDocumentReport]:
        clients = self.load_clients()
        received_docs = self.load_received_docs()

        received_by_client: dict[str, set[str]] = {
            entry.client_id: {doc.type for doc in entry.received}
            for entry in received_docs
            if entry.month == month
        }

        reports: list[MissingDocumentReport] = []
        for client in clients:
            submitted = received_by_client.get(client.id, set())
            missing = [
                doc for doc in client.expected_documents if doc.type not in submitted
            ]
            if missing:
                reports.append(
                    MissingDocumentReport(
                        client_id=client.id,
                        client_name=client.name,
                        contact=client.contact,
                        month=month,
                        missing_documents=missing,
                    )
                )

        logger.info(
            "%d/%d clients have missing documents for %s.",
            len(reports),
            len(clients),
            month,
        )
        return reports

    def _read_json(self, filepath: str) -> list[dict]:
        try:
            with open(filepath, encoding="utf-8") as fh:
                return json.load(fh)
        except FileNotFoundError:
            logger.error("Data file not found: %s", filepath)
            return []
        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON in %s: %s", filepath, exc)
            return []
