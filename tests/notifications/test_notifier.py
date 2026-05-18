from unittest.mock import MagicMock, patch
import logging
import pytest

from app.notifications.notifier import Notifier
from app.notifications.base import NotificationSender
from app.models.document import MissingDocumentReport
from app.models.client import Contact, ExpectedDocument


@pytest.fixture
def mock_sender() -> MagicMock:
    sender = MagicMock(spec=NotificationSender)
    sender.send.return_value = True
    return sender


@pytest.fixture
def notifier(mock_sender: MagicMock) -> Notifier:
    return Notifier(mock_sender)


@pytest.fixture
def report(missing_report: MissingDocumentReport) -> MissingDocumentReport:
    return missing_report


class TestFormatMessage:
    def test_contains_client_name(self, notifier: Notifier, report: MissingDocumentReport) -> None:
        msg = notifier._format_message(report)
        assert "Levi Enterprises" in msg

    def test_contains_month(self, notifier: Notifier, report: MissingDocumentReport) -> None:
        msg = notifier._format_message(report)
        assert "2026-05" in msg

    def test_contains_all_missing_labels(self, notifier: Notifier, report: MissingDocumentReport) -> None:
        msg = notifier._format_message(report)
        for doc in report.missing_documents:
            assert doc.label in msg


class TestNotify:
    def test_success_calls_sender_and_returns_true(
        self, notifier: Notifier, mock_sender: MagicMock, report: MissingDocumentReport
    ) -> None:
        result = notifier.notify(report)
        assert result is True
        mock_sender.send.assert_called_once_with(
            report.contact.phone, notifier._format_message(report)
        )

    def test_sender_not_implemented_returns_false(
        self, report: MissingDocumentReport
    ) -> None:
        broken = MagicMock(spec=NotificationSender)
        broken.send.side_effect = NotImplementedError
        notifier = Notifier(broken)
        assert notifier.notify(report) is False

    def test_sender_raises_generic_exception_returns_false(
        self, report: MissingDocumentReport
    ) -> None:
        broken = MagicMock(spec=NotificationSender)
        broken.send.side_effect = RuntimeError("network error")
        notifier = Notifier(broken)
        assert notifier.notify(report) is False


class TestNotifyAll:
    def test_notifies_each_report(
        self, notifier: Notifier, mock_sender: MagicMock, report: MissingDocumentReport
    ) -> None:
        notifier.notify_all([report, report])
        assert mock_sender.send.call_count == 2

    def test_empty_list_sends_nothing(
        self, notifier: Notifier, mock_sender: MagicMock
    ) -> None:
        notifier.notify_all([])
        mock_sender.send.assert_not_called()

    def test_logs_success_count(
        self, notifier: Notifier, report: MissingDocumentReport, caplog
    ) -> None:
        with caplog.at_level(logging.INFO):
            notifier.notify_all([report])
        assert "1/1" in caplog.text
