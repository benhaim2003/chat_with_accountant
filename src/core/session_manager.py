from __future__ import annotations
import dataclasses
import json
import logging
from src.models.session import UserSession
from src.infrastructure.redis_client import get_redis

logger = logging.getLogger(__name__)

_SESSION_TTL_SECONDS = 24 * 3600


def _key(chat_id: str, platform) -> str:
    p = platform.value if hasattr(platform, "value") else platform
    return f"session:{p}:{chat_id}"


def get_session(chat_id: str, platform: str = "telegram") -> UserSession:
    raw = get_redis().get(_key(chat_id, platform))
    if raw:
        return UserSession(**json.loads(raw))
    logger.debug("New session: %s", _key(chat_id, platform))
    return UserSession(chat_id=chat_id, platform=platform)


def set_state(chat_id: str, state: str, platform: str = "telegram", **context) -> None:
    session = get_session(chat_id, platform)
    session.state = state
    if context:
        session.context.update(context)
    get_redis().set(_key(chat_id, platform), json.dumps(dataclasses.asdict(session)), ex=_SESSION_TTL_SECONDS)
    logger.debug("Session %s → state=%s", _key(chat_id, platform), state)


def clear_session(chat_id: str, platform: str = "telegram") -> None:
    get_redis().delete(_key(chat_id, platform))
