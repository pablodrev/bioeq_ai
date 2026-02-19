import os
import time
from uuid import uuid4

from services.qdrant_client import (
    delete_point,
    ensure_collection,
    search_points,
    upsert_point,
)


def test_qdrant_upsert_search_delete() -> None:
    os.environ.setdefault("QDRANT_URL", "http://localhost:6333")

    collection = f"wake_up_{uuid4().hex[:16]}"
    point_id = str(uuid4())
    vector = [0.1, 0.2, 0.3]
    payload = {"service": "qdrant", "ok": True}

    ensure_collection(collection, vector_size=3)
    upsert_point(collection, point_id, vector, payload)

    found = False
    for _ in range(5):
        points = search_points(collection, vector, limit=5)
        if any(str(item["id"]) == point_id for item in points):
            found = True
            break
        time.sleep(0.2)
    assert found is True

    delete_point(collection, point_id)

    removed = False
    for _ in range(5):
        points = search_points(collection, vector, limit=5)
        if not any(str(item["id"]) == point_id for item in points):
            removed = True
            break
        time.sleep(0.2)
    assert removed is True
