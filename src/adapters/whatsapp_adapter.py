# MVP placeholder — WhatsApp adapter (Phase 2).
# Implement send_text / send_file / start using Twilio or WhatsApp Cloud API.
from src.adapters.base import PlatformAdapter


class WhatsAppAdapter(PlatformAdapter):
    def send_text(self, chat_id: str, text: str) -> None:
        raise NotImplementedError("WhatsApp adapter is not yet implemented (Phase 2).")

    def send_file(self, chat_id: str, file_path: str, caption: str = "") -> None:
        raise NotImplementedError("WhatsApp adapter is not yet implemented (Phase 2).")

    def start(self) -> None:
        raise NotImplementedError("WhatsApp adapter is not yet implemented (Phase 2).")
