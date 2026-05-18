import logging
import pdfplumber
import anthropic

from model_config import get_active_model

logger = logging.getLogger(__name__)

VALID_DOCUMENT_TYPES: list[str] = [
    "electricity_bill",
    "tax_invoice",
    "bank_statement",
    "salary_slip",
    "vat_report",
    "other",
]

_CLASSIFICATION_PROMPT = """\
You are a document classification assistant for an accounting firm.
Read the text extracted from the document below and respond with ONLY one of these labels — no explanation, no punctuation, just the label:

electricity_bill
tax_invoice
bank_statement
salary_slip
vat_report
other

Document text:
{text}
"""


def extract_text(file_path: str) -> str:
    with pdfplumber.open(file_path) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    return "\n".join(pages).strip()


def classify_document(file_path: str) -> str:
    text = extract_text(file_path)
    if not text:
        logger.warning("No text extracted from %s — defaulting to 'other'", file_path)
        return "other"

    model = get_active_model()
    if model.provider != "anthropic":
        raise NotImplementedError(
            f"Provider '{model.provider}' is not yet supported. "
            "Set ACTIVE_MODEL to a Claude model key."
        )

    import os
    api_key = os.environ.get(model.api_key_env, "")
    if not api_key:
        raise EnvironmentError(
            f"API key not found. Set the {model.api_key_env} environment variable."
        )

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model.model_id,
        max_tokens=16,
        messages=[
            {
                "role": "user",
                "content": _CLASSIFICATION_PROMPT.format(text=text[:4000]),
            }
        ],
    )

    raw: str = message.content[0].text.strip().lower()
    if raw not in VALID_DOCUMENT_TYPES:
        logger.warning("Unexpected classification response '%s' — defaulting to 'other'", raw)
        return "other"

    logger.debug("Classified %s as '%s'", file_path, raw)
    return raw
