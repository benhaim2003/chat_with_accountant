from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class UserSession:
    chat_id: str
    platform: str
    # Populated in MVP via phone-number authentication
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    phone: Optional[str] = None
    # Tracks the email thread for routing secretary replies back to this user
    active_thread_id: Optional[str] = None
    # Conversation state machine
    state: str = "idle"
    context: dict = field(default_factory=dict)
