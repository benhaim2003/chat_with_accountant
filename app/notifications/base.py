from abc import ABC, abstractmethod


class NotificationSender(ABC):
    @abstractmethod
    def send(self, phone: str, message: str) -> bool:
        """Send a message to the given phone number. Return True on success."""
