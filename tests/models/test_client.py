import pytest
from app.models.client import Client, Contact, ExpectedDocument


class TestContact:
    def test_from_dict(self, contact_dict: dict) -> None:
        c = Contact.from_dict(contact_dict)
        assert c.phone == "+972501111111"
        assert c.email == "info@levi.co.il"

    def test_frozen(self, contact: Contact) -> None:
        with pytest.raises(Exception):
            contact.phone = "new"  # type: ignore[misc]


class TestExpectedDocument:
    def test_from_dict(self, expected_doc_dict: dict) -> None:
        doc = ExpectedDocument.from_dict(expected_doc_dict)
        assert doc.type == "electricity_bill"
        assert doc.label == "Electricity Bill"
        assert doc.frequency == "monthly"

    def test_frozen(self, expected_doc_dict: dict) -> None:
        doc = ExpectedDocument.from_dict(expected_doc_dict)
        with pytest.raises(Exception):
            doc.type = "other"  # type: ignore[misc]


class TestClient:
    def test_from_dict(self, client_dict: dict) -> None:
        client = Client.from_dict(client_dict)
        assert client.id == "C001"
        assert client.name == "Levi Enterprises"
        assert client.contact.phone == "+972501111111"
        assert len(client.expected_documents) == 2
        assert client.expected_documents[0].type == "electricity_bill"

    def test_from_dict_empty_expected_documents(self, client_dict: dict) -> None:
        client_dict["expected_documents"] = []
        client = Client.from_dict(client_dict)
        assert client.expected_documents == []

    def test_from_dict_missing_expected_documents_key(self, client_dict: dict) -> None:
        del client_dict["expected_documents"]
        client = Client.from_dict(client_dict)
        assert client.expected_documents == []
