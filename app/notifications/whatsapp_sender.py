import logging

from app.notifications.base import NotificationSender

logger = logging.getLogger(__name__)


class TwilioWhatsAppSender(NotificationSender):
    def __init__(self, account_sid: str, auth_token: str, from_number: str) -> None:
        self._account_sid = account_sid
        self._auth_token = auth_token
        self._from_number = from_number

    def send(self, phone: str, message: str) -> bool:
        # --- Uncomment when Twilio is configured ---
        # from twilio.rest import Client
        # client = Client(self._account_sid, self._auth_token)
        # client.messages.create(
        #     from_=f"whatsapp:{self._from_number}",
        #     to=f"whatsapp:{phone}",
        #     body=message,
        # )
        # return True
        raise NotImplementedError(
            "Twilio WhatsApp sender not configured yet. "
            "Uncomment the Twilio block and add twilio to requirements.txt."
        )
