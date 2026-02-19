import os
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams


def get_qdrant_client() -> QdrantClient:
    qdrant_url = os.getenv("QDRANT_URL")
    if not qdrant_url:
        raise ValueError("Переменная окружения QDRANT_URL не задана")
    return QdrantClient(url=qdrant_url)


def ensure_collection(collection_name: str, vector_size: int) -> None:
    client = get_qdrant_client()
    collections = client.get_collections().collections
    exists = any(collection.name == collection_name for collection in collections)
    if not exists:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )


def upsert_point(
    collection_name: str,
    point_id: int | str,
    vector: list[float],
    payload: dict[str, Any] | None = None,
) -> None:
    client = get_qdrant_client()
    client.upsert(
        collection_name=collection_name,
        points=[
            PointStruct(
                id=point_id,
                vector=vector,
                payload=payload or {},
            )
        ],
        wait=True,
    )


def search_points(
    collection_name: str,
    query_vector: list[float],
    limit: int = 5,
) -> list[dict[str, Any]]:
    client = get_qdrant_client()
    points = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        limit=limit,
    ).points
    return [
        {
            "id": point.id,
            "score": point.score,
            "payload": point.payload,
        }
        for point in points
    ]


def delete_point(collection_name: str, point_id: int | str) -> None:
    client = get_qdrant_client()
    client.delete(
        collection_name=collection_name,
        points_selector=[point_id],
        wait=True,
    )
