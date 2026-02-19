import os
from uuid import uuid4

from services.minio_client import download_bytes, object_exists, remove_object, upload_bytes


def test_minio_upload_download_delete() -> None:
    os.environ.setdefault("MINIO_ENDPOINT", "localhost:9000")
    os.environ.setdefault("MINIO_ACCESS_KEY", "minioadmin")
    os.environ.setdefault("MINIO_SECRET_KEY", "change_me_minio")
    os.environ.setdefault("MINIO_SECURE", "false")

    bucket_name = f"wake-up-{uuid4().hex[:20]}"
    object_name = f"obj-{uuid4().hex}.txt"
    content = b"wake-up-minio-test"

    upload_bytes(bucket_name, object_name, content, content_type="text/plain")
    assert object_exists(bucket_name, object_name) is True
    assert download_bytes(bucket_name, object_name) == content

    remove_object(bucket_name, object_name)
    assert object_exists(bucket_name, object_name) is False
