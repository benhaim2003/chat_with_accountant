from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Contact:
    phone: str
    email: str

    @classmethod
    def from_dict(cls, data: dict) -> Contact:
        return cls(phone=data["phone"], email=data["email"])


@dataclass
class Client:
    id: str
    name: str
    contact: Contact

    @classmethod
    def from_dict(cls, data: dict) -> Client:
        return cls(
            id=data["id"],
            name=data["name"],
            contact=Contact.from_dict(data["contact"]),
        )
