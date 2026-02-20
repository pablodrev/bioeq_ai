import os
from contextlib import contextmanager
from typing import Any, Generator

import psycopg2
import psycopg2.extras


def _database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("Переменная окружения DATABASE_URL не задана")
    return database_url


@contextmanager
def get_postgres_connection() -> Generator[psycopg2.extensions.connection, None, None]:
    conn = psycopg2.connect(_database_url())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def pg_fetch_one(query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    with get_postgres_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            return dict(row) if row else None


def pg_fetch_all(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with get_postgres_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]


def pg_execute(query: str, params: tuple[Any, ...] = ()) -> int:
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.rowcount


def pg_healthcheck() -> bool:
    row = pg_fetch_one("SELECT 1 AS ok;")
    return bool(row and row.get("ok") == 1)
