from __future__ import annotations
import logging
import os

from app.classification.base import DocumentClassifier

logger = logging.getLogger(__name__)

_FILENAME_PATTERNS: dict[str, list[str]] = {
    "electricity_bill": ["electricity", "electric"],
    "water_bill":       ["water"],
    "tax_invoice":      ["tax", "invoice"],
    "bank_statement":   ["bank", "statement"],
    "salary_slip":      ["salary", "slip", "payslip", "paystub"],
    "vat_report":       ["vat", "vat_report"],
}


class MockClassifier(DocumentClassifier):
    """Classifier that infers the document type from the filename alone.

    Used as a zero-cost fallback when no API key is available, and in tests
    that need a deterministic classifier without network calls.
    """

    def classify(self, file_path: str) -> str:
        stem = os.path.basename(file_path).lower()
        for doc_type, patterns in _FILENAME_PATTERNS.items():
            if any(p in stem for p in patterns):
                logger.debug("MockClassifier: %s → %s", file_path, doc_type)
                return doc_type
        logger.debug("MockClassifier: %s → other (no pattern matched)", file_path)
        return "other"
