from __future__ import annotations
import logging
from src.models.user_model import UserSession

logger = logging.getLogger(__name__)

_sessions: dict[str, UserSession] = {}


def get_session(chat_id: str, platform: str = "telegram") -> UserSession:
    key = _key(chat_id, platform)
    if key not in _sessions:
        _sessions[key] = UserSession(chat_id=chat_id, platform=platform)
        logger.debug("New session: %s", key)
    return _sessions[key]


def set_state(chat_id: str, state: str, platform: str = "telegram", **context) -> None:
    session = get_session(chat_id, platform)
    session.state = state
    if context:
        session.context.update(context)
    logger.debug("Session %s → state=%s", _key(chat_id, platform), state)


def clear_session(chat_id: str, platform: str = "telegram") -> None:
    _sessions.pop(_key(chat_id, platform), None)


def _key(chat_id: str, platform: str) -> str:
    return f"{platform}:{chat_id}"
