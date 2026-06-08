from __future__ import annotations
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ── Document types ────────────────────────────────────────────────────────────

VALID_TYPES: list[str] = [
    "electricity_bill",
    "water_bill",
    "tax_invoice",
    "bank_statement",
    "salary_slip",
    "vat_report",
    "other",
]

# ── Model configuration ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class ModelConfig:
    provider: str
    model_id: str
    display_name: str
    api_key_env: str


AVAILABLE_MODELS: dict[str, ModelConfig] = {
    "claude-opus-4-7": ModelConfig(
        provider="anthropic",
        model_id="claude-opus-4-7",
        display_name="Claude Opus 4.7",
        api_key_env="ANTHROPIC_API_KEY",
    ),
    "claude-sonnet-4-6": ModelConfig(
        provider="anthropic",
        model_id="claude-sonnet-4-6",
        display_name="Claude Sonnet 4.6",
        api_key_env="ANTHROPIC_API_KEY",
    ),
    "claude-haiku-4-5": ModelConfig(
        provider="anthropic",
        model_id="claude-haiku-4-5-20251001",
        display_name="Claude Haiku 4.5",
        api_key_env="ANTHROPIC_API_KEY",
    ),
}

_ACTIVE_KEY: str = os.environ.get("ACTIVE_MODEL", "claude-sonnet-4-6")


def get_active_model() -> ModelConfig:
    if _ACTIVE_KEY not in AVAILABLE_MODELS:
        raise ValueError(
            f"Unknown ACTIVE_MODEL '{_ACTIVE_KEY}'. "
            f"Available: {', '.join(AVAILABLE_MODELS)}"
        )
    return AVAILABLE_MODELS[_ACTIVE_KEY]


# ── Classifier interface ──────────────────────────────────────────────────────

class DocumentClassifier(ABC):
    @abstractmethod
    def classify(self, file_path: str) -> str:
        """Return a document-type label for the given PDF file."""


# ── Anthropic (LLM-based) classifier ─────────────────────────────────────────

_PROMPT = """\
You are a document classification assistant for an accounting firm.
Read the text extracted from the document and respond with ONLY one of these \
labels — no explanation, no punctuation, just the label:

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
        import anthropic
        self._model_id = model_id
        self._client = anthropic.Anthropic(api_key=api_key)

    def classify(self, file_path: str) -> str:
        import pdfplumber
        text = self._extract_text(file_path, pdfplumber)
        if not text:
            logger.warning("No text in %s — defaulting to 'other'", file_path)
            return "other"
        return self._call_llm(file_path, text)

    def _extract_text(self, file_path: str, pdfplumber) -> str:
        with pdfplumber.open(file_path) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages]
        return "\n".join(pages).strip()

    def _call_llm(self, file_path: str, text: str) -> str:
        msg = self._client.messages.create(
            model=self._model_id,
            max_tokens=16,
            messages=[{"role": "user", "content": _PROMPT.format(text=text[:4000])}],
        )
        raw: str = msg.content[0].text.strip().lower()
        if raw not in VALID_TYPES:
            logger.warning("Unexpected label '%s' for %s — using 'other'", raw, file_path)
            return "other"
        return raw


# ── Mock (filename-based) classifier ─────────────────────────────────────────

_FILENAME_PATTERNS: dict[str, list[str]] = {
    "electricity_bill": ["electricity", "electric"],
    "water_bill":       ["water"],
    "tax_invoice":      ["tax", "invoice"],
    "bank_statement":   ["bank", "statement"],
    "salary_slip":      ["salary", "slip", "payslip"],
    "vat_report":       ["vat"],
}


class MockClassifier(DocumentClassifier):
    def classify(self, file_path: str) -> str:
        stem = os.path.basename(file_path).lower()
        for doc_type, patterns in _FILENAME_PATTERNS.items():
            if any(p in stem for p in patterns):
                return doc_type
        return "other"


# ── Public API ────────────────────────────────────────────────────────────────

_classifier: DocumentClassifier | None = None


def classify_document(file_path: str) -> str:
    global _classifier
    if _classifier is None:
        _classifier = _build()
    return _classifier.classify(file_path)


def _build() -> DocumentClassifier:
    model = get_active_model()
    api_key = os.environ.get(model.api_key_env, "")
    if api_key:
        logger.info("Classifier: AnthropicClassifier (%s)", model.model_id)
        return AnthropicClassifier(model_id=model.model_id, api_key=api_key)
    logger.warning("Classifier: %s not set — using MockClassifier", model.api_key_env)
    return MockClassifier()
