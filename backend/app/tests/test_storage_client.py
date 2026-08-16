import pytest

from app.integrations.storage_client import RealStorageClient
from app.tests.doubles.fake_storage_client import FakeStorageClient


@pytest.mark.asyncio
async def test_fake_storage_client_records_uploads_and_returns_a_signed_url() -> None:
    fake = FakeStorageClient()

    url = await fake.upload_and_sign("personal_admin_forms/step-1.pdf", b"%PDF-fake", content_type="application/pdf")

    assert url == "https://fake-storage.example.com/personal_admin_forms/step-1.pdf?signed=true"
    assert fake.uploads == [{"path": "personal_admin_forms/step-1.pdf", "data": b"%PDF-fake", "content_type": "application/pdf"}]


class _FakeBlob:
    def __init__(self) -> None:
        self.uploaded: bytes | None = None
        self.content_type: str | None = None

    def upload_from_string(self, data: bytes, content_type: str) -> None:
        self.uploaded = data
        self.content_type = content_type

    def generate_signed_url(self, *, version: str, expiration, method: str) -> str:
        return f"https://storage.example.com/signed?version={version}&method={method}"


class _FakeBucket:
    def __init__(self) -> None:
        self.blobs: dict[str, _FakeBlob] = {}

    def blob(self, path: str) -> _FakeBlob:
        blob = _FakeBlob()
        self.blobs[path] = blob
        return blob


class _FakeSdkClient:
    def __init__(self) -> None:
        self.bucket_obj = _FakeBucket()

    def bucket(self, name: str) -> _FakeBucket:
        return self.bucket_obj


@pytest.mark.asyncio
async def test_real_storage_client_uploads_then_generates_a_v4_signed_url() -> None:
    sdk_client = _FakeSdkClient()
    client = RealStorageClient("test-bucket", sdk_client=sdk_client)

    url = await client.upload_and_sign("personal_admin_forms/step-1.pdf", b"%PDF-fake", content_type="application/pdf")

    assert sdk_client.bucket_obj.blobs["personal_admin_forms/step-1.pdf"].uploaded == b"%PDF-fake"
    assert sdk_client.bucket_obj.blobs["personal_admin_forms/step-1.pdf"].content_type == "application/pdf"
    assert url == "https://storage.example.com/signed?version=v4&method=GET"
