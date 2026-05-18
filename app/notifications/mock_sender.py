import logging

from app.notifications.base import NotificationSender

logger = logging.getLogger(__name__)


class MockSender(NotificationSender):
    def send(self, phone: str, message: str) -> bool:
        logger.info("--- [MOCK] Sending message to %s ---\n%s\n---", phone, message)
        return True
