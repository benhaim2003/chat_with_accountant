from __future__ import annotations
import os
import redis

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        url = os.environ["REDIS_URL"]
        _client = redis.from_url(url, decode_responses=True)
    return _client
