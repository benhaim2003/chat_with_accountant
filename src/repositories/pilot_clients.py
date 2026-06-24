from __future__ import annotations

# Pilot phase: map known Telegram chat ids → client display names.
# Replace with the real ClientRepository once phone-based identification is wired up.
_NAMES_BY_CHAT_ID: dict[str, str] = {
    # Telegram chat ids
    "[REDACTED-CHATID]":   "[REDACTED-NAME]",
    "[REDACTED-CHATID]":    "[REDACTED-NAME]",
    # WhatsApp phone numbers (E.164 without "+")
    "[REDACTED-PHONE]": "[REDACTED-NAME]",
    "[REDACTED-PHONE]": "[REDACTED-NAME]",
    "[REDACTED-PHONE]": "[REDACTED-NAME]",
}


def client_name(chat_id: str) -> str | None:
    return _NAMES_BY_CHAT_ID.get(str(chat_id))


def client_label(chat_id: str) -> str:
    name = client_name(chat_id)
    return name if name else f"לקוח לא מזוהה ({chat_id})"
