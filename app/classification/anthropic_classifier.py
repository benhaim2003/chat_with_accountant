
from __future__ import annotations
import logging
import os

import anthropic
import pdfplumber

from app.classification.base import DocumentClassifier

logger = logging.getLogger(__name__)

VALID_DOCUMENT_TYPES: list[str] = [
    "electricity_bill",
    "water_bill",
    "tax_invoice",
    "bank_statement",
    "salary_slip",
    "vat_report",
    "other",
]

_PROMPT = """\
You are a document classification assistant for an accounting firm.
Read the text extracted from the document below and respond with ONLY one of \
these labels — no explanation, no punctuation, just the label:

electricity_bill
water_bill
tax_invoice
bank_statement
salary_slip
vat_report
other

Document text:
{text}
"""


class AnthropicClassifier(DocumentClassifier):
    def __init__(self, model_id: str, api_key: str) -> None:
        self._model_id = model_id
        self._client = anthropic.Anthropic(api_key=api_key)

    def classify(self, file_path: str) -> str:
        text = self._extract_text(file_path)
        if not text:
            logger.warning("No text extracted from %s — defaulting to 'other'", file_path)
            return "other"
        return self._classify_text(file_path, text)

    def _extract_text(self, file_path: str) -> str:
        with pdfplumber.open(file_path) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        return "\n".join(pages).strip()

    def _classify_text(self, file_path: str, text: str) -> str:
        message = self._client.messages.create(
            model=self._model_id,
            max_tokens=16,
            messages=[{"role": "user", "content": _PROMPT.format(text=text[:4000])}],
        )
        raw: str = message.content[0].text.strip().lower()
        if raw not in VALID_DOCUMENT_TYPES:
            logger.warning(
                "Unexpected classification '%s' for %s — defaulting to 'other'",
                raw,
                file_path,
            )
            return "other"
        logger.debug("Classified %s as '%s'", file_path, raw)
        return raw
