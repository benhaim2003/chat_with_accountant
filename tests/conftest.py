import json
import pytest

from app.models.client import Client, Contact, ExpectedDocument
from app.models.document import ReceivedDocument, ClientReceivedDocs, MissingDocumentReport


# ---------------------------------------------------------------------------
# Raw dict fixtures (match the JSON schema on disk)
# ---------------------------------------------------------------------------

@pytest.fixture
def contact_dict() -> dict:
    return {"phone": "+972501111111", "email": "info@levi.co.il"}


@pytest.fixture
def expected_doc_dict() -> dict:
    return {"type": "electricity_bill", "label": "Electricity Bill", "frequency": "monthly"}


@pytest.fixture
def client_dict(contact_dict: dict) -> dict:
    return {
        "id": "C001",
        "name": "Levi Enterprises",
        "contact": contact_dict,
        "expected_documents": [
            {"type": "electricity_bill", "label": "Electricity Bill", "frequency": "monthly"},
            {"type": "bank_statement",   "label": "Bank Statement",   "frequency": "monthly"},
        ],
    }


@pytest.fixture
def received_docs_dict() -> dict:
    return {
        "client_id": "C001",
        "month": "2026-05",
        "received": [
            {"type": "electricity_bill", "filename": "electricity_bill_2026_05.txt", "received_at": "2026-05-02"},
            {"type": "bank_statement",   "filename": "bank_statement_2026_05.txt",   "received_at": "2026-05-03"},
        ],
    }


# ---------------------------------------------------------------------------
# Domain object fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def contact() -> Contact:
    return Contact(phone="+972501111111", email="info@levi.co.il")


@pytest.fixture
def expected_docs() -> list[ExpectedDocument]:
    return [
        ExpectedDocument(type="electricity_bill", label="Electricity Bill", frequency="monthly"),
        ExpectedDocument(type="bank_statement",   label="Bank Statement",   frequency="monthly"),
    ]


@pytest.fixture
def client(contact: Contact, expected_docs: list[ExpectedDocument]) -> Client:
    return Client(id="C001", name="Levi Enterprises", contact=contact, expected_documents=expected_docs)


@pytest.fixture
def missing_report(contact: Contact, expected_docs: list[ExpectedDocument]) -> MissingDocumentReport:
    return MissingDocumentReport(
        client_id="C001",
        client_name="Levi Enterprises",
        contact=contact,
        month="2026-05",
        missing_documents=expected_docs,
    )


# ---------------------------------------------------------------------------
# Temp JSON file helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def clients_json_file(tmp_path: pytest.TempPathFactory, client_dict: dict):
    path = tmp_path / "clients.json"
    path.write_text(json.dumps([client_dict]), encoding="utf-8")
    return str(path)


@pytest.fixture
def received_docs_json_file(tmp_path: pytest.TempPathFactory, received_docs_dict: dict):
    path = tmp_path / "received_docs.json"
    path.write_text(json.dumps([received_docs_dict]), encoding="utf-8")
    return str(path)
