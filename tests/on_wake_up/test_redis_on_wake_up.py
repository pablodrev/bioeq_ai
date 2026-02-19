import os
from uuid import uuid4

from services.redis_client import redis_delete, redis_exists, redis_get_json, redis_set_json


def test_redis_roundtrip() -> None:
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

    key = f"wake-up:redis:{uuid4().hex}"
    payload = {"service": "redis", "ok": True}

    assert redis_set_json(key, payload, ttl_seconds=30) is True
    assert redis_exists(key) is True
    assert redis_get_json(key) == payload
    assert redis_delete(key) is True
    assert redis_get_json(key) is None
