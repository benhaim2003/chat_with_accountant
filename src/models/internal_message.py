from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Platform(str, Enum):
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"


class MessageType(str, Enum):
    TEXT = "text"
    DOCUMENT = "document"
    PHOTO = "photo"


@dataclass
class InternalMessage:
    platform: Platform
    chat_id: str
    message_type: MessageType
    text: Optional[str] = None
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    raw: Optional[dict] = None
