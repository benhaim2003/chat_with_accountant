import json
import pytest

from app.repositories.client_repository import ClientRepository


class TestLoadClients:
    def test_returns_clients(self, clients_json_file: str) -> None:
        repo = ClientRepository(clients_json_file, "")
        clients = repo.load_clients()
        assert len(clients) == 1
        assert clients[0].id == "C001"
        assert clients[0].name == "Levi Enterprises"
        assert len(clients[0].expected_documents) == 2

    def test_file_not_found_returns_empty(self) -> None:
        repo = ClientRepository("nonexistent.json", "")
        assert repo.load_clients() == []

    def test_invalid_json_returns_empty(self, tmp_path: pytest.TempPathFactory) -> None:
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not valid json", encoding="utf-8")
        repo = ClientRepository(str(bad_file), "")
        assert repo.load_clients() == []


class TestLoadReceivedDocs:
    def test_returns_received_docs(self, received_docs_json_file: str) -> None:
        repo = ClientRepository("", received_docs_json_file)
        docs = repo.load_received_docs()
        assert len(docs) == 1
        assert docs[0].client_id == "C001"
        assert docs[0].month == "2026-05"
        assert len(docs[0].received) == 2

    def test_file_not_found_returns_empty(self) -> None:
        repo = ClientRepository("", "nonexistent.json")
        assert repo.load_received_docs() == []


class TestGetMissingDocuments:
    def test_all_submitted_returns_no_report(self, tmp_path: pytest.TempPathFactory) -> None:
        clients = [
            {
                "id": "C001", "name": "Levi", "contact": {"phone": "123", "email": "a@b.com"},
                "expected_documents": [
                    {"type": "electricity_bill", "label": "Electricity Bill", "frequency": "monthly"},
                ],
            }
        ]
        received = [
            {"client_id": "C001", "month": "2026-05", "received": [
                {"type": "electricity_bill", "filename": "f.txt", "received_at": "2026-05-01"},
            ]},
        ]
        c_file = tmp_path / "c.json"
        r_file = tmp_path / "r.json"
        c_file.write_text(json.dumps(clients), encoding="utf-8")
        r_file.write_text(json.dumps(received), encoding="utf-8")

        repo = ClientRepository(str(c_file), str(r_file))
        reports = repo.get_missing_documents("2026-05")
        assert reports == []

    def test_missing_docs_creates_report(self, tmp_path: pytest.TempPathFactory) -> None:
        clients = [
            {
                "id": "C002", "name": "Goldberg Tech",
                "contact": {"phone": "456", "email": "g@t.com"},
                "expected_documents": [
                    {"type": "electricity_bill", "label": "Electricity Bill", "frequency": "monthly"},
                    {"type": "tax_invoice",      "label": "Tax Invoice",      "frequency": "monthly"},
                ],
            }
        ]
        received = [
            {"client_id": "C002", "month": "2026-05", "received": [
                {"type": "electricity_bill", "filename": "f.txt", "received_at": "2026-05-01"},
            ]},
        ]
        c_file = tmp_path / "c.json"
        r_file = tmp_path / "r.json"
        c_file.write_text(json.dumps(clients), encoding="utf-8")
        r_file.write_text(json.dumps(received), encoding="utf-8")

        repo = ClientRepository(str(c_file), str(r_file))
        reports = repo.get_missing_documents("2026-05")

        assert len(reports) == 1
        assert reports[0].client_id == "C002"
        assert len(reports[0].missing_documents) == 1
        assert reports[0].missing_documents[0].type == "tax_invoice"

    def test_client_with_no_received_entry_is_fully_missing(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        clients = [
            {
                "id": "C003", "name": "New Client",
                "contact": {"phone": "789", "email": "n@c.com"},
                "expected_documents": [
                    {"type": "bank_statement", "label": "Bank Statement", "frequency": "monthly"},
                ],
            }
        ]
        c_file = tmp_path / "c.json"
        r_file = tmp_path / "r.json"
        c_file.write_text(json.dumps(clients), encoding="utf-8")
        r_file.write_text("[]", encoding="utf-8")

        repo = ClientRepository(str(c_file), str(r_file))
        reports = repo.get_missing_documents("2026-05")

        assert len(reports) == 1
        assert reports[0].missing_documents[0].type == "bank_statement"

    def test_different_month_is_ignored(self, tmp_path: pytest.TempPathFactory) -> None:
        clients = [
            {
                "id": "C001", "name": "Levi",
                "contact": {"phone": "111", "email": "a@b.com"},
                "expected_documents": [
                    {"type": "electricity_bill", "label": "Electricity Bill", "frequency": "monthly"},
                ],
            }
        ]
        received = [
            {"client_id": "C001", "month": "2026-04", "received": [
                {"type": "electricity_bill", "filename": "f.txt", "received_at": "2026-04-01"},
            ]},
        ]
        c_file = tmp_path / "c.json"
        r_file = tmp_path / "r.json"
        c_file.write_text(json.dumps(clients), encoding="utf-8")
        r_file.write_text(json.dumps(received), encoding="utf-8")

        repo = ClientRepository(str(c_file), str(r_file))
        reports = repo.get_missing_documents("2026-05")

        assert len(reports) == 1
        assert reports[0].missing_documents[0].type == "electricity_bill"
