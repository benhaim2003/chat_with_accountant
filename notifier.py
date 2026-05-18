import logging
from data_manager import MissingDocumentReport

logger = logging.getLogger(__name__)


def format_message(report: MissingDocumentReport) -> str:
    missing_list = "\n".join(
        f"  - {doc['label']}" for doc in report["missing_documents"]
    )
    return (
        f"Hello {report['client_name']},\n\n"
        f"This is a friendly reminder from your accountant.\n"
        f"We are still missing the following documents for {report['month']}:\n\n"
        f"{missing_list}\n\n"
        f"Please send them at your earliest convenience.\n"
        f"Thank you!"
    )


def _send_mock(phone: str, message: str) -> bool:
    logger.info("--- [MOCK] Sending message to %s ---\n%s\n---", phone, message)
    return True


def _send_whatsapp(phone: str, message: str) -> bool:
    # --- Plug Twilio in here when ready ---
    # from twilio.rest import Client
    # client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    # client.messages.create(
    #     from_="whatsapp:+14155238886",
    #     to=f"whatsapp:{phone}",
    #     body=message,
    # )
    raise NotImplementedError("Twilio WhatsApp sender not configured yet.")


def send_notification(report: MissingDocumentReport, use_mock: bool = True) -> bool:
    phone = report["contact"]["phone"]
    message = format_message(report)
    try:
        if use_mock:
            return _send_mock(phone, message)
        return _send_whatsapp(phone, message)
    except NotImplementedError:
        logger.error("Real sender not configured. Switch use_mock=True or set up Twilio.")
        return False
    except Exception as e:
        logger.error("Failed to send notification to %s: %s", phone, e)
        return False


def notify_all(reports: list[MissingDocumentReport], use_mock: bool = True) -> None:
    if not reports:
        logger.info("No reminders to send.")
        return

    success_count = 0
    for report in reports:
        sent = send_notification(report, use_mock=use_mock)
        if sent:
            success_count += 1

    logger.info("Sent %d/%d reminders.", success_count, len(reports))
