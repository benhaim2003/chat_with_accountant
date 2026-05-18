import logging

from app.repositories.client_repository import ClientRepository
from app.notifications.notifier import Notifier

logger = logging.getLogger(__name__)


class ReportPipeline:
    def __init__(self, repository: ClientRepository, notifier: Notifier) -> None:
        self._repository = repository
        self._notifier = notifier

    def run(self, month: str) -> None:
        reports = self._repository.get_missing_documents(month)
        if not reports:
            logger.info("All clients have submitted their documents for %s.", month)
            return
        self._notifier.notify_all(reports)
