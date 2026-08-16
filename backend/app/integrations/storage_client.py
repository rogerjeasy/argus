from datetime import timedelta
from typing import Any, Protocol

from starlette.concurrency import run_in_threadpool


class StorageClient(Protocol):
    async def upload_and_sign(self, path: str, data: bytes, *, content_type: str) -> str: ...


class RealStorageClient:
    """The genuine `google-cloud-storage` SDK behind the StorageClient
    interface — not a mock, the real client, just swappable so tests use
    FakeStorageClient instead (design doc §8/§10, same pattern
    `RealTwilioClient` already established). `sdk_client` is injectable for
    tests; unset in production, where it's the real `storage.Client()`
    (see `get_storage_client()` in `core/clients.py`)."""

    def __init__(
        self, bucket_name: str, *, sdk_client: Any | None = None, signed_url_expiry_seconds: int = 3600
    ) -> None:
        self._bucket_name = bucket_name
        self._expiry = signed_url_expiry_seconds
        if sdk_client is not None:
            self._client = sdk_client
        else:
            from google.cloud import storage
            self._client = storage.Client()

    async def upload_and_sign(self, path: str, data: bytes, *, content_type: str) -> str:
        bucket = self._client.bucket(self._bucket_name)
        blob = bucket.blob(path)
        await run_in_threadpool(blob.upload_from_string, data, content_type=content_type)
        return await run_in_threadpool(
            blob.generate_signed_url, version="v4", expiration=timedelta(seconds=self._expiry), method="GET",
        )
