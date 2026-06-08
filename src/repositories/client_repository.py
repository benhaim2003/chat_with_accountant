from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Optional

from src.models.client import Client

logger = logging.getLogger(__name__)


class ClientRepository:
    """Loads and queries clients from clients.json.

    MVP extension point: add lookup_by_phone() once phone-number auth is in place.
    """

    def __init__(self, clients_file: str = "data/clients.json") -> None:
        self._path = clients_file
        self._clients: list[Client] = []

    def load(self) -> list[Client]:
        raw = self._read_json()
        self._clients = [Client.from_dict(item) for item in raw]
        logger.info("Loaded %d clients", len(self._clients))
        return self._clients

    def get_by_id(self, client_id: str) -> Optional[Client]:
        return next((c for c in self._clients if c.id == client_id), None)

    # Phase 2: phone-number authentication
    def get_by_phone(self, phone: str) -> Optional[Client]:
        return next((c for c in self._clients if c.contact.phone == phone), None)

    def _read_json(self) -> list[dict]:
        try:
            with open(self._path, encoding="utf-8") as fh:
                return json.load(fh)
        except FileNotFoundError:
            logger.error("clients.json not found: %s", self._path)
            return []
        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON in %s: %s", self._path, exc)
            return []
