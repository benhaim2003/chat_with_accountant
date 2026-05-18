import logging

from app.models.document import MissingDocumentReport
from app.notifications.base import NotificationSender

logger = logging.getLogger(__name__)


class Notifier:
    def __init__(self, sender: NotificationSender) -> None:
        self._sender = sender

    def notify(self, report: MissingDocumentReport) -> bool:
        message = self._format_message(report)
        try:
            return self._sender.send(report.contact.phone, message)
        except NotImplementedError:
            logger.error(
                "Sender not configured for client %s. Switch to MockSender or set up Twilio.",
                report.client_id,
            )
            return False
        except Exception as exc:
            logger.error("Failed to notify client %s: %s", report.client_id, exc)
            return False

    def notify_all(self, reports: list[MissingDocumentReport]) -> None:
        if not reports:
            logger.info("No reminders to send.")
            return
        success = sum(1 for report in reports if self.notify(report))
        logger.info("Sent %d/%d reminders.", success, len(reports))

    def _format_message(self, report: MissingDocumentReport) -> str:
        missing_list = "\n".join(
            f"  - {doc.label}" for doc in report.missing_documents
        )
        return (
            f"Hello {report.client_name},\n\n"
            f"This is a friendly reminder from your accountant.\n"
            f"We are still missing the following documents for {report.month}:\n\n"
            f"{missing_list}\n\n"
            f"Please send them at your earliest convenience.\n"
            f"Thank you!"
        )
