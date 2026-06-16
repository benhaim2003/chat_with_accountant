from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class UserSession:
    chat_id: str
    platform: str
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    phone: Optional[str] = None
    active_thread_id: Optional[str] = None
    state: str = "idle"
    context: dict = field(default_factory=dict)
