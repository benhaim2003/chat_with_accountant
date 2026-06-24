from __future__ import annotations

import base64
import binascii
import json
import logging
import os

logger = logging.getLogger(__name__)

# Pilot phase: chat_id → display-name map. Personal data — never committed.
# Populated from one of two env vars:
#   PILOT_CLIENTS_JSON_B64  — base64-encoded JSON, used in production so the
#                             Container Apps YAML stays ASCII-only (the Windows
#                             Azure CLI can't read non-ASCII YAML files).
#   PILOT_CLIENTS_JSON      — raw single-line JSON, for local dev via .env.
# If neither is set, all clients surface as "לקוח לא מזוהה (<chat_id>)".
def _load() -> dict[str, str]:
    b64 = (os.environ.get("PILOT_CLIENTS_JSON_B64") or "").strip()
    if b64:
        try:
            raw = base64.b64decode(b64).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError) as exc:
            logger.error("PILOT_CLIENTS_JSON_B64 set but could not be decoded: %s", exc)
            return {}
    else:
        raw = (os.environ.get("PILOT_CLIENTS_JSON") or "").strip()
        if not raw:
            logger.warning("PILOT_CLIENTS_JSON(_B64) not set — all clients will show as unidentified.")
            return {}

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Pilot clients JSON could not be parsed: %s", exc)
        return {}
    if not isinstance(data, dict):
        logger.error("Pilot clients JSON must be an object; got %s", type(data).__name__)
        return {}
    return {str(k): str(v) for k, v in data.items()}


_NAMES_BY_CHAT_ID: dict[str, str] = _load()


def client_name(chat_id: str) -> str | None:
    return _NAMES_BY_CHAT_ID.get(str(chat_id))


def client_label(chat_id: str) -> str:
    name = client_name(chat_id)
    return name if name else f"לקוח לא מזוהה ({chat_id})"
