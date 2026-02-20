import json
import os
from typing import Any

from redis import Redis


def get_redis_client() -> Redis:
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        raise ValueError("Переменная окружения REDIS_URL не задана")
    return Redis.from_url(redis_url, decode_responses=True)


def redis_set_json(key: str, value: dict[str, Any], ttl_seconds: int | None = None) -> bool:
    client = get_redis_client()
    payload = json.dumps(value, ensure_ascii=False)
    return bool(client.set(name=key, value=payload, ex=ttl_seconds))


def redis_get_json(key: str) -> dict[str, Any] | None:
    client = get_redis_client()
    payload = client.get(key)
    if payload is None:
        return None
    return json.loads(payload)


def redis_delete(key: str) -> bool:
    client = get_redis_client()
    return bool(client.delete(key))


def redis_exists(key: str) -> bool:
    client = get_redis_client()
    return bool(client.exists(key))
