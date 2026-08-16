class FakeStorageClient:
    """Test double for StorageClient — records every upload so a test can
    assert on it, never touches real Cloud Storage."""

    def __init__(self) -> None:
        self.uploads: list[dict] = []

    async def upload_and_sign(self, path: str, data: bytes, *, content_type: str) -> str:
        self.uploads.append({"path": path, "data": data, "content_type": content_type})
        return f"https://fake-storage.example.com/{path}?signed=true"
