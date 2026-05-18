from __future__ import annotations
from dataclasses import dataclass, field

from app.models.client import Contact, ExpectedDocument


@dataclass
class ReceivedDocument:
    type: str
    filename: str
    received_at: str

    @classmethod
    def from_dict(cls, data: dict) -> ReceivedDocument:
        return cls(
            type=data["type"],
            filename=data["filename"],
            received_at=data["received_at"],
        )


@dataclass
class ClientReceivedDocs:
    client_id: str
    month: str
    received: list[ReceivedDocument] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> ClientReceivedDocs:
        return cls(
            client_id=data["client_id"],
            month=data["month"],
            received=[ReceivedDocument.from_dict(doc) for doc in data.get("received", [])],
        )


@dataclass
class MissingDocumentReport:
    client_id: str
    client_name: str
    contact: Contact
    month: str
    missing_documents: list[ExpectedDocument] = field(default_factory=list)
