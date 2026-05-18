from app.models.document import ReceivedDocument, ClientReceivedDocs, MissingDocumentReport
from app.models.client import Contact, ExpectedDocument


class TestReceivedDocument:
    def test_from_dict(self) -> None:
        raw = {"type": "bank_statement", "filename": "bank_2026_05.txt", "received_at": "2026-05-03"}
        doc = ReceivedDocument.from_dict(raw)
        assert doc.type == "bank_statement"
        assert doc.filename == "bank_2026_05.txt"
        assert doc.received_at == "2026-05-03"


class TestClientReceivedDocs:
    def test_from_dict(self, received_docs_dict: dict) -> None:
        entry = ClientReceivedDocs.from_dict(received_docs_dict)
        assert entry.client_id == "C001"
        assert entry.month == "2026-05"
        assert len(entry.received) == 2
        assert entry.received[0].type == "electricity_bill"

    def test_from_dict_empty_received(self) -> None:
        raw = {"client_id": "C002", "month": "2026-05"}
        entry = ClientReceivedDocs.from_dict(raw)
        assert entry.received == []


class TestMissingDocumentReport:
    def test_defaults_to_empty_missing_list(self, contact: Contact) -> None:
        report = MissingDocumentReport(
            client_id="C001",
            client_name="Levi Enterprises",
            contact=contact,
            month="2026-05",
        )
        assert report.missing_documents == []

    def test_stores_missing_documents(self, missing_report: MissingDocumentReport) -> None:
        assert len(missing_report.missing_documents) == 2
        assert missing_report.missing_documents[0].type == "electricity_bill"
