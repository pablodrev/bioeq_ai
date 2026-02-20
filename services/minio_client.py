import io
import os
from typing import BinaryIO

from minio import Minio
from minio.error import S3Error


def get_minio_client() -> Minio:
    endpoint = os.getenv("MINIO_ENDPOINT")
    access_key = os.getenv("MINIO_ACCESS_KEY")
    secret_key = os.getenv("MINIO_SECRET_KEY")

    if not endpoint or not access_key or not secret_key:
        raise ValueError(
            "Не заданы MINIO_ENDPOINT / MINIO_ACCESS_KEY / MINIO_SECRET_KEY"
        )

    secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
    return Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)


def ensure_bucket(bucket_name: str) -> None:
    client = get_minio_client()
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)


def upload_bytes(
    bucket_name: str, object_name: str, data: bytes, content_type: str = "application/octet-stream"
) -> None:
    client = get_minio_client()
    ensure_bucket(bucket_name)
    data_stream = io.BytesIO(data)
    client.put_object(
        bucket_name=bucket_name,
        object_name=object_name,
        data=data_stream,
        length=len(data),
        content_type=content_type,
    )


def upload_file_obj(
    bucket_name: str, object_name: str, file_obj: BinaryIO, length: int, content_type: str = "application/octet-stream"
) -> None:
    client = get_minio_client()
    ensure_bucket(bucket_name)
    client.put_object(
        bucket_name=bucket_name,
        object_name=object_name,
        data=file_obj,
        length=length,
        content_type=content_type,
    )


def download_bytes(bucket_name: str, object_name: str) -> bytes:
    client = get_minio_client()
    response = client.get_object(bucket_name=bucket_name, object_name=object_name)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def remove_object(bucket_name: str, object_name: str) -> None:
    client = get_minio_client()
    client.remove_object(bucket_name=bucket_name, object_name=object_name)


def object_exists(bucket_name: str, object_name: str) -> bool:
    client = get_minio_client()
    try:
        client.stat_object(bucket_name=bucket_name, object_name=object_name)
        return True
    except S3Error as error:
        if error.code in {"NoSuchKey", "NoSuchObject"}:
            return False
        raise
