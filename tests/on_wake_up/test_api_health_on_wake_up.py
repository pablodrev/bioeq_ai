import json
from urllib.request import urlopen


def test_api_health_endpoint() -> None:
    with urlopen("http://localhost:8000/health", timeout=5) as response:
        data = json.loads(response.read().decode("utf-8"))

    assert data["status"] == "ok"
    assert data["services"]["server"]["status"] == "ok"
    assert data["services"]["redis"]["status"] == "ok"
    assert data["services"]["postgres"]["status"] == "ok"
    assert data["services"]["minio"]["status"] == "ok"
    assert data["services"]["qdrant"]["status"] == "ok"


def test_api_service_health_endpoints() -> None:
    endpoints = [
        "http://localhost:8000/health/server",
        "http://localhost:8000/health/redis",
        "http://localhost:8000/health/postgres",
        "http://localhost:8000/health/minio",
        "http://localhost:8000/health/qdrant",
    ]

    for endpoint in endpoints:
        with urlopen(endpoint, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
        assert data["status"] == "ok"
