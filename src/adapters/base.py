from abc import ABC, abstractmethod

from src.models.menu_response import MenuResponse


class PlatformAdapter(ABC):
    @abstractmethod
    def send_response(self, chat_id: str, response: MenuResponse) -> None:
        """Send a structured response (text + optional buttons) to the user."""

    @abstractmethod
    def send_text(self, chat_id: str, text: str) -> None:
        """Send a plain-text message to the user."""

    @abstractmethod
    def send_file(self, chat_id: str, file_path: str, caption: str = "") -> None:
        """Send a file to the user."""

    @abstractmethod
    def start(self) -> None:
        """Start listening for incoming messages (blocking)."""
