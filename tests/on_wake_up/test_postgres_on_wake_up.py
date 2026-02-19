import os

from services.postgres_client import pg_fetch_all, pg_fetch_one, pg_healthcheck


def test_postgres_healthcheck() -> None:
    os.environ.setdefault(
        "DATABASE_URL",
        "postgresql://postgres_bioeq_user:postgres_bioeq_password_change_me@localhost:5432/postgres_bioeq",
    )
    assert pg_healthcheck() is True


def test_postgres_read_queries() -> None:
    os.environ.setdefault(
        "DATABASE_URL",
        "postgresql://postgres_bioeq_user:postgres_bioeq_password_change_me@localhost:5432/postgres_bioeq",
    )

    one = pg_fetch_one("SELECT 1 AS id, 'ok' AS status;")
    all_rows = pg_fetch_all(
        "SELECT * FROM (VALUES (1, 'a'), (2, 'b')) AS t(id, val) ORDER BY id;"
    )

    assert one == {"id": 1, "status": "ok"}
    assert all_rows == [{"id": 1, "val": "a"}, {"id": 2, "val": "b"}]
