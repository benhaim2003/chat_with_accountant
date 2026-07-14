from abc import ABC, abstractmethod

from src.models.menu_response import MenuResponse


class PlatformAdapter(ABC):
    @abstractmethod
    def send_response(self, chat_id: str, response: MenuResponse) -> None: ...

    @abstractmethod
    def send_text(self, chat_id: str, text: str) -> None: ...

    @abstractmethod
    def send_file(self, chat_id: str, file_path: str, caption: str = "") -> None: ...

    @abstractmethod
    def start(self) -> None: ...
