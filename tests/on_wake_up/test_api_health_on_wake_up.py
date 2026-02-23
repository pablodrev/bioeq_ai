import json
import time
from http.client import RemoteDisconnected
from urllib.error import URLError
from urllib.request import urlopen


def _get_json_with_retry(url: str, retries: int = 10, delay_seconds: float = 0.5) -> dict:
    last_error: Exception | None = None
    for _ in range(retries):
        try:
            with urlopen(url, timeout=5) as response:
                return json.loads(response.read().decode("utf-8"))
        except (URLError, RemoteDisconnected, ConnectionResetError) as exc:
            last_error = exc
            time.sleep(delay_seconds)
    if last_error is not None:
        raise last_error
    raise RuntimeError("Unexpected empty retry loop state")


def test_api_health_endpoint() -> None:
    data = _get_json_with_retry("http://localhost:8001/health")

    assert data["status"] == "ok"
    assert data["services"]["server"]["status"] == "ok"
    assert data["services"]["redis"]["status"] == "ok"
    assert data["services"]["postgres"]["status"] == "ok"
    assert data["services"]["minio"]["status"] == "ok"
    assert data["services"]["qdrant"]["status"] == "ok"


def test_api_service_health_endpoints() -> None:
    endpoints = [
        "http://localhost:8001/health/server",
        "http://localhost:8001/health/redis",
        "http://localhost:8001/health/postgres",
        "http://localhost:8001/health/minio",
        "http://localhost:8001/health/qdrant",
    ]

    for endpoint in endpoints:
        data = _get_json_with_retry(endpoint)
        assert data["status"] == "ok"
