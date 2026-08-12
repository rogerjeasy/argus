from collections.abc import AsyncIterator
from unittest.mock import MagicMock

import pytest

from app.core.config import Settings
from app.ws.gemini_bridge import INPUT_MIME_TYPE, GeminiLiveBridge


class _FakeLiveSession:
    """Stands in for `google.genai.live.AsyncSession`.

    Mirrors the real SDK's split of responsibilities: the object is both the
    `@asynccontextmanager` returned by `client.aio.live.connect(...)` and the
    session it yields, but `close()` and `__aexit__` are tracked separately so
    a test can tell which one the bridge actually invoked.
    """

    def __init__(self, replies: list[bytes]) -> None:
        self._replies = replies
        self.sent: list[dict] = []
        self.close_calls = 0
        self.aexit_calls = 0

    @property
    def closed(self) -> bool:
        """True once the socket has been torn down by either path."""
        return self.close_calls > 0 or self.aexit_calls > 0

    async def send(self, *, input: dict) -> None:
        self.sent.append(input)

    async def receive(self) -> AsyncIterator[MagicMock]:
        for chunk in self._replies:
            response = MagicMock()
            response.data = chunk
            yield response

    async def close(self) -> None:
        self.close_calls += 1

    async def __aenter__(self) -> "_FakeLiveSession":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        self.aexit_calls += 1


@pytest.mark.asyncio
async def test_send_audio_forwards_bytes_to_live_session() -> None:
    fake_session = _FakeLiveSession(replies=[])
    fake_client = MagicMock()
    fake_client.aio.live.connect.return_value = fake_session
    settings = Settings(gcp_project_id="p", vertex_ai_location="us-central1", gemini_live_model="m")

    bridge = GeminiLiveBridge(settings, client_factory=lambda: fake_client)
    await bridge.connect()
    await bridge.send_audio(b"hello-pcm")

    assert fake_session.sent == [{"data": b"hello-pcm", "mime_type": INPUT_MIME_TYPE}]


@pytest.mark.asyncio
async def test_send_audio_declares_the_sample_rate_gemini_live_expects() -> None:
    # Gemini Live cannot infer the rate of a raw PCM stream; without the
    # parameter it mis-reads 16 kHz capture. Must match the browser capture
    # rate in `frontend/lib/session/audio.ts`.
    assert INPUT_MIME_TYPE == "audio/pcm;rate=16000"


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


@pytest.mark.asyncio
async def test_close_finalizes_the_connect_context_manager() -> None:
    # Regression: connect() used to discard the @asynccontextmanager wrapper
    # and keep only the yielded AsyncSession, so the generator was never
    # resumed and the `async with websockets.connect(...)` block inside the
    # SDK never unwound.
    fake_session = _FakeLiveSession(replies=[])
    fake_client = MagicMock()
    fake_client.aio.live.connect.return_value = fake_session
    settings = Settings(gcp_project_id="p", vertex_ai_location="us-central1", gemini_live_model="m")

    bridge = GeminiLiveBridge(settings, client_factory=lambda: fake_client)
    await bridge.connect()
    await bridge.close()

    assert fake_session.aexit_calls == 1
    assert fake_session.closed is True


@pytest.mark.asyncio
async def test_close_is_idempotent_and_safe_before_connect() -> None:
    fake_session = _FakeLiveSession(replies=[])
    fake_client = MagicMock()
    fake_client.aio.live.connect.return_value = fake_session
    settings = Settings(gcp_project_id="p", vertex_ai_location="us-central1", gemini_live_model="m")

    bridge = GeminiLiveBridge(settings, client_factory=lambda: fake_client)
    await bridge.close()  # never connected — must not raise

    await bridge.connect()
    await bridge.close()
    await bridge.close()

    assert fake_session.aexit_calls == 1
