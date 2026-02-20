from typing import Any

from fastapi import FastAPI, Response

from services.minio_client import get_minio_client
from services.postgres_client import pg_healthcheck
from services.qdrant_client import get_qdrant_client
from services.redis_client import get_redis_client

app = FastAPI(title="bioeq-ai")


def _check_server() -> tuple[bool, dict[str, str]]:
    return True, {"status": "ok"}


def _check_redis() -> tuple[bool, dict[str, str]]:
    try:
        redis_ok = bool(get_redis_client().ping())
        payload = {"status": "ok" if redis_ok else "error"}
    except Exception as exc:
        redis_ok = False
        payload = {"status": "error", "error": str(exc)}
    return redis_ok, payload


def _check_postgres() -> tuple[bool, dict[str, str]]:
    try:
        postgres_ok = pg_healthcheck()
        payload = {"status": "ok" if postgres_ok else "error"}
    except Exception as exc:
        postgres_ok = False
        payload = {"status": "error", "error": str(exc)}
    return postgres_ok, payload


def _check_minio() -> tuple[bool, dict[str, str]]:
    try:
        get_minio_client().list_buckets()
        minio_ok = True
        payload = {"status": "ok"}
    except Exception as exc:
        minio_ok = False
        payload = {"status": "error", "error": str(exc)}
    return minio_ok, payload


def _check_qdrant() -> tuple[bool, dict[str, str]]:
    try:
        get_qdrant_client().get_collections()
        qdrant_ok = True
        payload = {"status": "ok"}
    except Exception as exc:
        qdrant_ok = False
        payload = {"status": "error", "error": str(exc)}
    return qdrant_ok, payload


@app.get("/health/server")
def health_server(response: Response) -> dict[str, str]:
    ok, payload = _check_server()
    if not ok:
        response.status_code = 503
    return payload


@app.get("/health/redis")
def health_redis(response: Response) -> dict[str, str]:
    ok, payload = _check_redis()
    if not ok:
        response.status_code = 503
    return payload


@app.get("/health/postgres")
def health_postgres(response: Response) -> dict[str, str]:
    ok, payload = _check_postgres()
    if not ok:
        response.status_code = 503
    return payload


@app.get("/health/minio")
def health_minio(response: Response) -> dict[str, str]:
    ok, payload = _check_minio()
    if not ok:
        response.status_code = 503
    return payload


@app.get("/health/qdrant")
def health_qdrant(response: Response) -> dict[str, str]:
    ok, payload = _check_qdrant()
    if not ok:
        response.status_code = 503
    return payload


@app.get("/health")
def health(response: Response) -> dict[str, Any]:
    server_ok, server_payload = _check_server()
    redis_ok, redis_payload = _check_redis()
    postgres_ok, postgres_payload = _check_postgres()
    minio_ok, minio_payload = _check_minio()
    qdrant_ok, qdrant_payload = _check_qdrant()

    all_ok = server_ok and redis_ok and postgres_ok and minio_ok and qdrant_ok
    if not all_ok:
        response.status_code = 503

    return {
        "status": "ok" if all_ok else "error",
        "services": {
            "server": server_payload,
            "redis": redis_payload,
            "postgres": postgres_payload,
            "minio": minio_payload,
            "qdrant": qdrant_payload,
        },
    }
