from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config import Settings
from app.ws.gemini_bridge import GeminiLiveBridge


class _FakeLiveSession:
    def __init__(self, replies: list[bytes]) -> None:
        self._replies = replies
        self.sent: list[bytes] = []

    async def send(self, *, input: dict) -> None:
        self.sent.append(input["data"])

    async def receive(self) -> AsyncIterator[MagicMock]:
        for chunk in self._replies:
            response = MagicMock()
            response.data = chunk
            yield response

    async def __aenter__(self) -> "_FakeLiveSession":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        return None


@pytest.mark.asyncio
async def test_send_audio_forwards_bytes_to_live_session() -> None:
    fake_session = _FakeLiveSession(replies=[])
    fake_client = MagicMock()
    fake_client.aio.live.connect.return_value = fake_session
    settings = Settings(gcp_project_id="p", vertex_ai_location="us-central1", gemini_live_model="m")

    bridge = GeminiLiveBridge(settings, client_factory=lambda: fake_client)
    await bridge.connect()
    await bridge.send_audio(b"hello-pcm")

    assert fake_session.sent == [b"hello-pcm"]


@pytest.mark.asyncio
async def test_receive_audio_yields_response_chunks() -> None:
    fake_session = _FakeLiveSession(replies=[b"chunk-1", b"chunk-2"])
    fake_client = MagicMock()
    fake_client.aio.live.connect.return_value = fake_session
    settings = Settings(gcp_project_id="p", vertex_ai_location="us-central1", gemini_live_model="m")

    bridge = GeminiLiveBridge(settings, client_factory=lambda: fake_client)
    await bridge.connect()

    received = [chunk async for chunk in bridge.receive_audio()]
    assert received == [b"chunk-1", b"chunk-2"]
