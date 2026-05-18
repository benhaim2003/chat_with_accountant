from abc import ABC, abstractmethod


class DocumentClassifier(ABC):
    @abstractmethod
    def classify(self, file_path: str) -> str:
        """Return a document-type label for the given file (e.g. 'electricity_bill')."""
