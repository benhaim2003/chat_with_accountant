from __future__ import annotations
import logging
from src.models.internal_message import InternalMessage
from src.core.menu_handler import MenuHandler

logger = logging.getLogger(__name__)


class MessageRouter:
    def __init__(self, menu_handler: MenuHandler) -> None:
        self._menu = menu_handler

    def route(self, message: InternalMessage) -> str:
        logger.info(
            "Message from %s:%s  type=%s",
            message.platform,
            message.chat_id,
            message.message_type,
        )
        return self._menu.handle(message)
