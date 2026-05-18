import logging
from unittest.mock import MagicMock

import pytest

from app.pipeline.report_pipeline import ReportPipeline
from app.repositories.client_repository import ClientRepository
from app.notifications.notifier import Notifier
from app.models.document import MissingDocumentReport


@pytest.fixture
def mock_repo() -> MagicMock:
    return MagicMock(spec=ClientRepository)


@pytest.fixture
def mock_notifier() -> MagicMock:
    return MagicMock(spec=Notifier)


@pytest.fixture
def pipeline(mock_repo: MagicMock, mock_notifier: MagicMock) -> ReportPipeline:
    return ReportPipeline(mock_repo, mock_notifier)


class TestReportPipeline:
    def test_run_with_reports_calls_notify_all(
        self,
        pipeline: ReportPipeline,
        mock_repo: MagicMock,
        mock_notifier: MagicMock,
        missing_report: MissingDocumentReport,
    ) -> None:
        mock_repo.get_missing_documents.return_value = [missing_report]
        pipeline.run("2026-05")
        mock_notifier.notify_all.assert_called_once_with([missing_report])

    def test_run_with_no_reports_skips_notifications(
        self,
        pipeline: ReportPipeline,
        mock_repo: MagicMock,
        mock_notifier: MagicMock,
    ) -> None:
        mock_repo.get_missing_documents.return_value = []
        pipeline.run("2026-05")
        mock_notifier.notify_all.assert_not_called()

    def test_run_passes_month_to_repository(
        self,
        pipeline: ReportPipeline,
        mock_repo: MagicMock,
    ) -> None:
        mock_repo.get_missing_documents.return_value = []
        pipeline.run("2026-05")
        mock_repo.get_missing_documents.assert_called_once_with("2026-05")

    def test_run_logs_when_no_reports(
        self,
        pipeline: ReportPipeline,
        mock_repo: MagicMock,
        caplog,
    ) -> None:
        mock_repo.get_missing_documents.return_value = []
        with caplog.at_level(logging.INFO):
            pipeline.run("2026-05")
        assert "2026-05" in caplog.text
