from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Contact:
    phone: str
    email: str

    @classmethod
    def from_dict(cls, data: dict) -> Contact:
        return cls(phone=data["phone"], email=data["email"])


@dataclass(frozen=True)
class ExpectedDocument:
    type: str
    label: str
    frequency: str

    @classmethod
    def from_dict(cls, data: dict) -> ExpectedDocument:
        return cls(type=data["type"], label=data["label"], frequency=data["frequency"])


@dataclass
class Client:
    id: str
    name: str
    contact: Contact
    expected_documents: list[ExpectedDocument]

    @classmethod
    def from_dict(cls, data: dict) -> Client:
        return cls(
            id=data["id"],
            name=data["name"],
            contact=Contact.from_dict(data["contact"]),
            expected_documents=[
                ExpectedDocument.from_dict(doc)
                for doc in data.get("expected_documents", [])
            ],
        )
