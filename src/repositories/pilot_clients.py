from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger(__name__)

# Pilot phase: chat_id → display-name map. Populated from the PILOT_CLIENTS_JSON
# env var (a single-line JSON object), not committed to the repo since it contains
# personal data. Falls back to an empty dict so the bot still functions; unknown
# chat ids surface as "לקוח לא מזוהה (<chat_id>)" in email subjects.
def _load() -> dict[str, str]:
    raw = (os.environ.get("PILOT_CLIENTS_JSON") or "").strip()
    if not raw:
        logger.warning("PILOT_CLIENTS_JSON not set — all clients will show as unidentified.")
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("PILOT_CLIENTS_JSON is set but not valid JSON: %s", exc)
        return {}
    if not isinstance(data, dict):
        logger.error("PILOT_CLIENTS_JSON must be a JSON object; got %s", type(data).__name__)
        return {}
    return {str(k): str(v) for k, v in data.items()}


_NAMES_BY_CHAT_ID: dict[str, str] = _load()


def client_name(chat_id: str) -> str | None:
    return _NAMES_BY_CHAT_ID.get(str(chat_id))


def client_label(chat_id: str) -> str:
    name = client_name(chat_id)
    return name if name else f"לקוח לא מזוהה ({chat_id})"
