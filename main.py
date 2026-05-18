import config
from app.repositories import ClientRepository
from app.notifications import MockSender, TwilioWhatsAppSender, Notifier
from app.pipeline import ReportPipeline

config.configure_logging()


def main() -> None:
    repository = ClientRepository(config.CLIENTS_FILE, config.RECEIVED_DOCS_FILE)

    sender = (
        MockSender()
        if config.USE_MOCK
        else TwilioWhatsAppSender(
            account_sid=config.TWILIO_ACCOUNT_SID,
            auth_token=config.TWILIO_AUTH_TOKEN,
            from_number=config.TWILIO_WHATSAPP_FROM,
        )
    )

    notifier = Notifier(sender)
    pipeline = ReportPipeline(repository, notifier)
    pipeline.run(config.CURRENT_MONTH)


if __name__ == "__main__":
    main()
